'''
Created on 12.11.2014

@author: constantin
'''
import logging
import sys
import requests
from models import WebPage, ClickableType, DeltaPage, Url
from urllib.parse import urlparse, urldefrag
from PyQt5.Qt import QApplication, QObject
from filter import LinkExtractor, FormExtractor
from analyzer import TimingAnalyzer, EventlistenerAnalyzer, PropertyAnalyzer
from events import EventExecutor, Event_Result
from events import XHR_Behavior
from utils import Factory, PageHandler, PageRenderer
from enum import Enum
from requests.utils import dict_from_cookiejar
from copy import deepcopy
from execptions import LoginErrorException, LoginFormNotFoundException, \
    PageNotFoundException
from asyncio.tasks import sleep
from persistentmanager import PersistentsManager


potential_logout_urls = []

class Crawler(QObject):
    
    def __init__(self, crawl_config, proxy="", port=0):
        QObject.__init__(self)
        self.app = QApplication(sys.argv)  
        self._link_extractor = LinkExtractor(self, proxy, port, crawl_speed=crawl_config.crawl_speed)
        self._timing_analyzer = TimingAnalyzer(self, proxy, port, crawl_speed=crawl_config.crawl_speed)
        self._property_observer = PropertyAnalyzer(self, proxy, port, crawl_speed=crawl_config.crawl_speed)
        self._addevent_observer = EventlistenerAnalyzer(self, proxy, port, crawl_speed=crawl_config.crawl_speed)
        self._form_extractor = FormExtractor(self, proxy, port, crawl_speed=crawl_config.crawl_speed)
        self._event_executor = EventExecutor(self, proxy, port, crawl_speed=crawl_config.crawl_speed)
        self._page_renderer = PageRenderer(self, proxy, port, crawl_speed=crawl_config.crawl_speed)
        self.domain_handler = None
        self.current_depth = 0
        self.login_form = None
        self.crawl_with_login = False
        self.session_handler = None
        self.headers = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.94 Safari/537.36'
        self.crawler_state = Crawle_State.normal_page
        self.page_handler = PageHandler()
        self.crawl_config = crawl_config
        self.tmp_delta_page_storage = []  # holds the deltapages for further analyses
        self.url_frontier = []
        self.user = None
        self.landing_page_loged_out = None
        self.landing_page_loged_in = None
        self.login_cookie_keys = []
        self.landing_page_url = None
        self.page_id = 0
        self.current_depth = 0
        self.persistentsmanager = PersistentsManager(self.crawl_config)
            
        if proxy != "" and port != 0:
            self.request_proxies = {"https": proxy + ":" + str(port)}
        else:
            self.request_proxies = None
        
    def test(self):
        data = {"log" : "admin", "pwd" : "admin"}
        logging.debug(data)
        response = self.session_handler.post("http://localhost:8080/wp-login.php", data=data, proxies=self.request_proxies, verify=False)
        logging.debug(response.text)
            
    def crawl(self, user):
               
        self.user = self.persistentsmanager.init_new_crawl_session_for_user(user)
        if self.user.login_data is not None:
            self.crawl_with_login = True
        
        """
        Restore initial state
        """
        self._event_executor.seen_timeouts = {}
        self.domain_handler = DomainHandler(self.crawl_config.domain)
        self._link_extractor.domain_handler = self.domain_handler
        self.session_handler = requests.Session()
        self.session_handler.headers.update({"User-Agent":self.headers})
        self.landing_page_url = self.domain_handler.create_url(self.crawl_config.domain)
        self.landing_page_url.depth_of_finding = None
        self.persistentsmanager.insert_url(self.landing_page_url)
        self.landing_page_loged_out = None
        self.landing_page_loged_in = None
        self.login_cookie_keys = []     
                    
        requested_url = None
        necessary_clicks = []  # Saves the actions the crawler need to reach a delta page
        parent_page = None  # Saves the parent of the delta-page (not other delta pages)
        previous_pages = []  # Saves all the pages the crawler have to pass to reach my delta-page
         
        if self.crawl_with_login:
            logging.debug("Crawling with login...")
            login_page = self.get_webpage_without_timeming_analyses(self.user.url_with_login_form)
            self.login_form = self.find_login_form(login_page, self.user.login_data)
            if self.login_form is None:
                raise LoginFormNotFoundException("Could not find login form")
            self.landing_page_loged_out = self.get_webpage_without_timeming_analyses(self.landing_page_url.toString())
            logging.debug("Perform login...")
            self.login(self.user.login_data, self.login_form)
            logging.debug("Validate login...")
            self.landing_page_loged_in = self.get_webpage_without_timeming_analyses(self.landing_page_url.toString())
            if self.landing_page_loged_in.toString() != self.landing_page_loged_out.toString():
                logging.debug("Login successfull...")
                c = dict_from_cookiejar(self.session_handler.cookies)
                for k in c: 
                    self.login_cookie_keys.append(k)
            else:
                raise LoginErrorException("Login failed")
        else:
            logging.debug("Crawl without login")

        """
        Just for debugging
        """
        
        # self.add_new_url(self.domain_handler.create_url("http://localhost:8080/?page_id=5", depth_of_finding=0))
         
        logging.debug("Crawl with userId: " + str(self.user.user_id))   
        while True:
            logging.debug("=======================New Round=======================")
            parent_page = None
            current_page = None
            necessary_clicks = []
            previous_pages = []
            delta_page = None
            
                        
            if len(self.tmp_delta_page_storage) > 0:
                self.crawler_state = Crawle_State.delta_page
                current_page = self.tmp_delta_page_storage.pop(0)
                logging.debug("Processing Deltapage wit ID: {}, {} deltapages left...".format(str(current_page.id), str(len(self.tmp_delta_page_storage))))
                parent_page = current_page
                while isinstance(parent_page, DeltaPage):
                    necessary_clicks.insert(0, parent_page.generator)  # Insert as first element because of reverse order'
                    parent_page = self.persistentsmanager.get_page(parent_page.parent_id)
                    if parent_page is None:
                        raise PageNotFoundException("This exception should never be raised...")
                    previous_pages.append(parent_page)
                # Now I'm reaching a non delta-page
                self.print_to_file(parent_page.toString(), "parent.txt")
                self.current_depth = parent_page.current_depth                
                url = self.domain_handler.create_url(parent_page.url, depth_of_finding=parent_page.current_depth)
                
            else:
                url = self.persistentsmanager.get_next_url_for_crawling()
                if url is not None:
                    self.crawler_state = Crawle_State.normal_page
                    if url.depth_of_finding is None:
                        self.current_depth = 0
                        url.depth_of_finding = 0
                    else:
                        self.current_depth = url.depth_of_finding + 1
                else:
                    break
            
            
            
            if self.crawler_state == Crawle_State.normal_page:
                if not self.domain_handler.is_in_scope(url) or url.depth_of_finding > self.crawl_config.max_depth:
                    logging.debug("Ignoring(Not in scope or max crawl depth reached)...: " + url.toString())
                    self.persistentsmanager.visit_url(url, None, 000)
                    continue    
                
            if self.crawler_state == Crawle_State.delta_page:
                if current_page.delta_depth == self.crawl_config.max_click_depth:
                    logging.debug("Maximum click depth is reached...storing DeltaPage and continue")   
                    self.persistentsmanager.store_delta_page(current_page)
                    self.print_to_file(current_page.toString(), str(current_page.id) + ".txt")
                    continue
                
            logging.debug("Fetching {} ... ".format(url.toString()))
            counter = 0
            
            while True:
                try:
                    response = self.session_handler.get(url.toString(), proxies=self.request_proxies, verify=False)
                    html = response.text
                    requested_url = response.url
                    response_code = response.status_code 
                    break
                except Exception:
                    logging.debug("Exception during fetching ressource occours...")
                    counter += 1
                    if counter == 3:
                        logging.debug("Getting Ressource {} not possible...continue with next".format(url.toString()))
                        html = None
                        requested_url = url.toString()
                        response_code = 666
                    sleep(2)
                    
            
            
            if response_code not in [200, 301, 304]:
                self.persistentsmanager.visit_url(url, webpage_id=None, response_code=response_code)
                continue
            
            if self.crawl_with_login:
                if len(response.history) > 1:
                    if requested_url != url.toString():
                        logging.debug("Possible logout, multiple redirects...")
                        go_on = self.handling_possible_logout()
                        if not go_on:
                            raise LoginErrorException("Relogin failed...")
                if len(self.session_handler.cookies) < len(self.login_cookie_keys) * .80:
                    logging.debug("Possible logout, too less cookies...")
                    go_on = self.handling_possible_logout()
                    if not go_on:
                        raise LoginErrorException("Relogin failed...")
                                            
            
            html = self._page_renderer.render(requested_url, html)
                             
            if self.crawler_state == Crawle_State.delta_page:
                current_page.cookiejar = self.session_handler.cookies  # Assigning current cookies to the page
                current_page.html = html  # Assigning html
                logging.debug("Now at Deltapage: " + str(current_page.id))
                self.persistentsmanager.store_delta_page(current_page)
                
            if self.crawler_state == Crawle_State.normal_page:
                current_page = WebPage(self.get_next_page_id(), requested_url, html, self.session_handler.cookies, depth=self.current_depth)
                logging.debug("Now at Page: " + str(current_page.id))
                current_page = self._analyze_webpage(current_page)
                self.persistentsmanager.visit_url(url, current_page.id, response_code)
                self.extract_new_links_from_page(current_page, self.current_depth)
                self.persistentsmanager.store_web_page(current_page)
            """
            Now beginning of event execution
            """
            
            
            self._event_executor.updateCookieJar(self.session_handler.cookies, requested_url)
            clickable_to_process = deepcopy(current_page.clickables)
            clickable_to_process = self.edit_clickables_for_execution(clickable_to_process)
            clickables = []
            counter = 1
            errors = 0
            retrys = 0
            MAX_RETRYS_FOR_CLICKING = 5
            while len(clickable_to_process) > 0 and retrys < MAX_RETRYS_FOR_CLICKING:
                clickable = clickable_to_process.pop(0)
                if not self.should_execute_clickable(clickable):
                    clickable.clickable_type = ClickableType.Ignored_by_Crawler
                    self.persistentsmanager.update_clickable(current_page.id, clickable)
                    clickables.append(clickable)
                    continue
                logging.debug("Processing Clickable Number {} - {} left".format(str(counter), str(len(clickable_to_process))))
                counter += 1
                
                event = clickable.event 
                if event[0:2] == "on":
                    event = event[2:]
                if clickable.clicked:
                    continue
                
                if event not in self._event_executor.supported_events:
                    clickable.clickable_type = ClickableType.Unsuported_Event
                    self.persistentsmanager.update_clickable(current_page.id, clickable)
                    clickables.append(clickable)
                    continue
                
                if clickable.clickable_type == ClickableType.SendingAjax:
                    xhr_behavior = XHR_Behavior.ignore_xhr
                    event_state, delta_page = self._event_executor.execute(current_page, element_to_click=clickable, pre_clicks=necessary_clicks, xhr_options=XHR_Behavior.ignore_xhr)          
                else:
                    xhr_behavior = XHR_Behavior.intercept_xhr
                    event_state, delta_page = self._event_executor.execute(current_page, element_to_click=clickable, pre_clicks=necessary_clicks, xhr_options=XHR_Behavior.intercept_xhr)
                
                if event_state == Event_Result.Unsupported_Tag:
                    clickable.clicked = True
                    clickable.clickable_type = ClickableType.Unsuported_Event
                    clickables.append(clickable)
                    self.persistentsmanager.update_clickable(current_page.id, clickable)
                    continue
                    
                if event_state == Event_Result.Target_Element_Not_Founs or event_state == Event_Result.Error_While_Initial_Loading:
                    clickable.clicked = True
                    clickable.clickable_type = ClickableType.Error
                    clickables.append(clickable)
                    self.persistentsmanager.update_clickable(current_page.id, clickable)
                    continue
                
                if event_state == Event_Result.Previous_Click_Not_Found:
                    errors += 1
                    clickable.clicked = False
                    error_ratio = errors / len(current_page.clickables)
                    if error_ratio > .2:
                        go_on = self.handling_possible_logout()
                        if not go_on:
                            #raise LoginErrorException("Cannot login anymore")
                            continue
                        else: 
                            retrys += 1
                            errors = 0
                            clickable_to_process.append(clickable)
                            continue
                    else:
                        clickable_to_process.append(clickable)
                
                if self.crawler_state == Crawle_State.normal_page:
                    delta_page.delta_depth = 1
                if self.crawler_state == Crawle_State.delta_page:
                    delta_page.delta_depth = current_page.delta_depth + 1
                
                if event_state == Event_Result.URL_Changed:
                    logging.debug("DeltaPage has new Url..." + delta_page.url)
                    clickable.clicked = True
                    clickable.links_to = delta_page.url                  
                    clickable.clickable_type = ClickableType.Link
                    new_url = self.domain_handler.create_url(delta_page.url, depth_of_finding=current_page.current_depth)
                    self.persistentsmanager.insert_url(new_url)
                    clickables.append(clickable)
                    self.persistentsmanager.update_clickable(current_page.id, clickable)
                else:
                    clickable.clicked = True
                    delta_page.current_depth = self.current_depth
                    delta_page.cookiejar = self.session_handler.cookies
                    delta_page = self._analyze_webpage_without_addeventlisteners(delta_page)
                    if self.crawler_state == Crawle_State.normal_page:
                        delta_page = self.page_handler.subtract_parent_from_delta_page(current_page, delta_page)
                    if self.crawler_state == Crawle_State.delta_page:
                        delta_page = self.page_handler.subtract_parent_from_delta_page(current_page, delta_page)
                        for p in previous_pages:
                            delta_page = self.page_handler.subtract_parent_from_delta_page(p, delta_page)
                    
                    if len(delta_page.clickables) > 0 or len(delta_page.links) > 0 or len(delta_page.ajax_requests) > 0 or len(delta_page.forms) > 0: 
                        if len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            self.handle_delta_page_has_only_new_links(delta_page, current_page) 
                        
                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            self.handle_delta_page_has_only_ajax_requests(delta_page, current_page)
                        
                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            self.handle_delta_page_has_new_links_and_ajax_requests(delta_page, current_page)
                        
                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            self.handle_delta_page_has_only_new_clickables(delta_page, current_page)
                            
                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            self.handle_delta_page_has_new_links_and_clickables(delta_page, current_page)
                            
                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            self.handle_delta_page_has_new_clickables_and_ajax_requests(delta_page, current_page)
                            
                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(delta_page.clickables) != 0 and len(delta_page.forms) == 0:    
                            self.handle_delta_page_has_new_links_ajax_requests__clickables(delta_page, current_page)
                            
                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            self.handle_delta_page_has_only_new_forms(delta_page, current_page)
                            
                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            self.handle_delta_page_has_new_links_and_forms(delta_page, current_page)
                        
                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            self.handle_delta_page_has_new_forms_and_ajax_requests(delta_page, current_page)
                                
                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            self.handle_delta_page_has_new_links_forms_ajax_requests(delta_page, current_page)
                            
                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            self.handle_delta_page_has_new_clickable_and_forms(delta_page, current_page)
                            
                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            self.handle_delta_page_has_new_links_clickables_forms(delta_page, current_page)
                           
                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            self.handle_delta_page_has_new_clickables_forms_ajax_requests(delta_page, current_page)
                            
                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            self.handle_delta_page_has_new_links_clickables_forms_ajax_requests(delta_page, current_page)
                            
                        else:  
                            logging.debug("Nothing matches...")
                            logging.debug("    Clickables: " + str(len(delta_page.clickables)))                     
                            logging.debug("    Links: " + str(len(delta_page.links)))                     
                            logging.debug("    Forms: " + str(len(delta_page.forms)))                     
                            logging.debug("    AjaxRequests: " + str(len(delta_page.ajax_requests)))                     
                                                   
                    else:
                        if clickable.clickable_type != ClickableType.SendingAjax:
                            clickable.clickable_type = ClickableType.UI_Change   
                        
                    if clickable.clickable_type != ClickableType.SendingAjax:
                        clickables.append(clickable)
                        self.persistentsmanager.update_clickable(current_page.id, clickable)
                    else:
                        if xhr_behavior == XHR_Behavior.intercept_xhr: #Proceed again, but this time without interception
                            clickable.clicked = False
                            clickable_to_process.append(clickable)
                        else:
                            clickables.append(clickable)
                            self.persistentsmanager.update_clickable(current_page.id, clickable)
            
            current_page.clickables = clickables
            self.print_to_file(current_page.toString(), str(current_page.id) + ".txt")
                            
         
        logging.debug("No more pages to crawl...")
        #logging.debug("The crawlers visited {} visited_urls...".format(str(len(self.user.visited_urls))))
        #logging.debug("The crawlers sees {} pages...".format(str(len(self.user.visited_pages) + len(self.user.visited_delta_pages))))
        return self.user
    
    def handle_delta_page_has_only_new_links(self, delta_page, parent_page = None):
        delta_page.id = self.get_next_page_id()
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        self.persistentsmanager.store_delta_page(delta_page)
        self.print_to_file(delta_page.toString(), str(delta_page.id) + ".txt")
    
    def handle_delta_page_has_only_new_clickables(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_only_new_forms(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.persistentsmanager.store_delta_page(delta_page)
        self.extract_new_links_from_page(delta_page, self.current_depth)
        self.print_to_file(delta_page.toString(), str(delta_page.id) + ".txt")
                        
    def handle_delta_page_has_only_ajax_requests(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.SendingAjax
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        self.persistentsmanager.extend_ajax_requests_to_webpage(parent_page, delta_page.ajax_requests)
    
    def handle_delta_page_has_new_links_and_clickables(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_new_links_and_forms(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        self.persistentsmanager.store_delta_page(delta_page)
        self.print_to_file(delta_page.toString(), str(delta_page.id) + ".txt")
    
    def handle_delta_page_has_new_links_and_ajax_requests(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        self.persistentsmanager.store_delta_page(delta_page)
        self.print_to_file(delta_page.toString(), str(delta_page.id) + ".txt")
    
    def handle_delta_page_has_new_clickable_and_forms(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_new_clickables_and_ajax_requests(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_new_forms_and_ajax_requests(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_new_links_clickables_forms(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_new_links_forms_ajax_requests(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_new_clickables_forms_ajax_requests(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        delta_page.id = self.get_next_page_id()
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_pages_has_new_links_clickables_forms(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.id = self.get_next_page_id()
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_new_links_ajax_requests__clickables(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    def handle_delta_page_has_new_links_clickables_forms_ajax_requests(self, delta_page, parent_page = None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
    
    
    """
    Returns if we can go on or an unrecoverable error occurs
    """ 
    def handling_possible_logout(self):
        num_retries = 0
        max_num_retries = 3 # We try 3 times to login...
        
        landing_page = self.get_webpage_without_timeming_analyses(self.landing_page_url.toString())
        if self.page_handler.calculate_similarity_between_pages(landing_page, self.landing_page_loged_in) > .8:
            logging.debug("No logout...continue processing")
            return True
        logging.debug("Logout detected...")
        while(num_retries < max_num_retries ):
            logging.debug("Try login number " + str(num_retries+1))
            self.login(self.user.login_data, self.login_form)
            landing_page_after_login_try = self.get_webpage_without_timeming_analyses(self.landing_page_url.toString())
            if self.page_handler.calculate_similarity_between_pages(self.landing_page_loged_in, landing_page_after_login_try) > .0:
                logging.debug("Re login succesfull....continue processing")
                return True
            else:
                logging.debug("Login not successfull...")
                num_retries ++ 1
                sleep(2)
        logging.debug("All loging attempts failed...stop crawling")          
        return False
                   
    def get_webpage_without_timeming_analyses(self, url):
        response = self.session_handler.get(url, proxies=self.request_proxies, verify=False)
        login_page = WebPage(-1, url, response.text, self.session_handler.cookies, 0)
        login_page = self._analyze_webpage_without_timeming(login_page)
        return login_page
        
    
    def find_login_form(self, login_page, login_data):
        login_form = None
        keys = list(login_data.keys())
        data1 = keys[0]
        data2 = keys[1]
        for form in login_page.forms:
            if form.toString().find(data1) > -1 and form.toString().find(data2):
                login_form = form
        return login_form
        
    def login(self, data, login_form):
        if not isinstance(data, dict):
            raise AttributeError("Data must be a dict with login credentials")
        factory = Factory()
        data = factory.form_to_json(login_form, data)
        login_url = self.domain_handler.create_url(login_form.action, depth_of_finding=0)
        res = self.session_handler.post(login_url.toString(), data=data, proxies=self.request_proxies, verify=False)
        return res.url
        
    def extract_new_links_from_page(self, page, current_depth):
        for link in page.links:
            self.persistentsmanager.insert_url(link.url)
        
        if page.ajax_requests is not None:
            for ajax in page.ajax_requests:
                url = self.domain_handler.create_url(ajax.url, page.url, depth_of_finding=current_depth)
                self.persistentsmanager.insert_url(url)
            
        for ajax in page.timing_requests:
            url = self.domain_handler.create_url(ajax.url, page.url, depth_of_finding=current_depth)
            self.persistentsmanager.insert_url(url)
            
        for form in page.forms:
            url = self.domain_handler.create_url(form.action, page.url, depth_of_finding=current_depth)
            self.persistentsmanager.insert_url(url)
    
            
    def _analyze_webpage(self, current_page):
        self._form_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.forms = (self._form_extractor.extract_forms(current_page.html, current_page.url))
        self._link_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.links.extend(self._link_extractor.extract_elements(current_page.html, current_page.url))            
        for link in current_page.links:
            link.url.depth_of_finding = current_page.current_depth
        self._timing_analyzer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.timing_requests = self._timing_analyzer.analyze(current_page.html, current_page.url)
        self._property_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._property_observer.analyze(current_page.html, current_page.url))
        self._addevent_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._addevent_observer.analyze(current_page.html, current_page.url))
        return current_page
    
    def _analyze_webpage_without_timeming(self, current_page):
        self._form_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.forms = (self._form_extractor.extract_forms(current_page.html, current_page.url))
        self._link_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.links.extend(self._link_extractor.extract_elements(current_page.html, current_page.url))            
        for link in current_page.links:
            link.url.depth_of_finding = current_page.current_depth
        self._property_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._property_observer.analyze(current_page.html, current_page.url))
        self._addevent_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._addevent_observer.analyze(current_page.html, current_page.url))
        return current_page
    
    def _analyze_webpage_without_addeventlisteners(self, current_page):
        self._form_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.forms = (self._form_extractor.extract_forms(current_page.html, current_page.url))
        self._link_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.links.extend(self._link_extractor.extract_elements(current_page.html, current_page.url))            
        for link in current_page.links:
            link.url.depth_of_finding = current_page.current_depth
        self._property_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._property_observer.analyze(current_page.html, current_page.url))
        return current_page
    
    def print_to_file(self, item, filename):
        f = open("result/" + str(self.user.user_id) + "/" + filename, "w")
        f.write(item)
        f.close()
    
    def should_delta_page_be_stored_for_crawling(self, delta_page):
        page_handler = PageHandler()
        for d_pages in self.tmp_delta_page_storage:
            if d_pages.url == delta_page.url:
                page_similarity = page_handler.calculate_similarity_between_pages(delta_page, d_pages, clickable_weight=1, form_weight=0, link_weight=0)
                if page_similarity >= 0.9:
                    logging.debug("Equal page is already stored...")
                    return False
        for d_pages in self.get_all_crawled_deltapages_to_url(delta_page.url):
            if d_pages.url == delta_page.url:
                page_similarity = page_handler.calculate_similarity_between_pages(delta_page, d_pages, clickable_weight=1, form_weight=0, link_weight=0)
                if page_similarity >= 0.9:
                    logging.debug("Equal page is already seen...")
                    return False
        return True
    
    def _store_delta_page_for_crawling(self, delta_page):
        self.tmp_delta_page_storage.append(delta_page)
     
     
    def get_all_stored_delta_pages(self):
        return self.tmp_delta_page_storage
    
    def get_all_crawled_deltapages_to_url(self, url):
        result = self.persistentsmanager.get_all_crawled_delta_pages(url)
        return result
    
    def get_next_page_id(self):
        tmp = self.page_id
        self.page_id += 1
        return tmp   
    
        
    def extend_ajax_requests_to_webpage(self, web_page, ajax_requests):
        web_page.ajax_requests.extend(ajax_requests)
        self.persistentsmanager._extend_ajax_requests_to_webpage(web_page, ajax_requests)
        
    """
    Is called right before event execution starts. Here you can change the order or delete clickables
    """
    def edit_clickables_for_execution(self, clickables):
        return clickables
    
    """
    Is called right before an clickable will be executed. You have to return True or False
    """
    
    def should_execute_clickable(self, clickable):
        #logging.debug(str(clickable.html_class) + " : " + str(clickable.event))
        return True
        if clickable.html_class == "yl kH" and clickable.event == "click":
            return True   
        else:
            return False
'''
Pagehandling and Scanning2
'''
class DomainHandler(QObject):
    def __init__(self, domain):
        QObject.__init__(self)
        o = urlparse(domain)
        self.domain = o.netloc
        self.scheme = o.scheme
        
        
    def create_url(self, url, requested_url=None, depth_of_finding=None):
        res = ""
        if requested_url is not None:
            index = requested_url.find("#") 
            if index != -1:
                requested_url = requested_url[:index]
            parsed_requested_url = urldefrag(requested_url)[0]
            parsed_requested_url = urlparse(parsed_requested_url) 
        else:
            parsed_requested_url = urlparse(self.domain)
        url_to_request = urlparse(url)
        
        if url_to_request.netloc != "":  # If url has netloc, we assum it is complete
            res = url
        elif url_to_request.netloc == "" and url_to_request.path == "" and url_to_request.query == "" and url_to_request.fragment != "":  # if only fragment is available, than append original url
            res = requested_url + url
        else:
            if parsed_requested_url != None:
                if parsed_requested_url.scheme == "":
                    scheme = "http"
                else:
                    scheme = parsed_requested_url.scheme
                res += scheme + "://" + parsed_requested_url.netloc  # requested url must have this!!
                if res[len(res) - 1] != "/":  # Up to here...url: scheme://domain/
                    res += "/"
                if parsed_requested_url.path != "":
                    tmp = parsed_requested_url.path.split("/")
                    path = ""
                    for part in tmp:  # To find folder of the page
                        if part.find(".") == -1 and part != "":
                            path += part + "/"
                    res += path
                if url_to_request.path != "":
                    if url_to_request.path != "/":
                        if url_to_request.path[0] == "/":
                            res += url_to_request.path[1:]
                        else:
                            res += url_to_request.path
                if url_to_request.query != "":
                    res += "?" + url_to_request.query
                if url_to_request.fragment != "":
                    res += "#" + url_to_request.fragment
            else:
                logging.debug("Connot handle: {} - {}".format(url, requested_url))
                return None
        
        res = Url(res)
        res.depth_of_finding = depth_of_finding
        return res 
    
    def is_in_scope(self, url):
        url_splits = url.toString().split(".")
        end_of_url = url_splits[len(url_splits) - 1]
        if end_of_url in ['png', "jpg"]:
            return False
        parsed_url = urlparse(url.toString())
        if parsed_url.netloc.find(self.domain) != -1 and parsed_url.fragment == "":
            return True
        else:
            return False
        
    def create_url_from_domain(self, domain):
        return "http://" + domain

    def has_urls_same_structure(self, url1, url2):
        if url1.__class__ != url2.__class__:
            raise ValueError("Both must be Url...")
        
        if url1.toString() == url2.toString():
            return True
        
        
        if url1.domain != url2.domain or url1.path != url2.path or len(url1.params) != len(url2.params):
            return False
          
        for key in url1.params:
            if key not in url2.params:
                return False
            
        for key in url2.params:
            if key not in url1.params:
                return False
        
        return True

class Crawle_State(Enum):
    normal_page = 0
    event_generated_page = 1
    delta_page = 2 
    analyze_login_page = 3
    login = 4
    

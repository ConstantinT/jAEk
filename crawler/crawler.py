'''
Created on 12.11.2014

@author: constantin
'''
import logging
import sys
from PyQt5.Qt import QApplication, QObject
from enum import Enum
from copy import deepcopy

from filter.linkextractor import LinkExtractor
from analyzer.timemimganalzyer import TimingAnalyzer
from analyzer.propertyanalyzer import PropertyAnalyzer
from analyzer.eventlisteneranalyzer import EventlistenerAnalyzer
from filter.formextractor import FormExtractor
from analyzer.eventexecutor import EventExecutor, XHR_Behavior, Event_Result
from utils.utils import PageHandler
from database.persistentmanager import PersistentsManager
from utils.execptions import PageNotFoundException
from models.deltapage import DeltaPage
from models.webpage import WebPage
from models.clickabletype import ClickableType
from utils.pagerenderer import PageRenderer
from utils.domainhandler import DomainHandler
from urllib.parse import urljoin
from analyzer.dynamicanalyzer import Analyzer
from utils.requestmanager import RequestManager




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
        self._dynamic_analyzer = Analyzer(self, proxy, port, crawl_speed=crawl_config.crawl_speed)
        self.domain_handler = None
        self.current_depth = 0
        self.crawl_with_login = False
        
        self.crawler_state = Crawle_State.normal_page
        self.page_handler = PageHandler()
        self.crawl_config = crawl_config
        self.tmp_delta_page_storage = []  # holds the deltapages for further analyses
        self.url_frontier = []
        self.user = None
        self.page_id = 0
        self.current_depth = 0
        self.persistentsmanager = PersistentsManager(self.crawl_config)

        
        
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
        self.domain_handler = DomainHandler(self.crawl_config.start_page_url)
        self._link_extractor.domain_handler = self.domain_handler
        
        start_page_url = self.domain_handler.create_url(self.crawl_config.start_page_url, None)
        self.persistentsmanager.insert_url(start_page_url)
        self.requestmanager = RequestManager(self.crawl_with_login, self, start_page_url.toString(), self.user.login_data, self.user.url_with_login_form)
        
        
        necessary_clicks = []  # Saves the actions the crawler need to reach a delta page
        parent_page = None  # Saves the parent of the delta-page (not other delta pages)
        previous_pages = []  # Saves all the pages the crawler have to pass to reach my delta-page
         
        if self.crawl_with_login:
            self.requestmanager.initial_login()
        else:
            logging.debug("Crawl without login")

        
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
                self.current_depth = parent_page.current_depth                
                url = parent_page.url
                
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
                response_url, response_code, html, cookies = self.requestmanager.fetch_page(url.toString()) 
                
            if self.crawler_state == Crawle_State.delta_page:
                if current_page.delta_depth == self.crawl_config.max_click_depth:
                    logging.debug("Maximum click depth is reached...storing DeltaPage and continue")   
                    self.persistentsmanager.store_delta_page(current_page)
                    self.print_to_file(current_page.toString(), str(current_page.id) + ".txt")
                    continue
                response_url, response_code, html, cookies = self.requestmanager.fetch_page(url) 
                
            
                    
            
            
            if response_code not in [200, 301, 304]:
                self.persistentsmanager.visit_url(url, webpage_id=None, response_code=response_code)
                continue
            
            
            
            base_url, html = self._page_renderer.render(response_url, html)
                             
            if self.crawler_state == Crawle_State.delta_page:
                current_page.cookiejar = cookies  # Assigning current cookies to the page
                current_page.html = html  # Assigning html
                logging.debug("Now at Deltapage: " + str(current_page.id))
                self.persistentsmanager.store_delta_page(current_page)
                
            if self.crawler_state == Crawle_State.normal_page:
                current_page = WebPage(self.get_next_page_id(), response_url, html, cookies, depth=self.current_depth, base_url = base_url)
                logging.debug("Now at Page: " + str(current_page.id))
                current_page = self._analyze_webpage(current_page)
                self.persistentsmanager.visit_url(url, current_page.id, response_code)
                self.extract_new_links_from_page(current_page, self.current_depth, current_page.base_url)
                self.persistentsmanager.store_web_page(current_page)
            """
            Now beginning of event execution
            """
            
            
            self._event_executor.updateCookieJar(cookies, response_url)
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
                        go_on = self.requestmanager.handling_possible_logout()
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
                    delta_page.cookiejar = cookies
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
    
    

                   
    def get_webpage_without_timeming_analyses(self, url):
        response, cookies = self.requestmanager.get(url)
        login_page = WebPage(-1, url, response.text, cookies, 0)
        login_page = self._analyze_webpage_without_timeming(login_page)
        return login_page
        
    
    def find_login_form(self, login_page, login_data):
        login_form = None
        keys = list(login_data.keys())
        data1 = keys[0]
        data2 = keys[1]
        for form in login_page.forms:
            if form.toString().find(data1) > -1 and form.toString().find(data2) > -1:
                login_form = form
        return login_form
        
    
        
    def extract_new_links_from_page(self, page, current_depth, base_url = None):
        
        if base_url is not None:
            base_url = base_url
        else:
            base_url = page.url
            
        for link in page.links:
            self.persistentsmanager.insert_url(link.url)
        
        if page.ajax_requests is not None:
            for ajax in page.ajax_requests:
                url = self.domain_handler.create_url(ajax.url, base_url,  depth_of_finding=current_depth)
                self.persistentsmanager.insert_url(url)
            
        for ajax in page.timing_requests:
            url = self.domain_handler.create_url(ajax.url, base_url, depth_of_finding=current_depth)
            self.persistentsmanager.insert_url(url)
            
        for form in page.forms:
            url = self.domain_handler.create_url(form.action, base_url, depth_of_finding=current_depth)
            self.persistentsmanager.insert_url(url)
    
            
    def _analyze_webpage(self, current_page):
        self._dynamic_analyzer.updateCookieJar(current_page.cookiejar, current_page.url)
        html_after_timeouts, clickables, timeming_requests = self._dynamic_analyzer.analyze(current_page.html, current_page.url) 
        
        self._form_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(clickables)
        current_page.timing_requests = timeming_requests
        forms = (self._form_extractor.extract_forms(html_after_timeouts, current_page.url))
        # TODO: Maybe do to another place
        for form in forms:
            if current_page.base_url is not None:
                self.convert_action_url_to_absolute(form, current_page.base_url)
            else:
                self.convert_action_url_to_absolute(form, current_page.url)
        current_page.forms = forms
        self._link_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        new_links, new_clickables = self._link_extractor.extract_elements(html_after_timeouts, current_page.url, base_url=current_page.base_url)
        current_page.links.extend(new_links)            
        for link in current_page.links:
            link.url.depth_of_finding = current_page.current_depth
        for clickables in new_clickables:
            clickables.clickable_depth = 0
        current_page.clickables.extend(new_clickables)
        self._property_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._property_observer.analyze(html_after_timeouts, current_page.url))
        return current_page
    
    def _analyze_webpage_without_addeventlisteners(self, current_page):
        self._form_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        forms = (self._form_extractor.extract_forms(current_page.html, current_page.url))
        # TODO: Maybe do to another place
        for form in forms:
            if current_page.base_url is not None:
                self.convert_action_url_to_absolute(form, current_page.base_url)
            else:
                self.convert_action_url_to_absolute(form, current_page.url)
        current_page.forms = forms
        self._link_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        new_links, new_clickables = self._link_extractor.extract_elements(current_page.html, current_page.url, base_url=current_page.base_url)
        current_page.links.extend(new_links)            
        for link in current_page.links:
            link.url.depth_of_finding = current_page.current_depth
        for clickables in new_clickables:
            try: # Try a little bit duck typing
                clickables.clickable_depth = current_page.delta_depth
            except KeyError:
                clickables.clickable_depth = 0            
        current_page.clickables.extend(new_clickables)
        
        self._property_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._property_observer.analyze(current_page.html, current_page.url))
        return current_page
    
    def _analyze_webpage_without_timeming(self, current_page):
        self._form_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        forms = (self._form_extractor.extract_forms(current_page.html, current_page.url))
        # TODO: Maybe do to another place
        for form in forms:
            if current_page.base_url is not None:
                self.convert_action_url_to_absolute(form, current_page.base_url)
            else:
                self.convert_action_url_to_absolute(form, current_page.url)
        current_page.forms = forms
        self._link_extractor.updateCookieJar(current_page.cookiejar, current_page.url)
        new_links, new_clickables = self._link_extractor.extract_elements(current_page.html, current_page.url, base_url=current_page.base_url)
        current_page.links.extend(new_links)            
        for link in current_page.links:
            link.url.depth_of_finding = current_page.current_depth
        for clickables in new_clickables:
            try: # Try a little bit duck typing
                clickables.clickable_depth = current_page.delta_depth
            except KeyError:
                clickables.clickable_depth = 0            
        current_page.clickables.extend(new_clickables)
        
        self._addevent_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._addevent_observer.analyze(current_page.html, current_page.url))
        self._property_observer.updateCookieJar(current_page.cookiejar, current_page.url)
        current_page.clickables.extend(self._property_observer.analyze(current_page.html, current_page.url))
        return current_page
    
    
    def convert_action_url_to_absolute(self, form, base):
        form.action = urljoin(base, form.action)
        return form
    
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


class Crawle_State(Enum):
    normal_page = 0
    event_generated_page = 1
    delta_page = 2 
    analyze_login_page = 3
    login = 4
    

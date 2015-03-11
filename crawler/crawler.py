"""
Created on 12.11.2014

@author: constantin
"""
import logging
import sys
from enum import Enum
from copy import deepcopy
from urllib.parse import urljoin

from PyQt5.Qt import QApplication, QObject

from analyzer.eventexecutor import EventExecutor, XHR_Behavior, Event_Result
from database.persistentmanager import PersistentsManager
from models.url import Url
from utils.execptions import PageNotFoundException
from models.deltapage import DeltaPage
from models.webpage import WebPage
from models.clickabletype import ClickableType
from utils.domainhandler import DomainHandler
from analyzer.dynamicanalyzer import Analyzer
from network.network import NetWorkAccessManager
from utils.utils import calculate_similarity_between_pages, subtract_parent_from_delta_page, form_to_dict


potential_logout_urls = []


class Crawler(QObject):
    def __init__(self, crawl_config, proxy="", port=0):
        QObject.__init__(self)
        self.app = QApplication(sys.argv)
        self._network_access_manager = NetWorkAccessManager(self)
        self._event_executor = EventExecutor(self, proxy, port, crawl_speed=crawl_config.crawl_speed,
                                             network_access_manager=self._network_access_manager)
        self._dynamic_analyzer = Analyzer(self, proxy, port, crawl_speed=crawl_config.crawl_speed,
                                          network_access_manager=self._network_access_manager)
        self.domain_handler = None
        self.current_depth = 0
        self.crawl_with_login = False
        self.proxy = proxy
        self.port = port

        self.crawler_state = CrawlState.normal_page
        self.crawl_config = crawl_config
        self.tmp_delta_page_storage = []  # holds the deltapages for further analyses
        self.url_frontier = []
        self.user = None
        self.page_id = 0
        self.current_depth = 0
        self.persistentsmanager = PersistentsManager(self.crawl_config)


    def crawl(self, user):

        self.user = self.persistentsmanager.init_new_crawl_session_for_user(user)
        self.domain_handler = DomainHandler(self.crawl_config.start_page_url)
        start_page_url = self.domain_handler.create_url(self.crawl_config.start_page_url, None)
        self.persistentsmanager.insert_url(start_page_url)

        if self.user.login_data is not None:
            self.crawl_with_login = True
            self.initial_login(start_page_url, self.user.login_data)


        necessary_clicks = []  # Saves the actions the crawler need to reach a delta page
        parent_page = None  # Saves the parent of the delta-page (not other delta pages)
        previous_pages = []  # Saves all the pages the crawler have to pass to reach my delta-page

        logging.debug("Crawl with userId: " + str(self.user.user_id))

        while True:
            logging.debug("=======================New Round=======================")
            parent_page = None
            current_page = None
            necessary_clicks = []
            previous_pages = []
            delta_page = None

            if len(self.tmp_delta_page_storage) > 0:
                self.crawler_state = CrawlState.delta_page
                current_page = self.tmp_delta_page_storage.pop(0)
                logging.debug("Processing Deltapage with ID: {}, {} deltapages left...".format(str(current_page.id),
                                                                                               str(len(
                                                                                                   self.tmp_delta_page_storage))))
                parent_page = current_page
                while isinstance(parent_page, DeltaPage):
                    necessary_clicks.insert(0,
                                            parent_page.generator)  # Insert as first element because of reverse order'
                    parent_page = self.persistentsmanager.get_page(parent_page.parent_id)
                    if parent_page is None:
                        raise PageNotFoundException("This exception should never be raised...")
                    previous_pages.append(parent_page)
                # Now I'm reaching a non delta-page
                self.current_depth = parent_page.current_depth
                url_to_request = self.domain_handler.create_url(parent_page.url)

            else:
                url_to_request = self.persistentsmanager.get_next_url_for_crawling()
                if url_to_request is not None:
                    self.crawler_state = CrawlState.normal_page
                    if url_to_request.depth_of_finding is None:
                        self.current_depth = 0
                        url_to_request.depth_of_finding = 0
                    else:
                        self.current_depth = url_to_request.depth_of_finding + 1
                else:
                    break

            if self.crawler_state == CrawlState.normal_page:
                if not self.domain_handler.is_in_scope(
                        url_to_request) or url_to_request.depth_of_finding > self.crawl_config.max_depth:
                    logging.debug("Ignoring(Not in scope or max crawl depth reached)...: " + url_to_request.toString())
                    self.persistentsmanager.visit_url(url_to_request, None, 000)
                    continue
                response_code, html_after_timeouts, new_clickables, forms, links, timemimg_requests = self._dynamic_analyzer.analyze(url_to_request, current_depth=self.current_depth)

                current_page = WebPage(self.get_next_page_id(), url_to_request.toString(), html_after_timeouts)
                current_page.timeming_requests = timemimg_requests
                current_page.clickables = new_clickables
                current_page.links = links
                current_page.forms = forms
                self.domain_handler.complete_urls(current_page)
                self.persistentsmanager.store_web_page(current_page)
                self.persistentsmanager.visit_url(url_to_request,current_page.id, response_code)
                self.extract_new_links_from_page(current_page, current_page.current_depth, current_page.url)
                #logging.debug(page.toString())

            if self.crawler_state == CrawlState.delta_page:
                current_page.html = parent_page.html  # Assigning html
                logging.debug("Now at Deltapage: " + str(current_page.id))
                self.persistentsmanager.store_delta_page(current_page)
            # break

            clickable_to_process = deepcopy(current_page.clickables)
            clickable_to_process = self.edit_clickables_for_execution(clickable_to_process)
            clickables = []
            counter = 1  # Just a counter for displaying progress
            errors = 0  # Count the errors(Missing preclickable or target elements=
            retrys = 0  # Count the retries
            MAX_RETRYS_FOR_CLICKING = 5

            while len(clickable_to_process) > 0 and retrys < MAX_RETRYS_FOR_CLICKING:
                clickable = clickable_to_process.pop(0)
                if not self.should_execute_clickable(clickable):
                    clickable.clickable_type = ClickableType.Ignored_by_Crawler
                    self.persistentsmanager.update_clickable(current_page.id, clickable)
                    clickables.append(clickable)
                    continue
                logging.debug(
                    "Processing Clickable Number {} - {} left".format(str(counter), str(len(clickable_to_process))))
                counter += 1

                """
                If event is something like "onclick", take of the "on"
                """
                event = clickable.event
                if event[0:2] == "on":
                    event = event[2:]
                if clickable.clicked:
                    continue

                """
                If event is not supported, mark it so in the database and continue
                """
                if event not in self._event_executor.supported_events:
                    clickable.clickable_type = ClickableType.Unsuported_Event
                    self.persistentsmanager.update_clickable(current_page.id, clickable)
                    clickables.append(clickable)
                    continue
                """
                Because I want first a run without sending something to the backend, I distinguish if I know an element or not.
                If I know it(its clickable_type is set) I re-execute the event and let the ajax request pass.
                If I don't know it, I execute each clickable with an interception.
                """
                if clickable.clickable_type is not None:
                    """
                    The clickable was executed in the past, and has triggered an backend request. Know execute it again and let that request pass
                    """
                    xhr_behavior = XHR_Behavior.observe_xhr
                    event_state, delta_page = self._event_executor.execute(current_page, element_to_click=clickable,
                                                                           pre_clicks=necessary_clicks,
                                                                           xhr_options=xhr_behavior)
                else:
                    """
                    The clickable was never executed, so execute it with intercepting all backend requests.
                    """
                    xhr_behavior = XHR_Behavior.intercept_xhr
                    event_state, delta_page = self._event_executor.execute(current_page, element_to_click=clickable,
                                                                           pre_clicks=necessary_clicks,
                                                                           xhr_options=xhr_behavior)

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
                            # raise LoginErrorException("Cannot login anymore")
                            continue
                        else:
                            retrys += 1
                            errors = 0
                            clickable_to_process.append(clickable)
                            continue
                    else:
                        clickable_to_process.append(clickable)

                if self.crawler_state == CrawlState.normal_page:
                    delta_page.delta_depth = 1
                if self.crawler_state == CrawlState.delta_page:
                    delta_page.delta_depth = current_page.delta_depth + 1

                if event_state == Event_Result.URL_Changed:
                    logging.debug("DeltaPage has new Url..." + delta_page.url)
                    clickable.clicked = True
                    clickable.links_to = delta_page.url
                    clickable.clickable_type = ClickableType.Link
                    new_url = self.domain_handler.create_url(delta_page.url,
                                                             depth_of_finding=current_page.current_depth)
                    self.persistentsmanager.insert_url(new_url)
                    clickables.append(clickable)
                    self.persistentsmanager.update_clickable(current_page.id, clickable)
                else:
                    """
                    Everything works fine and I get a normal DeltaPage, now I have to:
                        - Assigne the current depth to it -> DeltaPages have the same depth as its ParentPages
                        - Assign the cookies, just for output and debugging
                        - Analyze the Deltapage without addEventlisteners and timemimg check. This is done during event execution
                        - Substract the ParentPage, optional Parent + all previous visited DeltaPages, from the DeltaPage to get
                          get the real DeltaPage
                        - Handle it after the result of the substraction
                    """
                    clickable.clicked = True
                    delta_page.current_depth = self.current_depth
                    delta_page = self.domain_handler.complete_urls(delta_page)

                    if self.crawler_state == CrawlState.normal_page:
                        delta_page = subtract_parent_from_delta_page(current_page, delta_page)
                    if self.crawler_state == CrawlState.delta_page:
                        delta_page = subtract_parent_from_delta_page(current_page, delta_page)
                        for p in previous_pages:
                            delta_page = subtract_parent_from_delta_page(p, delta_page)

                    if len(delta_page.clickables) > 0 or len(delta_page.links) > 0 or len(
                            delta_page.ajax_requests) > 0 or len(delta_page.forms) > 0:
                        if len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            clickable = self.handle_delta_page_has_only_new_links(clickable, delta_page, current_page,
                                                                                  xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            clickable = self.handle_delta_page_has_only_ajax_requests(clickable, delta_page,
                                                                                      current_page, xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            clickable = self.handle_delta_page_has_new_links_and_ajax_requests(clickable, delta_page,
                                                                                               current_page,
                                                                                               xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            clickable = self.handle_delta_page_has_only_new_clickables(clickable, delta_page,
                                                                                       current_page, xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            clickable = self.handle_delta_page_has_new_links_and_clickables(clickable, delta_page,
                                                                                            current_page, xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            clickable = self.handle_delta_page_has_new_clickables_and_ajax_requests(clickable,
                                                                                                    delta_page,
                                                                                                    current_page,
                                                                                                    xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            clickable = self.handle_delta_page_has_new_links_ajax_requests__clickables(clickable,
                                                                                                       delta_page,
                                                                                                       current_page,
                                                                                                       xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            clickable = self.handle_delta_page_has_only_new_forms(clickable, delta_page, current_page,
                                                                                  xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            clickable = self.handle_delta_page_has_new_links_and_forms(clickable, delta_page,
                                                                                       current_page, xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            clickable = self.handle_delta_page_has_new_forms_and_ajax_requests(clickable, delta_page,
                                                                                               current_page,
                                                                                               xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            clickable = self.handle_delta_page_has_new_links_forms_ajax_requests(clickable, delta_page,
                                                                                                 current_page,
                                                                                                 xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            clickable = self.handle_delta_page_has_new_clickable_and_forms(clickable, delta_page,
                                                                                           current_page, xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            clickable = self.handle_delta_page_has_new_links_clickables_forms(clickable, delta_page,
                                                                                              current_page,
                                                                                              xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            clickable = self.handle_delta_page_has_new_clickables_forms_ajax_requests(clickable,
                                                                                                      delta_page,
                                                                                                      current_page,
                                                                                                      xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            clickable = self.handle_delta_page_has_new_links_clickables_forms_ajax_requests(clickable,
                                                                                                            delta_page,
                                                                                                            current_page,
                                                                                                            xhr_behavior)

                        else:
                            logging.debug("Nothing matches...")
                            logging.debug("    Clickables: " + str(len(delta_page.clickables)))
                            logging.debug("    Links: " + str(len(delta_page.links)))
                            logging.debug("    Forms: " + str(len(delta_page.forms)))
                            logging.debug("    AjaxRequests: " + str(len(delta_page.ajax_requests)))

                        if clickable is not None:
                            clickable.clicked = False
                            clickable_to_process.append(clickable)

                    else:
                        clickable.clickable_type = ClickableType.UI_Change
                        self.persistentsmanager.update_clickable(current_page.id, clickable)

            current_page.clickables = clickables
            self.print_to_file(current_page.toString(), str(current_page.id) + ".txt")


    def handle_delta_page_has_only_new_links(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.id = self.get_next_page_id()
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        self.persistentsmanager.store_delta_page(delta_page)
        self.persistentsmanager.update_clickable(parent_page.id, clickable)
        self.print_to_file(delta_page.toString(), str(delta_page.id) + ".txt")

    def handle_delta_page_has_only_new_clickables(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.persistentsmanager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)

    def handle_delta_page_has_only_new_forms(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.persistentsmanager.store_delta_page(delta_page)
        self.extract_new_links_from_page(delta_page, self.current_depth)
        self.persistentsmanager.update_clickable(parent_page.id, clickable)
        self.print_to_file(delta_page.toString(), str(delta_page.id) + ".txt")

    def handle_delta_page_has_only_ajax_requests(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        clickable.clickable_type = ClickableType.SendingAjax
        if xhr_behavior == XHR_Behavior.observe_xhr:
            self.persistentsmanager.extend_ajax_requests_to_webpage(parent_page, delta_page.ajax_requests)
        else:
            return clickable

    def handle_delta_page_has_new_links_and_clickables(self, clickable, delta_page, parent_page=None,
                                                       xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        self.persistentsmanager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)

    def handle_delta_page_has_new_links_and_forms(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        self.persistentsmanager.store_delta_page(delta_page)
        self.persistentsmanager.update_clickable(parent_page.id, clickable)
        self.print_to_file(delta_page.toString(), str(delta_page.id) + ".txt")

    def handle_delta_page_has_new_links_and_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                          xhr_behavior=None):
        if xhr_behavior == XHR_Behavior.observe_xhr:
            delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
            delta_page.id = self.get_next_page_id()
            self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.persistentsmanager.store_delta_page(delta_page)
            self.persistentsmanager.update_clickable(parent_page.id, clickable)
            self.print_to_file(delta_page.toString(), str(delta_page.id) + ".txt")
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return clickable

    def handle_delta_page_has_new_clickable_and_forms(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.persistentsmanager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)

    def handle_delta_page_has_new_clickables_and_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                               xhr_behavior=None):
        if xhr_behavior == XHR_Behavior.observe_xhr:
            delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
            delta_page.id = self.get_next_page_id()
            self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.persistentsmanager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return clickable

    def handle_delta_page_has_new_forms_and_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                          xhr_behavior=None):
        if xhr_behavior == XHR_Behavior.observe_xhr:
            delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
            delta_page.id = self.get_next_page_id()
            self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.persistentsmanager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return clickable

    def handle_delta_page_has_new_links_clickables_forms(self, clickable, delta_page, parent_page=None,
                                                         xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        delta_page.id = self.get_next_page_id()
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        self.persistentsmanager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)

    def handle_delta_page_has_new_links_forms_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                            xhr_behavior=None):
        if xhr_behavior == XHR_Behavior.observe_xhr:
            delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
            delta_page.id = self.get_next_page_id()
            self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.persistentsmanager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return clickable

    def handle_delta_page_has_new_clickables_forms_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                                 xhr_behavior=None):
        if xhr_behavior == XHR_Behavior.observe_xhr:
            delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
            self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            delta_page.id = self.get_next_page_id()
            self.persistentsmanager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return clickable


    def handle_delta_pages_has_new_links_clickables_forms(self, clickable, delta_page, parent_page=None,
                                                          xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
        self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
        delta_page.id = self.get_next_page_id()
        self.persistentsmanager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)

    def handle_delta_page_has_new_links_ajax_requests__clickables(self, clickable, delta_page, parent_page=None,
                                                                  xhr_behavior=None):
        if xhr_behavior == XHR_Behavior.observe_xhr:
            delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
            delta_page.id = self.get_next_page_id()
            self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.persistentsmanager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return clickable

    def handle_delta_page_has_new_links_clickables_forms_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                                       xhr_behavior=None):
        if xhr_behavior == XHR_Behavior.observe_xhr:
            delta_page.generator.clickable_type = ClickableType.Creates_new_navigatables
            delta_page.id = self.get_next_page_id()
            self.extract_new_links_from_page(delta_page, current_depth=self.current_depth)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.persistentsmanager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return clickable


    def find_form_with_special_params(self, page, login_data):
        login_form = None
        keys = list(login_data.keys())
        data1 = keys[0]
        data2 = keys[1]
        for form in page.forms:
            logging.debug(form.toString())
            if form.toString().find(data1) > -1 and form.toString().find(data2) > -1:
                login_form = form
        return login_form


    def extract_new_links_from_page(self, page, current_depth, base_url=None):

        for link in page.links:
            self.persistentsmanager.insert_url(link.url)

        if page.ajax_requests is not None:
            for ajax in page.ajax_requests:
                url = self.domain_handler.create_url(ajax.url, None, depth_of_finding=current_depth)
                self.persistentsmanager.insert_url(url)

        for ajax in page.timeming_requests:
            url = self.domain_handler.create_url(ajax.url, None, depth_of_finding=current_depth)
            self.persistentsmanager.insert_url(url)

        for form in page.forms:
            url = self.domain_handler.create_url(form.action, None, depth_of_finding=current_depth)
            self.persistentsmanager.insert_url(url)


    def convert_action_url_to_absolute(self, form, base):
        form.action = urljoin(base, form.action)
        return form

    def print_to_file(self, item, filename):
        f = open("result/" + str(self.user.user_id) + "/" + filename, "w")
        f.write(item)
        f.close()

    def should_delta_page_be_stored_for_crawling(self, delta_page):
        for d_pages in self.tmp_delta_page_storage:
            if d_pages.url == delta_page.url:
                page_similarity = calculate_similarity_between_pages(delta_page, d_pages, clickable_weight=1,
                                                                     form_weight=0, link_weight=0)
                if page_similarity >= 0.9:
                    logging.debug("Equal page is already stored...")
                    return False
        for d_pages in self.get_all_crawled_deltapages_to_url(delta_page.url):
            if d_pages.url == delta_page.url:
                page_similarity = calculate_similarity_between_pages(delta_page, d_pages, clickable_weight=1,
                                                                     form_weight=0, link_weight=0)
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
        logging.debug("Get new ID")
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
        # logging.debug(str(clickable.html_class) + " : " + str(clickable.event))
        return True

    def initial_login(self, base_url, login_data):
        response_code, html_after_timeouts, new_clickables, forms, links, timemimg_requests = self._dynamic_analyzer.analyze(base_url, timeout=10)
        landing_page_loged_out = WebPage(-1, base_url, html_after_timeouts)
        landing_page_loged_out.clickables = new_clickables
        landing_page_loged_out.forms = forms
        landing_page_loged_out.links = links
        landing_page_loged_out.timeming_requests = timemimg_requests
        login_form = self.find_form_with_special_params(landing_page_loged_out, login_data)
        data = form_to_dict(login_form, login_data)
        data['history'] = ""
        data['__action_module__'] = "/Base_Box|0/Base_User_Login|login"
        url = urljoin(base_url.toString(), login_form.action)
        url = Url(url)
        response_code, html_after_timeouts, new_clickables, forms, links, timemimg_requests = self._dynamic_analyzer.analyze(url, timeout=30, method="POST", data=data)
        landing_page_loged_in = WebPage(-1, base_url, html_after_timeouts)
        landing_page_loged_in.clickables = new_clickables
        landing_page_loged_in.links = links
        landing_page_loged_in.timeming_requests = timemimg_requests
        landing_page_loged_in.forms = forms

        f = open("test1.txt", "w")
        f.write(landing_page_loged_out.toString())
        f.close()

        f = open("test2.txt", "w")
        f.write(landing_page_loged_in.toString())
        f.close()

        return True


class CrawlState(Enum):
    normal_page = 0
    event_generated_page = 1
    delta_page = 2
    analyze_login_page = 3
    login = 4


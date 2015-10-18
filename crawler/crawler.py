Copyright (C) 2015 Constantin Tschürtz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


from asyncio.tasks import sleep
import logging
import random
import sys
from enum import Enum
from copy import deepcopy
from urllib.parse import urljoin

from PyQt5.Qt import QApplication, QObject
from PyQt5.QtNetwork import QNetworkAccessManager

from core.eventexecutor import EventExecutor, XHRBehavior, EventResult
from core.formhandler import FormHandler
from core.clustermanager import ClusterManager
from core.jaekcore import JaekCore
from models.url import Url
from utils.asyncrequesthandler import AsyncRequestHandler
from utils.execptions import PageNotFound, LoginFailed
from models.deltapage import DeltaPage
from models.webpage import WebPage
from models.clickabletype import ClickableType
from utils.domainhandler import DomainHandler
from analyzer.mainanalyzer import MainAnalyzer
from utils.utils import calculate_similarity_between_pages, subtract_parent_from_delta_page, count_cookies


potential_logout_urls = []


class Crawler(JaekCore):
    def __init__(self, crawl_config, proxy="", port=0, database_manager=None):
        QObject.__init__(self)
        self.app = QApplication(sys.argv)
        self._network_access_manager = QNetworkAccessManager(self)
        #self._network_access_manager = self._dynamic_analyzer.networkAccessManager()

        self._event_executor = EventExecutor(self, proxy, port, crawl_speed=crawl_config.process_speed,
                                             network_access_manager=self._network_access_manager)
        self._dynamic_analyzer = MainAnalyzer(self, proxy, port, crawl_speed=crawl_config.process_speed,
                                          network_access_manager=self._network_access_manager)
        self._form_handler = FormHandler(self, proxy, port, crawl_speed=crawl_config.process_speed,
                                             network_access_manager=self._network_access_manager)



        self.domain_handler = None
        self.current_depth = 0
        self.crawl_with_login = False
        self.proxy = proxy
        self.port = port
        self.cookie_num = -1

        self.crawler_state = CrawlState.NormalPage
        self.crawl_config = crawl_config
        self.tmp_delta_page_storage = []  # holds the deltapages for further analyses
        self.url_frontier = []
        self.user = None
        self.page_id = 0
        self.current_depth = 0
        self.database_manager = database_manager

        self.cluster_manager = ClusterManager(self.database_manager) # dict with url_hash and

    def crawl(self, user):
        logging.debug("Crawl with userId: {}".format(user.username))
        self.user = user
        self.domain_handler = DomainHandler(self.crawl_config.start_page_url, self.database_manager, self.cluster_manager)
        self.async_request_handler = AsyncRequestHandler(self.database_manager)
        self.start_page_url = Url(self.crawl_config.start_page_url)
        self.database_manager.insert_url_into_db(self.start_page_url)

        if self.user.login_data is not None:
            self.crawl_with_login = True
            successfull, self.interactive_login_form_search = self._initial_login()


        round_counter = 0
        while True:
            logging.debug("=======================New Round=======================")
            current_page = None
            necessary_clicks = []  # Saves the actions the crawler need to reach a delta page
            parent_page = None  # Saves the parent of the delta-page (not other delta pages)
            previous_pages = []  # Saves all the pages the crawler have to pass to reach my delta-page
            delta_page = None


            if round_counter < 10:
                round_counter += 1
            else:
                # Need to do this to prevent memory leckages, issued by PyQT bindings or something else
                logging.debug("10 rounds over, renew critical classes...")
                round_counter = 0
                self._network_access_manager = None
                self._event_executor = None
                self._form_handler = None
                self._event_executor = None
                self._network_access_manager = QNetworkAccessManager(self)
                self._event_executor = EventExecutor(self, self.proxy, self.port, crawl_speed=self.crawl_config.process_speed,
                                             network_access_manager=self._network_access_manager)
                self._dynamic_analyzer = MainAnalyzer(self, self.proxy, self.port, crawl_speed=self.crawl_config.process_speed,
                                          network_access_manager=self._network_access_manager)
                self._form_handler = FormHandler(self, self.proxy, self.port, crawl_speed=self.crawl_config.process_speed,
                                             network_access_manager=self._network_access_manager)


            if len(self.tmp_delta_page_storage) > 0:
                self.crawler_state = CrawlState.DeltaPage
                current_page = self.tmp_delta_page_storage.pop(0)
                logging.debug("Processing Deltapage with ID: {}, {} deltapages left...".format(str(current_page.id),
                                                                                               str(len(
                                                                                                   self.tmp_delta_page_storage))))
                parent_page = current_page
                while isinstance(parent_page, DeltaPage):
                    necessary_clicks.insert(0,
                                            parent_page.generator)  # Insert as first element because of reverse order'
                    parent_page = self.database_manager.get_page_to_id(parent_page.parent_id)
                    if parent_page is None:
                        raise PageNotFound("This exception should never be raised...")
                    previous_pages.append(parent_page)
                # Now I'm reaching a non delta-page
                self.current_depth = parent_page.current_depth
                url_to_request = parent_page.url
                if current_page.generator.clickable_depth + 1 > self.crawl_config.max_click_depth:
                    logging.debug("Don't proceed with Deltapage(max click depth)...")
                    self.database_manager.store_delta_page(current_page)
                    continue

            else:
                logging.debug("Looking for the next url...")
                possible_urls = self.database_manager.get_all_unvisited_urls_sorted_by_hash()
                if len(possible_urls) > 0:
                    self.crawler_state = CrawlState.NormalPage
                    cluster_per_urls = []
                    for key in possible_urls:
                        cluster_per_urls.append((key, self.cluster_manager.calculate_cluster_per_visited_urls(key)))
                    next_url_hash, max_cluster_per_url = max(cluster_per_urls, key=lambda x: x[1])
                    possible_urls = possible_urls[next_url_hash]
                    url_to_request = possible_urls.pop(random.randint(0, len(possible_urls) - 1))
                    if url_to_request.depth_of_finding is None:
                        self.current_depth = 0
                    else:
                        self.current_depth = url_to_request.depth_of_finding + 1
                else:
                    break

            if self.crawler_state == CrawlState.NormalPage:
                if not self.domain_handler.is_in_scope(url_to_request):
                    logging.debug("Ignoring {} (Not in scope)... ".format(url_to_request.toString()))
                    self.database_manager.visit_url(url_to_request, None, 1000)
                    continue

                if url_to_request.depth_of_finding is not None:
                    if url_to_request.depth_of_finding + 1 > self.crawl_config.max_depth:
                        logging.debug("Ignoring {} (Max crawl depth)... ".format(url_to_request.toString()))
                        self.database_manager.visit_url(url_to_request, None, 1001)
                        continue

                plain_url_to_request = url_to_request.toString()
                if self.database_manager.url_visited(url_to_request):
                    logging.debug("Crawler tries to use url: {} twice".format(url_to_request.toString()))
                    continue

                if not self.cluster_manager.need_more_urls_of_this_type(url_to_request.url_hash):
                    self.database_manager.visit_url(url_to_request, None, 1002)
                    logging.debug("Seen enough urls from {} ".format(url_to_request.toString()))
                    continue

                current_page = None
                num_of_tries = 0
                logging.debug("Next Url is: {}".format(url_to_request.toString()))
                while current_page is None and num_of_tries < 3:
                    response_code, current_page = self._dynamic_analyzer.analyze(url_to_request, current_depth=self.current_depth)
                    self.domain_handler.complete_urls_in_page(current_page)
                    self.domain_handler.analyze_urls(current_page)
                    self.domain_handler.set_url_depth(current_page, self.current_depth)
                    self.async_request_handler.handle_requests(current_page)
                    num_of_tries += 1
                if current_page is None:
                    self.database_manager.visit_url(url_to_request, None, 1004)
                    logging.debug("Fetching url: {} fails.... continue".format(plain_url_to_request))
                    continue

                if self.crawl_with_login and self.cookie_num > 0:
                    num_cookies = count_cookies(self._network_access_manager, url_to_request)
                    logging.debug("Having {} cookies...".format(num_cookies))
                    if num_cookies < self.cookie_num or self._find_form_with_special_parameters(current_page, self.user.login_data, self.interactive_login_form_search)[0] is not None:
                        logging.debug("Too less cookies... possible logout!")
                        if not self._handle_possible_logout():
                            response_code, current_page = self._dynamic_analyzer.analyze(url_to_request, current_depth=self.current_depth)
                            self.domain_handler.complete_urls_in_page(current_page)
                            self.domain_handler.analyze_urls(current_page)
                            self.domain_handler.set_url_depth(current_page, self.current_depth)
                            self.async_request_handler.handle_requests(current_page)
                elif self.crawl_with_login \
                        and response_code in range(300, 350) \
                        and current_page.url != plain_url_to_request:
                    logging.debug("Redirect - Response code is: {} from {} to {}...".format(response_code, plain_url_to_request, current_page.url))
                    if not self._handle_possible_logout():
                        response_code, current_page = self._dynamic_analyzer.analyze(url_to_request, current_depth=self.current_depth)
                        self.domain_handler.complete_urls_in_page(current_page)
                        self.domain_handler.analyze_urls(current_page)
                        self.domain_handler.set_url_depth(current_page, self.current_depth)
                        self.async_request_handler.handle_requests(current_page)
                elif self.crawl_with_login and response_code in [200]:
                    if self._find_form_with_special_parameters(current_page, self.user.login_data, self.interactive_login_form_search)[0] is not None:
                        if not self._handle_possible_logout():
                            logging.debug("Loginpage was visible...relaod page and continue")
                            response_code, current_page = self._dynamic_analyzer.analyze(url_to_request, current_depth=self.current_depth)
                            self.domain_handler.complete_urls_in_page(current_page)
                            self.domain_handler.analyze_urls(current_page)
                            self.domain_handler.set_url_depth(current_page, self.current_depth)
                            self.async_request_handler.handle_requests(current_page)
                elif self.crawl_with_login and response_code in range(400,500):
                    logging.debug("Server responses with: {}...check if we are logged out".format(response_code))
                    if not self._handle_possible_logout():
                        logging.debug("Loginpage was visible...relaod page and continue")
                        response_code, current_page = self._dynamic_analyzer.analyze(url_to_request, current_depth=self.current_depth)
                        self.domain_handler.complete_urls_in_page(current_page)
                        self.domain_handler.analyze_urls(current_page)
                        self.domain_handler.set_url_depth(current_page, self.current_depth)
                        self.async_request_handler.handle_requests(current_page)

                current_page.current_depth = self.current_depth
                self.database_manager.store_web_page(current_page)

                for current_clickable_to_work_on in current_page.clickables:
                    current_clickable_to_work_on.clickable_depth = 0

                if response_code in range(300, 350) and current_page.url != plain_url_to_request:
                    wp_id = self.database_manager.get_id_to_url(current_page.url)
                    if wp_id is None or wp_id > 0:
                        logging.debug("Redirected page already seen, continue with next...")
                        self.database_manager.visit_url(url_to_request, wp_id, response_code, current_page.url)
                        continue  #Page was already seen
                    self.database_manager.visit_url(url_to_request, current_page.id, response_code, current_page.url)

                elif response_code > 399:
                    self.database_manager.visit_url(url_to_request, None, response_code)
                    logging.debug("{} returns code {}".format(url_to_request.toString(), response_code))
                    continue
                else:
                    self.database_manager.visit_url(url_to_request, current_page.id, response_code)
                self.domain_handler.extract_new_links_for_crawling(current_page)

            if self.crawler_state == CrawlState.DeltaPage:
                current_page.html = parent_page.html  # Assigning html
                logging.debug("Now at Deltapage: {}".format(current_page.id))
                self.database_manager.store_delta_page(current_page)

            num_clickables = len(current_page.clickables)
            counter = 1  # Just a counter for displaying progress
            errors = 0  # Count the errors(Missing preclickable or target elements)
            login_retries_per_clickable = 0  # Count the login_retries
            max_login_retires_per_clickable = 3
            max_errors = 3
            timeout_counter = 0
            current_working_clickable_number = 0
            if num_clickables > 0:
                logging.debug("Start executing events...")
            else:
                logging.debug("Page has no events. Cluster it and throw it to the others...")

            while current_working_clickable_number < len(current_page.clickables): # and login_retries_per_clickable < max_login_retires_per_clickable:
                current_clickable_to_work_on = current_page.clickables[current_working_clickable_number]
                if not self.should_execute_clickable(current_clickable_to_work_on):
                    current_clickable_to_work_on.clickable_type = ClickableType.IgnoredByCrawler
                    self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                    continue
                logging.debug(
                    "Processing Clickable Number {} from {}".format(str(counter), str(len(current_page.clickables))))
                counter += 1

                """
                If event is something like "onclick", take off the "on"
                """
                event = current_clickable_to_work_on.event
                if event[0:2] == "on":
                    event = event[2:]
                if current_clickable_to_work_on.clicked:
                    continue

                """
                If event is not supported, mark it so in the database and continue
                """
                if event not in self._event_executor.supported_events and "javascript:" not in event:
                    current_clickable_to_work_on.clickable_type = ClickableType.UnsupportedEvent
                    self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                    logging.debug("Unsupported event: {} in {}".format(event, current_clickable_to_work_on.toString()))
                    current_working_clickable_number += 1
                    continue
                """
                Because I want first a run without sending something to the backend, I distinguish if I know an element or not.
                If I know it(its clickable_type is set) I re-execute the event and let the ajax request pass.
                If I don't know it, I execute each clickable with an interception.
                """
                if current_clickable_to_work_on.clickable_type is not None:
                    """
                    The clickable was executed in the past, and has triggered an backend request. Know execute it again and let that request pass
                    """
                    xhr_behavior = XHRBehavior.ObserveXHR
                    event_result, delta_page = self._event_executor.execute(current_page, element_to_click=current_clickable_to_work_on,
                                                                           pre_clicks=necessary_clicks,
                                                                           xhr_options=xhr_behavior)
                else:
                    """
                    The clickable was never executed, so execute it with intercepting all backend requests.
                    """
                    xhr_behavior = XHRBehavior.InterceptXHR
                    event_result, delta_page = self._event_executor.execute(current_page, element_to_click=current_clickable_to_work_on,
                                                                           pre_clicks=necessary_clicks,
                                                                           xhr_options=xhr_behavior)

                if event_result == EventResult.UnsupportedTag:
                    current_clickable_to_work_on.clicked = True
                    current_clickable_to_work_on.clickable_type = ClickableType.UnsupportedEvent
                    self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                    current_working_clickable_number += 1
                    continue

                elif event_result == EventResult.ErrorWhileInitialLoading:
                    if timeout_counter < 10:
                        current_clickable_to_work_on.clicked = True
                        current_clickable_to_work_on.clickable_type = ClickableType.Error
                        self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                        timeout_counter += 1
                        current_working_clickable_number += 1
                        continue
                    else:
                        timeout_counter = 0
                        logging.debug("Too many loading errors... mark all clickables as error and continue")
                        for current_working_clickable_number in range(0, len(current_page.clickables)):
                            current_clickable_to_work_on = current_page.clickable[current_working_clickable_number]
                            current_clickable_to_work_on.clicked = True
                            current_clickable_to_work_on.clickable_type = ClickableType.Error
                            self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                            break
                        continue

                #Event execution error handling...
                elif event_result == EventResult.PreviousClickNotFound or event_result == EventResult.TargetElementNotFound:
                    if self.crawl_with_login:
                        if login_retries_per_clickable < max_login_retires_per_clickable:
                            if errors < max_errors:
                                current_clickable_to_work_on.clicked = False
                                errors += 1
                            else:
                                logging.debug("Too many event errors, checking for logout...")
                                self._handle_possible_logout()
                                login_retries_per_clickable += 1
                                errors = 0
                        else:
                            logging.debug("Max Loginretires per clickable - set clickable to error and go on...")
                            current_clickable_to_work_on.clickable_type = ClickableType.Error
                            login_retries_per_clickable = 0
                            self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                            errors = 0
                            current_working_clickable_number += 1
                        continue
                    else:
                        if errors < max_errors:
                            errors += 1
                        else:
                            logging.debug("Clickable {} times not found, continue with next...".format(max_errors))
                            errors = 0
                            current_clickable_to_work_on.clickable_type = ClickableType.Error
                            self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                            current_working_clickable_number += 1
                        continue
                elif event_result == EventResult.CreatesPopup:
                    current_clickable_to_work_on.clicked = True
                    current_clickable_to_work_on.links_to = delta_page.url
                    current_clickable_to_work_on.clickable_type = ClickableType.CreateNewWindow
                    new_url = Url(delta_page.url)
                    self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                    new_url = self.domain_handler.handle_url(new_url, None)
                    new_url.depth_of_finding = self.current_depth
                    self.database_manager.insert_url_into_db(new_url)
                    current_working_clickable_number += 1
                    continue

                else:
                    try:
                        delta_page.delta_depth = current_page.delta_depth + 1
                    except AttributeError:
                        delta_page.delta_depth = 1

                    if event_result == EventResult.URLChanged:
                        logging.debug("DeltaPage has new Url...{}".format(delta_page.url))
                        current_clickable_to_work_on.clicked = True
                        current_clickable_to_work_on.links_to = delta_page.url
                        current_clickable_to_work_on.clickable_type = ClickableType.Link
                        new_url = Url(delta_page.url)
                        self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                        if self.database_manager.insert_url_into_db(new_url): # Page does not exist
                            delta_page.id = self.get_next_page_id()
                            self.database_manager.visit_url(new_url, delta_page.id, 1000) #1000 is the code for a redirected url
                        else:
                            current_working_clickable_number += 1
                            continue
                    """
                    Everything works fine and I get a normal DeltaPage, now I have to:
                        - Assign the current depth to it -> DeltaPages have the same depth as its ParentPages
                        - Complete raw_db_urls of the deltapage and analyze it
                        - Analyze the Deltapage without addEventlisteners and timemimg check. This is done during event execution
                        - Substract the ParentPage, optional Parent + all previous visited DeltaPages, from the DeltaPage to get
                          the real DeltaPage
                        - Handle it after the result of the subtraction
                    """
                    current_clickable_to_work_on.clicked = True
                    current_clickable_to_work_on.clickable_depth = delta_page.delta_depth
                    delta_page.current_depth = self.current_depth
                    delta_page = self.domain_handler.complete_urls_in_page(delta_page)
                    delta_page = self.domain_handler.analyze_urls(delta_page)
                    delta_page = self.domain_handler.set_url_depth(delta_page, self.current_depth)
                    delta_page = self.async_request_handler.handle_requests(delta_page)

                    if self.crawler_state == CrawlState.NormalPage:
                        delta_page = subtract_parent_from_delta_page(current_page, delta_page)
                    if self.crawler_state == CrawlState.DeltaPage:
                        delta_page = subtract_parent_from_delta_page(current_page, delta_page)
                        for p in previous_pages:
                            delta_page = subtract_parent_from_delta_page(p, delta_page)
                    clickable_process_again = False

                    if len(delta_page.clickables) > 0 or len(delta_page.links) > 0 or len(
                            delta_page.ajax_requests) > 0 or len(delta_page.forms) > 0:
                        if len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            clickable_process_again = self.handle_delta_page_has_only_new_links(current_clickable_to_work_on, delta_page, current_page,
                                                                                  xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            clickable_process_again = self.handle_delta_page_has_only_ajax_requests(current_clickable_to_work_on, delta_page,
                                                                                      current_page, xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) == 0:
                            clickable_process_again = self.handle_delta_page_has_new_links_and_ajax_requests(current_clickable_to_work_on, delta_page,
                                                                                               current_page,
                                                                                               xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            clickable_process_again = self.handle_delta_page_has_only_new_clickables(current_clickable_to_work_on, delta_page,
                                                                                       current_page, xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            clickable_process_again = self.handle_delta_page_has_new_links_and_clickables(current_clickable_to_work_on, delta_page,
                                                                                            current_page, xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            clickable_process_again = self.handle_delta_page_has_new_clickables_and_ajax_requests(current_clickable_to_work_on,
                                                                                                    delta_page,
                                                                                                    current_page,
                                                                                                    xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) == 0:
                            clickable_process_again = self.handle_delta_page_has_new_links_ajax_requests__clickables(current_clickable_to_work_on,
                                                                                                       delta_page,
                                                                                                       current_page,
                                                                                                       xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            clickable_process_again = self.handle_delta_page_has_only_new_forms(current_clickable_to_work_on, delta_page, current_page,
                                                                                  xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            clickable_process_again = self.handle_delta_page_has_new_links_and_forms(current_clickable_to_work_on, delta_page,
                                                                                       current_page, xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            clickable_process_again = self.handle_delta_page_has_new_forms_and_ajax_requests(current_clickable_to_work_on, delta_page,
                                                                                               current_page,
                                                                                               xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) == 0 and len(delta_page.forms) != 0:
                            clickable_process_again = self.handle_delta_page_has_new_links_forms_ajax_requests(current_clickable_to_work_on, delta_page,
                                                                                                 current_page,
                                                                                                 xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            clickable_process_again = self.handle_delta_page_has_new_clickable_and_forms(current_clickable_to_work_on, delta_page,
                                                                                           current_page, xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) == 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            clickable_process_again = self.handle_delta_page_has_new_links_clickables_forms(current_clickable_to_work_on, delta_page,
                                                                                              current_page,
                                                                                              xhr_behavior)

                        elif len(delta_page.links) == 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            clickable_process_again = self.handle_delta_page_has_new_clickables_forms_ajax_requests(current_clickable_to_work_on,
                                                                                                      delta_page,
                                                                                                      current_page,
                                                                                                      xhr_behavior)

                        elif len(delta_page.links) != 0 and len(delta_page.ajax_requests) != 0 and len(
                                delta_page.clickables) != 0 and len(delta_page.forms) != 0:
                            clickable_process_again = self.handle_delta_page_has_new_links_clickables_forms_ajax_requests(current_clickable_to_work_on,
                                                                                                            delta_page,
                                                                                                            current_page,
                                                                                                            xhr_behavior)

                        else:
                            logging.debug("Nothing matches...")
                            logging.debug("    Clickables: " + str(len(delta_page.clickables)))
                            logging.debug("    Links: " + str(len(delta_page.links)))
                            logging.debug("    Forms: " + str(len(delta_page.forms)))
                            logging.debug("    AjaxRequests: " + str(len(delta_page.ajax_requests)))

                        if clickable_process_again :
                            # If we want to process the clickable again. We pop it out of the list and append it at the end
                            # Important: not increase the counter here
                            current_clickable_to_work_on.clicked = False
                            current_clickable_to_work_on = current_page.clickables.pop(current_working_clickable_number)
                            current_page.clickables.append(current_clickable_to_work_on)
                        else:
                             current_working_clickable_number += 1
                    else:
                        current_clickable_to_work_on.clickable_type = ClickableType.UIChange
                        self.database_manager.update_clickable(current_page.id, current_clickable_to_work_on)
                        current_working_clickable_number += 1


            if self.crawler_state == CrawlState.NormalPage:
                self.cluster_manager.add_webpage_to_cluster(current_page)
        logging.debug("Crawling is done...")

    def handle_delta_page_has_only_new_links(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        if delta_page.id == -1:
            delta_page.id = self.get_next_page_id()
        delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
        self.domain_handler.extract_new_links_for_crawling(delta_page)
        self.database_manager.store_delta_page(delta_page)
        self.database_manager.update_clickable(parent_page.id, clickable)
        return False

    def handle_delta_page_has_only_new_clickables(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
        if delta_page.id == -1:
            delta_page.id = self.get_next_page_id()
        self.database_manager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
        return False

    def handle_delta_page_has_only_new_forms(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
        if delta_page.id == -1:
            delta_page.id = self.get_next_page_id()
        self.database_manager.store_delta_page(delta_page)
        self.domain_handler.extract_new_links_for_crawling(delta_page)
        self.database_manager.update_clickable(parent_page.id, clickable)
        return False

    def handle_delta_page_has_only_ajax_requests(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        self.domain_handler.extract_new_links_for_crawling(delta_page)
        clickable.clickable_type = ClickableType.SendingAjax
        if xhr_behavior == XHRBehavior.ObserveXHR:
            self.database_manager.extend_ajax_requests_to_webpage(parent_page, delta_page.ajax_requests)
            return  False
        else:
            return True

    def handle_delta_page_has_new_links_and_clickables(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
        if delta_page.id == -1:
            delta_page.id = self.get_next_page_id()
        self.domain_handler.extract_new_links_for_crawling(delta_page)
        self.database_manager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
        return False

    def handle_delta_page_has_new_links_and_forms(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
        if delta_page.id == -1:
            delta_page.id = self.get_next_page_id()
        self.domain_handler.extract_new_links_for_crawling(delta_page)
        self.database_manager.store_delta_page(delta_page)
        self.database_manager.update_clickable(parent_page.id, clickable)
        return False

    def handle_delta_page_has_new_links_and_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                          xhr_behavior=None):
        if xhr_behavior == XHRBehavior.ObserveXHR:
            delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
            if delta_page.id == -1:
               delta_page.id = self.get_next_page_id()
            self.domain_handler.extract_new_links_for_crawling(delta_page)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.database_manager.store_delta_page(delta_page)
            self.database_manager.update_clickable(parent_page.id, clickable)
            return False
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return True

    def handle_delta_page_has_new_clickable_and_forms(self, clickable, delta_page, parent_page=None, xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
        if delta_page.id == -1:
            delta_page.id = self.get_next_page_id()
        self.database_manager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
        return False

    def handle_delta_page_has_new_clickables_and_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                               xhr_behavior=None):
        if xhr_behavior == XHRBehavior.ObserveXHR:
            delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
            if delta_page.id == -1:
                delta_page.id = self.get_next_page_id()
            self.domain_handler.extract_new_links_for_crawling(delta_page)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.database_manager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
            return False
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return True

    def handle_delta_page_has_new_forms_and_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                          xhr_behavior=None):
        if xhr_behavior == XHRBehavior.ObserveXHR:
            delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
            if delta_page.id == -1:
                delta_page.id = self.get_next_page_id()
            self.domain_handler.extract_new_links_for_crawling(delta_page)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.database_manager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
            return False
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return True

    def handle_delta_page_has_new_links_clickables_forms(self, clickable, delta_page, parent_page=None,
                                                         xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
        if delta_page.id == -1:
            delta_page.id = self.get_next_page_id()
        self.domain_handler.extract_new_links_for_crawling(delta_page)
        delta_page.generator_requests.extend(delta_page.ajax_requests)
        delta_page.ajax_requests = []
        self.database_manager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
        return False

    def handle_delta_page_has_new_links_forms_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                            xhr_behavior=None):
        if xhr_behavior == XHRBehavior.ObserveXHR:
            delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
            if delta_page.id == -1:
                delta_page.id = self.get_next_page_id()
            self.domain_handler.extract_new_links_for_crawling(delta_page)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.database_manager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
            return False
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return True

    def handle_delta_page_has_new_clickables_forms_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                                 xhr_behavior=None):
        if xhr_behavior == XHRBehavior.ObserveXHR:
            delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
            self.domain_handler.extract_new_links_for_crawling(delta_page)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            if delta_page.id == -1:
                delta_page.id = self.get_next_page_id()
            self.database_manager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
            return False
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return True


    def handle_delta_pages_has_new_links_clickables_forms(self, clickable, delta_page, parent_page=None,
                                                          xhr_behavior=None):
        delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
        self.domain_handler.extract_new_links_for_crawling(delta_page)
        if delta_page.id == -1:
            delta_page.id = self.get_next_page_id()
        self.database_manager.update_clickable(parent_page.id, clickable)
        if self.should_delta_page_be_stored_for_crawling(delta_page):
            self._store_delta_page_for_crawling(delta_page)
        return False

    def handle_delta_page_has_new_links_ajax_requests__clickables(self, clickable, delta_page, parent_page=None,
                                                                  xhr_behavior=None):
        if xhr_behavior == XHRBehavior.ObserveXHR:
            delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
            if delta_page.id == -1:
                delta_page.id = self.get_next_page_id()
            self.domain_handler.extract_new_links_for_crawling(delta_page)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.database_manager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
            return False
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return True

    def handle_delta_page_has_new_links_clickables_forms_ajax_requests(self, clickable, delta_page, parent_page=None,
                                                                       xhr_behavior=None):
        if xhr_behavior == XHRBehavior.ObserveXHR:
            delta_page.generator.clickable_type = ClickableType.CreatesNewNavigatables
            if delta_page.id == -1:
                delta_page.id = self.get_next_page_id()
            self.domain_handler.extract_new_links_for_crawling(delta_page)
            delta_page.generator_requests.extend(delta_page.ajax_requests)
            delta_page.ajax_requests = []
            self.database_manager.update_clickable(parent_page.id, clickable)
            if self.should_delta_page_be_stored_for_crawling(delta_page):
                self._store_delta_page_for_crawling(delta_page)
            return False
        else:
            clickable.clickable_type = ClickableType.SendingAjax
            return True


    #def find_form_with_special_parameters(self, page, login_data, interactive_search=True):
    #    logging.debug("Searching for form with given parameter names...")
    #    keys = list(login_data.keys())
    #    data1 = keys[0]
    #    data2 = keys[1]
    #    for form in page.forms:
    #        if form.toString().find(data1) > -1 and form.toString().find(data2) > -1:
    #            logging.debug("Login form found, without clicking...")
    #            self.interactive_login_form_search= False
    #            return form, None
    #    if interactive_search:
    #        for clickable in page.clickables:
    #            tmp_page = deepcopy(page)
    #            event_state, delta_page = self._event_executor.execute(tmp_page, element_to_click=clickable)
    #            if delta_page is None:
    #                continue
    #            delta_page = self.domain_handler.complete_urls_in_page(delta_page)
    #            delta_page = self.domain_handler.analyze_urls(delta_page)
    #            if event_state == EventResult.Ok:
    #                for form in delta_page.forms:
    #                    if form.toString().find(data1) > -1 and form.toString().find(data2) > -1:
    #                        logging.debug("Login form found, after clicking {}".format(clickable.toString()))
    #                        return form, clickable
    #    return None, None

    @staticmethod
    def convert_action_url_to_absolute(form, base):
        form.action = urljoin(base, form.action)
        return form

    def print_to_file(self, item, filename):
        f = open("result/"+ str(filename), "w")
        f.write(item)
        f.close()

    def should_delta_page_be_stored_for_crawling(self, delta_page):
        for d_pages in self.tmp_delta_page_storage:
            if d_pages.url == delta_page.url:
                page_similarity = calculate_similarity_between_pages(delta_page, d_pages, clickable_weight=1,
                                                                     form_weight=1, link_weight=1)
                if page_similarity >= 0.9:
                    logging.debug("Equal page is already stored...")
                    return False
        for d_pages in self.get_all_crawled_deltapages_to_url(delta_page.url):
            if d_pages.url == delta_page.url:
                page_similarity = calculate_similarity_between_pages(delta_page, d_pages, clickable_weight=1,
                                                                     form_weight=1, link_weight=1)
                if page_similarity >= 0.9:
                    logging.debug("Equal page is already seen...")
                    return False
        return True

    def _store_delta_page_for_crawling(self, delta_page):
        self.tmp_delta_page_storage.append(delta_page)


    def get_all_stored_delta_pages(self):
        return self.tmp_delta_page_storage

    def get_all_crawled_deltapages_to_url(self, url):
        result = self.database_manager.get_all_crawled_delta_pages(url)
        return result

    def get_next_page_id(self):
        tmp = self.page_id
        self.page_id += 1
        return tmp


    def extend_ajax_requests_to_webpage(self, web_page, ajax_requests):
        web_page.ajax_requests.extend(ajax_requests)
        self.database_manager._extend_ajax_requests_to_webpage(web_page, ajax_requests)

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

    #def initial_login(self):
    #    logging.debug("Initial Login...")
    #    self._page_with_loginform_logged_out = self._get_webpage(self.user.url_with_login_form)
    #    num_of_cookies_before_login = count_cookies(self._network_access_manager, self.user.url_with_login_form)
    #    logging.debug("Number of cookies before initial login: {}".format(num_of_cookies_before_login))
    #    self._login_form, login_clickables = self.find_form_with_special_parameters(self._page_with_loginform_logged_out, self.user.login_data)
    #    if self._login_form is None:
    #        #f = open("No_login_form.txt", "w")
    #        #f.write(self._page_with_loginform_logged_out.html)
    #        #f.close()
    #        raise LoginFailed("Cannot find Login form, please check the parameters...")

    #    page_after_login = self._login_and_return_webpage(self._login_form, self._page_with_loginform_logged_out, self.user.login_data, login_clickables)
    #    if page_after_login is None:
    #        raise LoginFailed("Cannot load loginpage anymore...stop...")
    #    login_successfull = calculate_similarity_between_pages(self._page_with_loginform_logged_out, page_after_login) < 0.5
    #    if login_successfull:
    #        num_cookies_after_login = count_cookies(self._network_access_manager, self.user.url_with_login_form)
    #        if num_cookies_after_login > num_of_cookies_before_login:
    #            self.cookie_num = num_cookies_after_login
    #        logging.debug("Initial login successfull!")
    #        return True
    #    raise LoginFailed("Cannot login, sorry...")

    #def _login_and_return_webpage(self, login_form, page_with_login_form=None, login_data=None, login_clickable= None):
    #    if page_with_login_form is None:
    #        page_with_login_form = self._page_with_loginform_logged_out
    #    try:
    #        if login_clickable is not None:
    #            tmp_page = deepcopy(page_with_login_form)
    #            event_state, page_with_login_form = self._event_executor.execute(tmp_page, element_to_click=login_clickable)
    #            if event_state == EventResult.ErrorWhileInitialLoading:
    #                sleep(2000)
    #                event_state, page_with_login_form = self._event_executor.execute(tmp_page, element_to_click=login_clickable)
    #                if event_state == EventResult.ErrorWhileInitialLoading:
    #                    logging.debug("Two time executing fails.. stop crawling")
    #                    return None
    #            self.domain_handler.complete_urls_in_page(page_with_login_form)
    #            self.domain_handler.analyze_urls(page_with_login_form)
    #            self.async_request_handler.handle_requests(page_with_login_form)
    #        logging.debug("Start submitting login form...")
    #        response_code, html_after_timeouts, new_clickables, forms, links, timemimg_requests = self._form_handler.submit_form(login_form, page_with_login_form, login_data)
    #    except ValueError:
    #        return None
    #    #TODO: Put building of Webpage inside submit function
    #    page_after_login = WebPage(-1, page_with_login_form.url, html_after_timeouts)
    #    page_after_login.clickables = new_clickables
    #    page_after_login.links = links
    #    page_after_login.timing_requests = timemimg_requests
    #    page_after_login.forms = forms
    #    self.domain_handler.complete_urls_in_page(page_after_login)
    #    self.domain_handler.analyze_urls(page_after_login)
    #    self.async_request_handler.handle_requests(page_after_login)
    #    return page_after_login

    #def handle_possible_logout(self):
    #    """
    #    Handles a possible logout
    #    :return: True is we were not logged out and false if we were logged out
    #    """
    #    retries = 0
    #    max_retries = 3
    #    while retries < max_retries:
    #        logging.debug("Start with relogin try number: {}".format(retries+1))
    #        page_with_login_form = self._get_webpage(self.user.url_with_login_form)
    #        login_form, login_clickable = self.find_form_with_special_parameters(page_with_login_form, self.user.login_data, self.interactive_login_form_search)
    #        if login_form is not None: #So login_form is visible, we are logged out
    #            logging.debug("Logout detected, visible login form...")
    #            hopefully_reloggedin_page = self._login_and_return_webpage(login_form, page_with_login_form, self.user.login_data, login_clickable)
    #            if hopefully_reloggedin_page is None:
    #                retries += 1
    #                logging.debug("Relogin attempt number {} failed".format(retries))
    #                sleep(2000)
    #            else:
    #                login_form, login_clickable = self.find_form_with_special_parameters(hopefully_reloggedin_page, self.user.login_data)
    #                if login_form is None:
    #                    logging.debug("Relogin successfull...continue")
    #                    return False
    #                else:
    #                    logging.debug("Relogin fails, loginform is still present...")
    #                    retries += 1
    #                    sleep(2000)
    #        else:
    #            logging.debug("Login Form is not there... we can continue (I hope)")
    #            if retries < 3:
    #                return True
    #            else:
    #                return False
    #    raise LoginFailed("We cannot login anymore... stop crawling here")

    #def _get_webpage(self, url):
    #    response_code, result = self._dynamic_analyzer.analyze(url, timeout=10)
    #    self.domain_handler.complete_urls_in_page(result)
    #    self.domain_handler.analyze_urls(result)
    #    self.async_request_handler.handle_requests(result)
    #    return result

class CrawlState(Enum):
    NormalPage = 0
    EventGeneratedPage = 1
    DeltaPage = 2
    AnalyzeLoginPage = 3
    Login = 4


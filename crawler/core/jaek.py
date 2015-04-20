from asyncio.tasks import sleep
import logging
from PyQt5.Qt import QApplication, QObject
from PyQt5.QtNetwork import QNetworkAccessManager
import sys
from copy import deepcopy
from analyzer.mainanalyzer import MainAnalyzer
from core.eventexecutor import EventResult, EventExecutor
from core.formhandler import FormHandler
from models.webpage import WebPage
from utils.asyncrequesthandler import AsyncRequestHandler
from utils.execptions import LoginFailed
from utils.utils import count_cookies, calculate_similarity_between_pages

__author__ = 'constantin'

class Jaek(QObject):


    def __init__(self, config, proxy="", port=0, database_manager=None):
        QObject.__init__(self)
        self.app = QApplication(sys.argv)
        self._network_access_manager = QNetworkAccessManager(self)
        self.user = None
        self.proxy = proxy
        self.port = port
        self.config = config
        self.database_manager = database_manager
        self.domain_handler = None
        self.process_with_login = False
        self.async_request_handler = AsyncRequestHandler(self.database_manager)

        self._event_executor = EventExecutor(self, proxy, port, crawl_speed=config.process_speed,
                                             network_access_manager=self._network_access_manager)
        self._dynamic_analyzer = MainAnalyzer(self, proxy, port, crawl_speed=config.process_speed,
                                          network_access_manager=self._network_access_manager)
        self._form_handler = FormHandler(self, proxy, port, crawl_speed=config.process_speed,
                                             network_access_manager=self._network_access_manager)

        self.cookie_num = -1

    def find_form_with_special_parameters(self, page, login_data, interactive_search=True):
        keys = list(login_data.keys())
        data1 = keys[0]
        data2 = keys[1]
        for form in page.forms:
            if form.toString().find(data1) > -1 and form.toString().find(data2) > -1:
                logging.debug("Login form found, without clicking...")
                return form, None
        if interactive_search:
            for clickable in page.clickables:
                tmp_page = deepcopy(page)
                event_state, delta_page = self._event_executor.execute(tmp_page, element_to_click=clickable)
                delta_page = self.domain_handler.complete_urls_in_page(delta_page)
                delta_page = self.domain_handler.analyze_urls(delta_page)
                if event_state == EventResult.Ok:
                    for form in delta_page.forms:
                        if form.toString().find(data1) > -1 and form.toString().find(data2) > -1:
                            logging.debug("Login form found, after clicking {}".format(clickable.toString()))
                            return form, clickable
        return None, None


    def initial_login(self):
        logging.debug("Initial Login...")
        self._page_with_loginform_logged_out = self._get_webpage(self.user.url_with_login_form)
        self.domain_handler.complete_urls_in_page(self._page_with_loginform_logged_out)
        self.domain_handler.analyze_urls(self._page_with_loginform_logged_out)
        #self.domain_handler.set_url_depth(current_page, self.current_depth)
        self.async_request_handler.handle_requests(self._page_with_loginform_logged_out)
        num_cookies_before_login = count_cookies(self._network_access_manager, self.user.url_with_login_form)
        #logging.debug(self._page_with_loginform_logged_out.toString())
        self._login_form, login_clickables = self.find_form_with_special_parameters(self._page_with_loginform_logged_out, self.user.login_data)
        if self._login_form is None:
            raise LoginFailed("Cannot find Login form, please check the parameters...")

        page_with_loginform_logged_in = self._login_and_return_webpage(self._login_form, self._page_with_loginform_logged_out, self.user.login_data, login_clickables)
        self.domain_handler.complete_urls_in_page(page_with_loginform_logged_in)
        self.domain_handler.analyze_urls(page_with_loginform_logged_in)
        #self.domain_handler.set_url_depth(page_with_loginform_logged_in, self.current_depth)
        self.async_request_handler.handle_requests(page_with_loginform_logged_in)
        login_successfull = calculate_similarity_between_pages(self._page_with_loginform_logged_out, page_with_loginform_logged_in) < 0.5
        if login_successfull:
            num_cookies_after_login = count_cookies(self._network_access_manager, self.user.url_with_login_form)
            if num_cookies_after_login > num_cookies_before_login:
                self.cookie_num = num_cookies_after_login
            logging.debug("Initial login successfull!")
            return True
        return False

    def _login_and_return_webpage(self, login_form, page_with_login_form=None, login_data=None, login_clickable= None):
        if page_with_login_form is None:
            page_with_login_form = self._page_with_loginform_logged_out
        try:
            if login_clickable is not None:
                tmp_page = deepcopy(page_with_login_form)
                event_state, page_with_login_form = self._event_executor.execute(tmp_page, element_to_click=login_clickable)
                self.domain_handler.complete_urls_in_page(page_with_login_form)
                self.domain_handler.analyze_urls(page_with_login_form)
            response_code, html_after_timeouts, new_clickables, forms, links, timemimg_requests = self._form_handler.submit_form(login_form, page_with_login_form, login_data)
        except ValueError:
            return None
        landing_page_logged_in = WebPage(-1, page_with_login_form.url, html_after_timeouts)
        landing_page_logged_in.clickables = new_clickables
        landing_page_logged_in.links = links
        landing_page_logged_in.timing_requests = timemimg_requests
        landing_page_logged_in.forms = forms

        return landing_page_logged_in

    def handle_possible_logout(self):
        retries = 0
        max_retries = 3
        while retries < max_retries:
            page_with_login_form = self._get_webpage(self.user.url_with_login_form)
            self.domain_handler.complete_urls_in_page(page_with_login_form)
            self.domain_handler.analyze_urls(page_with_login_form)
            self.async_request_handler.handle_requests(page_with_login_form)
            login_form, login_clickable = self.find_form_with_special_parameters(page_with_login_form, self.user.login_data)
            if login_form is not None: #So login_form is visible, we are logged out
                logging.debug("Logout detected, visible login form...")
                page = self._login_and_return_webpage(login_form, page_with_login_form, self.user.login_data, login_clickable)
                self.domain_handler.complete_urls_in_page(page)
                self.domain_handler.analyze_urls(page)
                self.async_request_handler.handle_requests(page)
                retries += 1
                if calculate_similarity_between_pages(page, page_with_login_form) < 0.5:
                    logging.debug("Relogin successfull...continue")
                    return
                else:
                    logging.debug("Relogin attempt number {} failed".format(retries))
                    sleep(2000)
            else:
                logging.debug("Login Form is not there... we can continue (I hope)")
                return
        raise LoginFailed("We cannot login anymore... stop crawling here")

    def _get_webpage(self, url):
        response_code, result = self._dynamic_analyzer.analyze(url, timeout=10)
        return result
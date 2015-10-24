'''
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
'''

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

class JaekCore(QObject):


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
        self.interactive_login_form_search = False

    def _find_form_with_special_parameters(self, page, login_data, interactive_search=True):
        keys = list(login_data.keys())
        data1 = keys[0]
        data2 = keys[1]
        for form in page.forms:
            if form.toString().find(data1) > -1 and form.toString().find(data2) > -1:
                return form, None
        if interactive_search:
            for clickable in page.clickables:
                tmp_page = deepcopy(page)
                event_state, delta_page = self._event_executor.execute(tmp_page, element_to_click=clickable)
                if delta_page is None:
                    sleep(2000)
                    event_state, delta_page = self._event_executor.execute(tmp_page, element_to_click=clickable)
                if delta_page is None:
                    continue
                delta_page = self.domain_handler.complete_urls_in_page(delta_page)
                delta_page = self.domain_handler.analyze_urls(delta_page)
                if event_state == EventResult.Ok:
                    for form in delta_page.forms:
                        if form.toString().find(data1) > -1 and form.toString().find(data2) > -1:
                            return form, clickable
        return None, None

    def _initial_login(self):
        logging.debug("Initial Login...")
        self._page_with_loginform_logged_out = self._get_webpage(self.user.url_with_login_form)
        num_of_cookies_before_login = count_cookies(self._network_access_manager, self.user.url_with_login_form)
        logging.debug("Number of cookies before initial login: {}".format(num_of_cookies_before_login))
        self._login_form, login_clickables = self._find_form_with_special_parameters(self._page_with_loginform_logged_out, self.user.login_data)
        if self._login_form is None:
            f = open("No_login_form.txt", "w")
            f.write(self._page_with_loginform_logged_out.html)
            f.close()
            raise LoginFailed("Cannot find Login form, please check the parameters...")

        page_after_login = self._login_and_return_webpage(self._login_form, self._page_with_loginform_logged_out, self.user.login_data, login_clickables)
        if page_after_login is None:
            raise LoginFailed("Cannot load loginpage anymore...stop...")
        login_successfull = calculate_similarity_between_pages(self._page_with_loginform_logged_out, page_after_login) < 0.5
        if login_successfull:
            num_cookies_after_login = count_cookies(self._network_access_manager, self.user.url_with_login_form)
            if num_cookies_after_login > num_of_cookies_before_login:
                self.cookie_num = num_cookies_after_login
            logging.debug("Initial login successfull!")
            if login_clickables is not None:
                return True, True # If we login with a click
            else:
                return True, False # If we don't login with a click
        raise LoginFailed("Cannot login, sorry...")

    def _login_and_return_webpage(self, login_form, page_with_login_form=None, login_data=None, login_clickable= None):
        if page_with_login_form is None:
            page_with_login_form = self._page_with_loginform_logged_out
        try:
            if login_clickable is not None:
                tmp_page = deepcopy(page_with_login_form)
                event_state, page_with_login_form = self._event_executor.execute(tmp_page, element_to_click=login_clickable)
                if event_state == EventResult.ErrorWhileInitialLoading:
                    sleep(2000)
                    event_state, page_with_login_form = self._event_executor.execute(tmp_page, element_to_click=login_clickable)
                    if event_state == EventResult.ErrorWhileInitialLoading:
                        logging.debug("Two time executing fails.. stop crawling")
                        return None
                self.domain_handler.complete_urls_in_page(page_with_login_form)
                self.domain_handler.analyze_urls(page_with_login_form)
                self.async_request_handler.handle_requests(page_with_login_form)
            logging.debug("Start submitting login form...")
            response_code, html_after_timeouts, new_clickables, forms, links, timemimg_requests = self._form_handler.submit_form(login_form, page_with_login_form, login_data)
        except ValueError:
            return None
        #TODO: Put building of Webpage inside submit function
        page_after_login = WebPage(-1, page_with_login_form.url, html_after_timeouts)
        page_after_login.clickables = new_clickables
        page_after_login.links = links
        page_after_login.timing_requests = timemimg_requests
        page_after_login.forms = forms
        self.domain_handler.complete_urls_in_page(page_after_login)
        self.domain_handler.analyze_urls(page_after_login)
        self.async_request_handler.handle_requests(page_after_login)
        return page_after_login

    def _handle_possible_logout(self):
        """
        Handles a possible logout
        :return: True is we were not logged out and false if we were logged out
        """
        retries = 0
        max_retries = 3
        while retries < max_retries:
            logging.debug("Start with relogin try number: {}".format(retries+1))
            page_with_login_form = self._get_webpage(self.user.url_with_login_form)
            login_form, login_clickable = self._find_form_with_special_parameters(page_with_login_form, self.user.login_data, self.interactive_login_form_search)
            if login_form is not None:
            #So login_form is visible, we are logged out
                logging.debug("Logout detected, visible login form...")
                hopefully_reloggedin_page = self._login_and_return_webpage(login_form, page_with_login_form, self.user.login_data, login_clickable)
                if hopefully_reloggedin_page is None:
                    retries += 1
                    logging.debug("Relogin attempt number {} failed".format(retries))
                    sleep(2000)
                else:
                    login_form, login_clickable = self._find_form_with_special_parameters(hopefully_reloggedin_page, self.user.login_data)
                    if login_form is None:
                        logging.debug("Relogin successfull...continue")
                        return False
                    else:
                        logging.debug("Relogin fails, loginform is still present...")
                        retries += 1
                        sleep(2000)
            else:
                logging.debug("Login form is not there... we can continue (I hope)")
                if retries < 3:
                    return True
                else:
                    return False
        raise LoginFailed("We cannot login anymore... stop crawling here")


    def _get_webpage(self, url):
        response_code, result = self._dynamic_analyzer.analyze(url, timeout=10)
        self.domain_handler.complete_urls_in_page(result)
        self.domain_handler.analyze_urls(result)
        self.async_request_handler.handle_requests(result)
        return result

    def _check_login_status_with_cookies(self):
        if self.cookie_num > 0:
            current_cookie_num = count_cookies(self._network_access_manager, self.user.url_with_login_form)
            return current_cookie_num >= self.cookie_num
        return True

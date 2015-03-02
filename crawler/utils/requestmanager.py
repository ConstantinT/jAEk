'''
Created on 01.03.2015

@author: constantin
'''
import logging
from asyncio.tasks import sleep
from utils.execptions import LoginErrorException, LoginFormNotFoundException
from utils.utils import form_to_json
from requests.utils import dict_from_cookiejar
import requests

class RequestManager(object):


    def __init__(self, crawl_loged_in, crawler, start_page_url ,login_data = None, url_with_login_form = None, proxy = "", port = 0):
        
        self._crawl_loged_in = crawl_loged_in
        self._login_data = login_data
        self._crawler = crawler
        self._url_with_login_form = url_with_login_form
        self.start_page_url = start_page_url
        self.session_handler = None
        #self.headers = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.94 Safari/537.36'
        self.headers = "jÄk was here..."
        self.session_handler = requests.Session()
        self.session_handler.headers.update({"User-Agent":self.headers})
        
        if proxy != "" and port != 0:
            self.request_proxies = {"https": proxy + ":" + str(port)}
        else:
            self.request_proxies = None
        
    def fetch_page(self, url):
        logging.debug("Fetching {} ... ".format(url))
       
        
        if not self._crawl_loged_in:
            response_url, response_code, html, response_history = self.__fetch_page(url)
            return response_url, response_code, html, self.session_handler.cookies, response_history
        else:
            response_url, response_code, html, response_history = self.__fetch_page(url)
              
            if len(response_history) > 1:
                if response_url != url.toString():
                    logging.debug("Possible logout, multiple redirects...")
                    go_on = self.handling_possible_logout()
                    if not go_on:
                        raise LoginErrorException("Relogin failed...")
                    else:
                        response_url, response_code, html, response_history = self.__fetch_page(url) 
            if len(self.session_handler.cookies) < len(self.login_cookie_keys) * .8:
                logging.debug("Possible logout, too less cookies...")
                go_on = self.handling_possible_logout()
                if not go_on:
                    raise LoginErrorException("Relogin failed...") 
                else:
                    response_url, response_code, html, response_history = self.__fetch_page(url) 

            return response_url, response_code, html, self.session_handler.cookies, response_history
                       
    def get(self, url):
        return self.session_handler.get(url, proxies=self.request_proxies, verify=False), self.session_handler.cookies
    
    
    def __fetch_page(self, url):
        counter = 0 
        while True:
            try:
                response = self.session_handler.get(url, proxies=self.request_proxies, verify=False)
                html = response.text
                response_url = response.url
                response_code = response.status_code 
                break
            except Exception:
                logging.debug("Exception during fetching ressource occours...")
                counter += 1
                if counter == 3:
                    logging.debug("Getting Ressource {} not possible...continue with next".format(url))
                    html = None
                    response_url = url
                    response_code = 666
                sleep(2)
        return response_url, response_code, html, response.history
        
        """
    Returns if we can go on or an unrecoverable error occurs
    """ 
    def handling_possible_logout(self):
        num_retries = 0
        max_num_retries = 3 # We try 3 times to login...
        
        landing_page = self._crawler.get_webpage_without_timeming_analyses(self.start_page_url)
        if self._crawler.page_handler.calculate_similarity_between_pages(landing_page, self.landing_page_loged_in) > .8:
            logging.debug("No logout...continue processing")
            return True
        logging.debug("Logout detected...")
        while(num_retries < max_num_retries ):
            logging.debug("Try login number " + str(num_retries+1))
            login_page = self._crawler.get_webpage_without_timeming_analyses(self._url_with_login_form)
            login_form = self._crawler.find_login_form(login_page, self._login_data)
            if login_form is None:
                raise LoginFormNotFoundException("Could not find login form")
            self.login(self._login_data, login_form)
            landing_page_after_login_try = self._crawler.get_webpage_without_timeming_analyses(self.start_page_url)
            if self._crawler.page_handler.calculate_similarity_between_pages(self.landing_page_loged_in, landing_page_after_login_try) > .9:
                logging.debug("Re login succesfull....continue processing")
                return True
            else:
                logging.debug("Login not successfull...")
                num_retries += 1
                sleep(2)
        logging.debug("All loging attempts failed...stop crawling")          
        return False
    
    def initial_login(self):
        logging.debug("Crawling with login...")
        login_page = self._crawler.get_webpage_without_timeming_analyses(self._url_with_login_form)
        login_form = self._crawler.find_login_form(login_page, self._login_data)
        if login_form is None:
            raise LoginFormNotFoundException("Could not find login form")
        
        if self._url_with_login_form == self.start_page_url:
            self.landing_page_loged_out = login_page   
        else:
            self.landing_page_loged_out = self._crawler.get_webpage_without_timeming_analyses(self.start_page_url)
            
        logging.debug("Perform login...")
        self.login(self._login_data, login_form)
        logging.debug("Validate login...")
        self.landing_page_loged_in = self._crawler.get_webpage_without_timeming_analyses(self.start_page_url)
        if self.landing_page_loged_in.toString() != self.landing_page_loged_out.toString():
            logging.debug("Login successfull...")
            c = dict_from_cookiejar(self.session_handler.cookies)
            self.login_cookie_keys = []
            for k in c: 
                self.login_cookie_keys.append(k)
        else:
            raise LoginErrorException("Login failed")
        
    def login(self, data, login_form):
        if not isinstance(data, dict):
            raise AttributeError("Data must be a dict with login credentials")
        data = form_to_json(login_form, data)
        login_url = self._crawler.domain_handler.create_url(login_form.action, depth_of_finding=0)
        res = self.session_handler.post(login_url.toString(), data=data, proxies=self.request_proxies, verify=False)
        return res.url
    
    def reset(self):
        self.session_handler = None
        self.session_handler = requests.Session()
        self.session_handler.headers.update({"User-Agent":self.headers})
    
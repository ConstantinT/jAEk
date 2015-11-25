'''
Copyright (C) 2015 Constantin Tschuertz

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

from enum import Enum
import logging
from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkRequest
from core.interactioncore import InteractionCore
from models.utils import CrawlSpeed

__author__ = 'constantin'


class XSSAttacker(InteractionCore):

    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium, network_access_manager = None):
        super(XSSAttacker, self).__init__(parent, proxy, port, crawl_speed, network_access_manager)
        self._analyzing_finished = False
        self._loading_complete = False
        self._attack_successfull = False
        self._random_value = None
        self.response_code = {}
        self.content_type = {}
        self.attack_counter = 0

    def attack(self, url, random_value, timeout = 10, verbose= False):
        self._analyzing_finished = False
        self._loading_complete = False
        self._attack_successfull = False
        self._random_value = random_value
        self.content_type = {}
        self.response_code = {}
        self.networkAccessManager().finished.connect(self.load_complete)
        self.mainFrame().load(QUrl(url))

        t = 0
        while not self._loading_complete and t < timeout:
            self._wait(self.wait_for_processing)
            t += self.wait_for_processing

        if not self._loading_complete:
            logging.debug("Timeout Error occurs...")
            self._analyzing_finished = True
            self.mainFrame().setHtml(None)
            return AttackResult.ErrorTimeout, None
        self.attack_counter += 1
        response_url = self.mainFrame().url().toString()
        try:
            response_code = self.response_code[response_url]
        except KeyError:
            response_code = 200
        response_html = self.mainFrame().toHtml()
        try:
            content_type = self.content_type[response_url]
        except KeyError:
            content_type = ""

        if verbose:
            self._analyzing_finished = True
            f = open("attackresult/" + str(self.attack_counter), "w")
            f.write("Url: " + url + " \n")
            f.write("================================================== \n")
            f.write(response_html)
            f.write(" \n =============================================== \n")

        self.networkAccessManager().finished.disconnect(self.load_complete)
        self.mainFrame().setHtml(None)

        if self._attack_successfull:
            if verbose:
                f.write(" \n Success!!!! \n")
                f.close()
            return AttackResult.AttackSuccessfull, response_code
        else:
            if verbose:
                f.write(" \n Fail... \n")
                f.close()
            try:
                if response_html is None:
                    return AttackResult.NotFound, response_code
                if random_value not in response_html and "javascript" in content_type:
                    return AttackResult.JSON, response_code
                elif random_value not in response_html and "html" in content_type:
                    return AttackResult.NotFound, response_code
                else:
                    return AttackResult.AttackFailed, response_code
            except TypeError:
                print("Error in {}, Random value: {}, Content Type: {}".format(url, random_value, content_type))

    def loadFinishedHandler(self, result):
        if not self._analyzing_finished:  # Just to ignoring setting of non page....
            self._loading_complete = True


    def javaScriptAlert(self, frame, msg):
        logging.debug("Alert occurs in frame: {} with message: {}".format(frame.baseUrl().toString(), msg))
        if self._random_value in msg:
            self._attack_successfull = True

    def _url_changes(self, url):
        self._url_changed = True
        self._new_url = url

    def load_complete(self, reply):
        if not self._analyzing_finished:
            self.content_type[reply.url().toString()] = reply.header(QNetworkRequest.ContentTypeHeader)
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) is None:
                logging.error("Response Code is None: Maybe, you dumb idiot, has set a proxy but not one running!!!")
                return
            else:
                #logging.debug("Response Code for {} is {}".format(reply.url().toString(), reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)))
                self.response_code[reply.url().toString()] = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

    def jsWinObjClearedHandler(self):  # Adding here the js-scripts I need
        if not self._analyzing_finished:
            self.mainFrame().addToJavaScriptWindowObject("jsb", self._js_bridge)

    def xss_callback(self, msg):
        logging.debug("XSS callback occurs with message: {}".format(msg))
        if self._random_value in msg:
            self._attack_successfull = True





class AttackResult(Enum):
    AttackSuccessfull = 0
    AttackFailed = 1
    ErrorTimeout = 2
    NotFound = 3 #The random value is not inside the html...
    JSON = 4
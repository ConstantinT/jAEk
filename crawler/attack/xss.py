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


    def attack(self, url, random_value, timeout = 10):
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


        self._analyzing_finished = True
        f = open("xss.txt", "w")
        f.write(response_html)
        f.close()
        self.networkAccessManager().finished.disconnect(self.load_complete)
        self.mainFrame().setHtml(None)

        if self._attack_successfull:
            return AttackResult.AttackSuccessfull, response_code
        else:
            if random_value not in response_html and "javascript" in content_type:
                return AttackResult.JSON, response_code
            elif random_value not in response_html and "html" in content_type:
                return AttackResult.NotFound, response_code
            else:
                return AttackResult.AttackFailed, response_code


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


class AttackResult(Enum):
    AttackSuccessfull = 0
    AttackFailed = 1
    ErrorTimeout = 2
    NotFound = 3 #The random value is not inside the html...
    JSON = 4
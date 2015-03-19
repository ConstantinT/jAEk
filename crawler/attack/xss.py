from enum import Enum
import logging
from PyQt5.QtCore import QUrl
from core.abstractinteractioncore import AbstractInteractionCore
from models.utils import CrawlSpeed

__author__ = 'constantin'


class XSSAttacker(AbstractInteractionCore):

    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium, network_access_manager = None):
        super(XSSAttacker, self).__init__(parent, proxy, port, crawl_speed, network_access_manager)
        self._analyzing_finished = False
        self._loading_complete = False
        self._attack_successfull = False


    def attack(self, url, timeout = 10):
        self._analyzing_finished = False
        self._loading_complete = False
        self._attack_successfull = False
        self.mainFrame().load(QUrl(url))

        t = 0
        while not self._loading_complete and t < timeout:
            self._wait(self.wait_for_processing)
            t += self.wait_for_processing

        if not self._loading_complete:
            logging.debug("Timeout Error occurs...")
            self._analyzing_finished = True
            self.mainFrame().setHtml(None)
            return AttackResult.Error_Timeout

        if self._attack_successfull:
            return AttackResult.Attack_Successfull
        else:
            return AttackResult.Attack_Failed


    def loadFinishedHandler(self, result):
        if not self._analyzing_finished:  # Just to ignoring setting of non page....
            self._loading_complete = True


    def javaScriptAlert(self, frame, msg):
        logging.debug("Alert occurs in frame: {} with message: {}".format(frame.baseUrl().toString(), msg))
        self._attack_successfull = True


class AttackResult(Enum):
    Attack_Successfull = 0
    Attack_Failed = 1
    Error_Timeout = 2
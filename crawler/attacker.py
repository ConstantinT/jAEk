import logging
import sys

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication

from attack.xss import XSSAttacker
from attack.xxxattacks import XSSVectors
from models.utils import CrawlSpeed
from network.network import NetWorkAccessManager


__author__ = 'constantin'


class Attacker(QObject):
    def __init__(self, config, proxy="", port=0, database_manager=None):
        QObject.__init__(self)
        self.app = QApplication(sys.argv)
        self._network_access_manager = NetWorkAccessManager(self)

        self._xss = XSSAttacker(self, proxy, port, crawl_speed=CrawlSpeed.Medium,
                                             network_access_manager=self._network_access_manager)

        self.database_manager = database_manager
        self._xss_vector = XSSVectors()

    def attack(self, user):

        all_urls = self.database_manager.get_all_visited_urls()
        for url in all_urls:
            if len(url.parameters) > 0:
                for i in url.parameters:
                    for j in url.parameters:
                        for vector in self._xss_vector.attack_vectors:
                            attack_string = url.scheme + "://" + url.domain + url.path + "?"
                            if i == j:
                                attack_string += j + "=" + vector.replace("XSS", self._xss_vector.random_string_generator(12)) + "&"
                            else:
                                attack_string += j + "=" + url.paramters[j][1] + "&"
                            logging.debug("Attack with: {}".format(attack_string[:-1]))
                            logging.debug(self._xss.attack(attack_string[:-1]))

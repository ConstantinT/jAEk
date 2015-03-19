import logging
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication
import sys
from attack.xss import XSSAttacker
from data.xxxattacks import XSSVectors
from database.persistentmanager import PersistenceManager
from models.utils import CrawlSpeed
from network.network import NetWorkAccessManager

__author__ = 'constantin'


class Attacker(QObject):
    def __init__(self, config, proxy="", port=0, persistence_manager=None):
        QObject.__init__(self)
        self.app = QApplication(sys.argv)
        self._network_access_manager = NetWorkAccessManager(self)

        self._xss = XSSAttacker(self, proxy, port, crawl_speed=CrawlSpeed.Medium,
                                             network_access_manager=self._network_access_manager)

        self.persistence_manager = persistence_manager
        self._xss_vector = XSSVectors()

    def attack(self, user):

        abstract_urls = self.persistence_manager.get_all_abstract_urls()
        for url in abstract_urls:
            if len(url.parameters) > 0:
                for i in range(len(url.parameters)):
                    for j in range(len(url.parameters)):
                        for vector in self._xss_vector.attack_vectors:
                            attack_string = url.path + "?"
                            if i == j:
                                attack_string += url.parameters[j][0] + "=" + vector.replace("XSS", self._xss_vector.random_generator(12)) + "&"
                            else:
                                attack_string += url.parameters[j][0] + "=" + url.paramters[j][1] + "&"
                            logging.debug("Attack with: {}".format(attack_string[:-1]))
                            logging.debug(self._xss.attack(attack_string[:-1]))

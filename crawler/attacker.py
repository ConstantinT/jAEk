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

        all_urls = self.database_manager.get_one_visited_url_per_structure()
        for url in all_urls:
            if len(url.parameters) > 0:
                for vector in self._xss_vector.attack_vectors:
                    for parameter_to_attack in url.parameters:
                        attack_url = url.scheme + "://" + url.domain + url.path + "?"
                        random_val  = self._xss_vector.random_string_generator(12)
                        for other_parameters in url.parameters:
                            if parameter_to_attack == other_parameters:
                                attack_url += other_parameters + "=" + vector.replace("XSS", random_val) + "&"
                            else:
                                attack_url += other_parameters + "=" + url.parameters[other_parameters][0] + "&"
                        attack_url = attack_url[:-1] # Removing the last "&
                        logging.debug("Attack with: {}".format(attack_url))
                        result = self._xss.attack(attack_url, random_val)
                        logging.debug("Result: {}" .format(result))
                        self.database_manager.insert_attack_result(result, attack_url)

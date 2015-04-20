import logging
import sys

from PyQt5.QtCore import QObject
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtWidgets import QApplication

from attack.xss import XSSAttacker, AttackResult
from attack.xxxattacks import XSSVectors
from core.jaek import Jaek
from models.utils import CrawlSpeed
from network.network import NetWorkAccessManager
from utils.domainhandler import DomainHandler
from utils.execptions import LoginFailed
from utils.utils import count_cookies


__author__ = 'constantin'


class Attacker(Jaek):
    def __init__(self, config, proxy="", port=0, database_manager=None):
        super(Attacker, self).__init__(config, proxy="", port=0, database_manager=database_manager)

        self._xss = XSSAttacker(self, proxy, port, crawl_speed=CrawlSpeed.Medium,
                                             network_access_manager=self._network_access_manager)

        self._xss_vector = XSSVectors()


    def attack(self, user):
        self.domain_handler = DomainHandler(self.config.start_page_url, self.database_manager)
        self.user = user
        if user.login_data is not None:
            self.process_with_login = True
            go_on = self.initial_login()
            if not go_on:
                raise LoginFailed("Initial login failed...")


        all_urls = self.database_manager.get_one_visited_url_per_structure()
        for url in all_urls:
            empty_limit = 5
            if len(url.parameters) > 0:
                for parameter_to_attack in url.parameters:
                    empty_counter = 0
                    for vector in self._xss_vector.attack_vectors:
                        if self.process_with_login:
                            num_cookies = count_cookies(self._network_access_manager, url)
                            if num_cookies < self.cookie_num:
                                logging.debug("Too less cookies... possible logout!")
                                self.handle_possible_logout()
                        attack_url = url.scheme + "://" + url.domain + url.path + "?"
                        random_val = self._xss_vector.random_string_generator(12)
                        for other_parameters in url.parameters:
                            if parameter_to_attack == other_parameters:
                                attack_url += other_parameters + "=" + vector.replace("XSS", random_val) + "&"
                            else:
                                attack_url += other_parameters + "=" + url.parameters[other_parameters][0] + "&"
                        attack_url = attack_url[:-1] # Removing the last "&
                        logging.debug("Attack with: {}".format(attack_url))
                        result, response_code = self._xss.attack(attack_url, random_val)
                        if result in (AttackResult.AttackSuccessfull, AttackResult.AttackFailed):
                            logging.debug("Result: {} - Response Code: {}" .format(result, response_code))
                            self.database_manager.insert_attack_result(result, attack_url)
                        else:
                            logging.debug("Result is empty...")
                            empty_counter += 1
                        if empty_counter > empty_limit:
                            break



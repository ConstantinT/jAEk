from asyncio.tasks import sleep
import logging
import sys
from urllib.parse import urlparse


from attack.xss import XSSAttacker, AttackResult
from attack.xxxattacks import XSSVectors
from core.jaek import Jaek
from models.url import Url
from models.utils import CrawlSpeed
from utils.domainhandler import DomainHandler
from utils.execptions import LoginFailed



__author__ = 'constantin'

EMPTY_LIMIT = 5
class Attacker(Jaek):
    def __init__(self, config, proxy="", port=0, database_manager=None):
        super(Attacker, self).__init__(config, proxy="", port=0, database_manager=database_manager)

        self._xss = XSSAttacker(self, proxy, port, crawl_speed=CrawlSpeed.Medium,
                                             network_access_manager=self._network_access_manager)

        self._xss_vector = XSSVectors()

    def attack(self, user):
        self.domain_handler = DomainHandler(self.config.start_page_url, self.database_manager, cluster_manager=None)
        self.user = user
        if user.login_data is not None:
            self.process_with_login = True
            go_on = self.initial_login()
            if not go_on:
                raise LoginFailed("Initial login failed...")
        self.attack_all_urls_with_replacing()
        self.attack_all_urls_with_additions()
        self.attack_all_get_forms()
        #url = "http://localhost:8080/index.php/apps/files/ajax/download.php?files=moep&dir=tut"
        #url = "http://localhost:8080/wp-content/plugins/tidio-gallery/popup-insert-help.php?galleryId=t47sx79npgz01tywyeo3wwuuxz03u7vh"
        #url = "http://localhost:8080/admin.php?page=plugin-AdminTool%3Cimg%20onerror%3Dalert(123)%3B%20src%3Dx%3Es"
        #url = "http://localhost:8080/report.php?type=post&pid=1"
        #self.attack_single_url(url, replacement= True)


    def attack_single_url(self, url, replacement=False):
        if not replacement:
            attack_url = url
            result, response_code = self._xss.attack(attack_url, "123")
            logging.debug("Result: {}".format(result))
            return
        url = Url(url)
        for parameter_to_attack in url.parameters:
            for vector in self._xss_vector.attack_vectors:
                attack_url = url.scheme + "://" + url.domain + url.path + "?"
                random_val = self._xss_vector.random_number_generator(12)
                ramdom_val = "123"
                for other_parameters in url.parameters:
                    if parameter_to_attack == other_parameters:
                        attack_url += other_parameters + "=" + vector.replace("XSS", random_val) + "&"
                    else:
                        attack_url += other_parameters + "=" + url.parameters[other_parameters][0] + "&"
                attack_url = attack_url[:-1] # Removing the last "&
                logging.debug("Attack with: {}".format(attack_url))
                result, response_code = self._xss.attack(attack_url, random_val)
                logging.debug("Result: {}".format(result))


    def attack_all_urls_with_additions(self):
        domain = urlparse(self.config.start_page_url)
        domain = domain.netloc
        all_urls = self.database_manager.get_all_urls_to_domain(domain)
        for url in all_urls:
            if len(url.parameters) > 0:
                logging.debug("Now testing with url: {}".format(url.toString()))
                if self.process_with_login:
                    self.handle_possible_logout()
                for parameter_to_attack in url.parameters:
                    empty_counter = 0
                    for vector in self._xss_vector.attack_vectors:
                        attack_url = url.scheme + "://" + url.domain + url.path + "?"
                        random_val = self._xss_vector.random_number_generator(12)
                        for other_parameters in url.parameters:
                            if parameter_to_attack == other_parameters:
                                attack_url += other_parameters + "=" + str(url.parameters[other_parameters][0]) if url.parameters[other_parameters][0] is not None else ""
                                attack_url += vector.replace("XSS", str(random_val)) + "&"
                            else:
                                attack_url += other_parameters + "="
                                attack_url += url.parameters[other_parameters][0] if url.parameters[other_parameters][0] is not None else ""
                                attack_url += "&"
                        attack_url = attack_url[:-1] # Removing the last "&
                        logging.debug("Attack with: {}".format(attack_url))
                        result, response_code = self._xss.attack(attack_url, random_val)
                        if not self.check_login_status():
                            sleep(2000)
                            self.initial_login()
                            result, response_code = self._xss.attack(attack_url, random_val)
                        if response_code is None:
                            continue
                        if response_code >= 400 or result == AttackResult.JSON:
                            empty_counter = 42
                        logging.debug("Result: {} - Response Code: {}" .format(result, response_code))
                        if result in (AttackResult.AttackSuccessfull, AttackResult.AttackFailed):
                            self.database_manager.insert_attack_result(result, attack_url)
                            empty_counter = 0
                        else:
                            empty_counter += 1
                        if empty_counter > EMPTY_LIMIT:
                            break



    def attack_all_urls_with_replacing(self):
        all_urls = self.database_manager.get_one_visited_url_per_structure()
        for url in all_urls:
            if len(url.parameters) > 0:
                logging.debug("Now testing with url: {}".format(url.toString()))
                if self.process_with_login:
                    self.handle_possible_logout()
                for parameter_to_attack in url.parameters:
                    empty_counter = 0
                    for vector in self._xss_vector.attack_vectors:
                        attack_url = url.scheme + "://" + url.domain + url.path + "?"
                        random_val = self._xss_vector.random_number_generator(12)
                        for other_parameters in url.parameters:
                            if parameter_to_attack == other_parameters:
                                attack_url += other_parameters + "=" + vector.replace("XSS", random_val) + "&"
                            else:
                                attack_url += other_parameters + "="
                                attack_url += url.parameters[other_parameters][0] if url.parameters[other_parameters][0] is not None else ""
                                attack_url += "&"
                        attack_url = attack_url[:-1] # Removing the last "&
                        logging.debug("Attack with: {}".format(attack_url))
                        result, response_code = self._xss.attack(attack_url, random_val)
                        if not self.check_login_status():
                            sleep(2000)
                            self.initial_login()
                            result, response_code = self._xss.attack(attack_url, random_val)
                        if response_code is None:
                            continue
                        if response_code >= 400 or result == AttackResult.JSON:
                            empty_counter = 42
                        logging.debug("Result: {} - Response Code: {}" .format(result, response_code))
                        if result in (AttackResult.AttackSuccessfull, AttackResult.AttackFailed):
                            self.database_manager.insert_attack_result(result, attack_url)
                            empty_counter = 0
                        else:
                            empty_counter += 1
                        if empty_counter > EMPTY_LIMIT:
                            break

    def attack_all_get_forms(self):
        if self.process_with_login:
                self.handle_possible_logout()
        logging.debug("Attacking with get forms")
        all_forms = self.database_manager.get_one_form_per_destination()
        for form in all_forms:
            logging.debug(form.toString())
            if "javascript" in form.action.complete_url:
                continue
            for param_to_attack in form.parameter:
                if param_to_attack.input_type == "submit" or param_to_attack.name is None:
                    continue
                logging.debug("Now at paramerter {}".format(param_to_attack.toString()))
                empty_counter = 0
                for vector in self._xss_vector.attack_vectors:
                    attack_url = form.action.complete_url + "?"
                    random_val = self._xss_vector.random_number_generator(12)
                    for other_parameter in form.parameter:
                        if param_to_attack == other_parameter:
                            if other_parameter is None or other_parameter.name is None:
                                continue
                            attack_url += other_parameter.name + "=" + vector.replace("XSS", random_val) + "&"
                        else:
                            if other_parameter.input_type == "submit" or other_parameter.name is None:
                                continue
                            elif other_parameter.values is None:
                                attack_url += other_parameter.name + "=&"
                            elif other_parameter.values[0] is not None:
                                attack_url += other_parameter.name + "=" + other_parameter.values[0] + "&"
                            else:
                                attack_url += other_parameter.name + "=" + self._xss_vector.random_string_generator(6) + "&"
                    attack_url = attack_url[:-1]
                    logging.debug("Attack with: {}".format(attack_url))
                    result, response_code = self._xss.attack(attack_url, random_val)
                    if not self.check_login_status():
                        sleep(2000)
                        self.initial_login()
                        result, response_code = self._xss.attack(attack_url, random_val)
                    if response_code is None:
                        continue
                    if response_code >= 400 or result == AttackResult.JSON:
                        empty_counter = 42
                    logging.debug("Result: {} - Response Code: {}" .format(result, response_code))
                    if result in (AttackResult.AttackSuccessfull, AttackResult.AttackFailed):
                        self.database_manager.insert_attack_result(result, attack_url)
                        empty_counter = 0
                    else:
                        empty_counter += 1
                    if empty_counter > EMPTY_LIMIT:
                        break






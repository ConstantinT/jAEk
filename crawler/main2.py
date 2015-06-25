'''
Created on 12.11.2014

@author: constantin
'''
import logging

from attacker import Attacker
from crawler import Crawler
from database.databasemanager import DatabaseManager
from utils.config import CrawlConfig, AttackConfig
from models.utils import CrawlSpeed
from utils.user import User
import csv
from utils.utils import calculate_similarity_between_pages

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s: %(levelname)s - %(message)s',
                    #datefmt='%d.%m.%Y %H:%M:%S.%f',
                    #filename='Attack.log',
                    #filemode='w'
                    )

if __name__ == '__main__':
    logging.info("Crawler started...")

    #user = User("WordpressX", 0, "http://localhost:8080/wp-login.php", login_data = {"log": "admin", "pwd": "admin"}, session="ABC")
    #user = User("constantin", 0, "http://localhost:8080/", login_data = {"username" : "admin", "pass" : "admin"})
    #user = ser("constantin", 0, "https://plus.google.com/", login_data={"Email": "constantin.tschuertz@gmail.com","Passwd": "NmE4NjliZm"})
    #user = User("local", 0, "http://localhost:8080/", login_data = {"user": "admin", "password": "admin"}, session="ABC")
    #user = User("constantin", 0, "http://localhost:8080/", login_data = {"username": "admin", "password": "admin"})
    #user = User("Gallery2", 0, "http://localhost:8080/", login_data= {"name": "admin", "password": "34edbc"}, session= "ABC")
    #user = User("Gallery41", 0, session="ABC")
    #user = User("PHPbb64", 0, "http://localhost:8080/phpbb/ucp.php?mode=login", login_data = {"username": "admin", "password": "adminadmin"}, session= "ABC")
    #user = User("Joomla", 0, "http://localhost:8080/", login_data = {"username": "admin", "password": "admin"}, session= "ABC")
    #user = User("ModX", 0 , "http://localhost:8080/manager/", login_data= {"username": "admin", "password": "adminadmin"}, session="ABC")
    #user = User("Pimcore", 0, "http://localhost:8080/admin/login/", login_data={"username": "admin", "password": "admin"}, session="ABC")
    #user = User("Piwigo", 0, "http://localhost:8080/", login_data={"username": "admin", "password": "admin"}, session="ABC")
    #user = User("Concret5", 0, "http://localhost:8080/index.php/login", login_data={"uName": "admin", "uPassword": "admin"})
    #user = User("Mediawiki", 0)
    #user = User("MyBB2", 0, "http://localhost:8080/index.php", login_data= {"quick_username": "admin", "quick_password": "admin"}, session="ABC")
    #user = User("MyBB2", 0, "http://localhost:8080/admin/index.php", login_data= {"username": "admin", "password": "admin"}, session="ABC")
    user = User("local", 0)

    #url = "http://localhost/test3.php"
    #url = "http://localhost:8080/showthread.php?tid=1"
    url = "http://localhost:8080/pages/18.php"
    #url = "http://localhost/submission_test1.php"
    crawler_config = CrawlConfig("Was weiß ich", url, max_depth=1, max_click_depth=5, crawl_speed=CrawlSpeed.Fast)
    attack_config = AttackConfig(url)

    database_manager = DatabaseManager(user, dropping=True)
    crawler = Crawler(crawl_config=crawler_config, database_manager=database_manager)#, proxy="localhost", port=8082)
    crawler.crawl(user)
    # TODO: It seems to be that, there is an error if we instanciate crawler and attacker and then call the crawl function. Maybe use one global app!
    logging.info("Crawler finished")
    logging.info("Start attacking...")
    #attacker = Attacker(attack_config, database_manager=database_manager)#, proxy="localhost", port=8082)
    #attacker.attack(user)
    logging.info("Finish attacking...")
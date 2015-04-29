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
                    datefmt='%d.%m.%Y %H:%M:%S',
                    filename='Crawler.log',
                    filemode='w'
                    )

if __name__ == '__main__':
    logging.info("Crawler started...")

    #user = User("WPAdmin3", 0, "http://localhost:8080/wp-login.php", login_data = {"log" : "admin", "pwd" : "admin"}, session="ABC")
    #user = User("constantin", 0, "http://localhost:8080/", login_data = {"username" : "admin", "pass" : "admin"})
    #user = User("constantin", 0, "https://plus.google.com/", login_data={"Email": "constantin.tschuertz@gmail.com","Passwd": "NmE4NjliZm"})
    #user = User("owncloud2", 0, "http://localhost:8080/", login_data = {"user" : "jaek", "password" : "jaek"}, session="ABC")
    #user = User("constantin", 0, "http://localhost:8080/", login_data = {"username": "admin", "password": "admin"})
    user = User("Gallery2", 0, "http://localhost:8080/", login_data = {"name": "admin", "password": "66ca90"}, session= "ABC")
    #user = User("GalleryGuestij", 0, session="ABC")
    #user = User("PHPbb2", 0, "http://localhost:8080/phpbb/ucp.php?mode=login", login_data = {"username": "admin", "password": "adminadmin"}, session= "ABC")



    url = "http://localhost:8080/"
    #url = "http://localhost:8080/index.php/login"

    crawler_config = CrawlConfig("Was weiß ich", url, max_depth=5,
max_click_depth=3, crawl_speed=CrawlSpeed.Fast)
    attack_config = AttackConfig(url)

    database_manager = DatabaseManager(user, dropping=True)
    crawler = Crawler(crawl_config=crawler_config, database_manager=database_manager)  #, proxy="localhost", port=8081)
    crawler.crawl(user)
    # TODO: It seems to be that, there is an error if we instanciate crawler and attacker and then call the crawl function. Maybe use one global app!

    #attacker = Attacker(attack_config, database_manager=database_manager)
    #attacker.attack(user)

    logging.info("Crawler finished")



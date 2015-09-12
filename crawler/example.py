__author__ = 'constantin'


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
                    #filename='Attack.log',
                    #filemode='w'
                    )

if __name__ == '__main__':
    logging.info("Crawler started...")

    # This is for example to crawl a wordpress installation as logged in user
    user = User("Wordpress", 0, "http://localhost:8080/wp-login.php", login_data = {"log": "admin", "pwd": "admin"}, session="ABC")

    url = "http://localhost/"

    # This is the confuigrtion I used for the experiments
    crawler_config = CrawlConfig("jÄk", url, max_depth=3, max_click_depth=3, crawl_speed=CrawlSpeed.Fast)
    attack_config = AttackConfig(url)

    database_manager = DatabaseManager(user, dropping=True)
    # Uncomment out the end of the next line to use a proxy
    crawler = Crawler(crawl_config=crawler_config, database_manager=database_manager)#, proxy="localhost", port=8082)
    crawler.crawl(user)
    logging.info("Crawler finished")

    logging.info("Start attacking...")
    attacker = Attacker(attack_config, database_manager=database_manager)#, proxy="localhost", port=8082)
    attacker.attack(user)
    logging.info("Finish attacking...")
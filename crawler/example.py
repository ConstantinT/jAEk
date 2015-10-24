'''
Copyright (C) 2015 Constantin Tschürtz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
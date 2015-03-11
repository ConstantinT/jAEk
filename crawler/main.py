'''
Created on 12.11.2014

@author: constantin
'''
import logging
from crawler import Crawler
from models.config import CrawlConfig
from models.user import CrawlerUser
from models.utils import CrawlSpeed


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s: %(levelname)s - %(message)s',
                    datefmt='%d.%m.%Y %H:%M:%S',
                    #filename='Crawler.log',
                    #filemode='w'
                    )

if __name__ == '__main__':
    
    
    logging.info("Crawler started...")
     
   
    
    url = "http://localhost/url_change_test1.php"
    #url = "http://localhost/iframe_test1.php"
    #url = "http://localhost:8081/pages/1.php"
    #url = "https://plus.google.com/"
    url = "http://localhost:8080"

    crawler_config = CrawlConfig("EPESI", url, max_depth=5,
max_click_depth=3, crawl_speed = CrawlSpeed.Fast)
    c = Crawler(crawl_config=crawler_config, proxy="localhost", port=8081)
    
    user = CrawlerUser("constantin" , 0)
    #user = CrawlerUser("constantin", 0, "http://localhost:8080/wp-login.php", login_data = {"log" : "admin", "pwd" : "admin"})
    #user = CrawlerUser("constantin", 0, "http://localhost:8080/", login_data = {"username" : "admin", "pass" : "admin"}) 
    #user = CrawlerUser("constantin", 0, "https://plus.google.com/", login_data={"Email": "constantin.tschuertz@gmail.com","Passwd": "NmE4NjliZm"})
    #user = CrawlerUser("constantin", 0, "http://localhost:8080/", login_data = {"user" : "arthur dent", "password" : "arthur"})
    user = CrawlerUser("constantin", 0, "http://localhost:8080/", login_data = {"username": "admin", "password": "admin"})
    user = c.crawl(user)
     
    logging.info("Crawler finished")

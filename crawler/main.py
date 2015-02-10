'''
Created on 12.11.2014

@author: constantin
'''
import logging
from crawler import Crawler
from models import CrawlerUser, CrawlConfig, CrawlSpeed



logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s: %(levelname)s - %(message)s',
                    datefmt='%d.%m.%Y %H:%M:%S',
                    #filename='Crawler.log',
                    #filemode='w'
                    )

if __name__ == '__main__':
    
    
    logging.info("Crawler started...")
     
    
    
    url = "http://localhost:8080/admin.php?action=projects"
    #url = "https://plus.google.com/"

    crawler_config = CrawlConfig("Test45", url, max_depth=3, max_click_depth=2, crawl_speed = CrawlSpeed.Fast)
    c = Crawler(crawl_config=crawler_config)#, proxy="localhost", port=8080)
    
    user = CrawlerUser("constantin" , 0)
    #user = CrawlerUser("constantin", 0, "http://localhost:8080/wp-login.php", login_data = {"log" : "admin", "pwd" : "admin"})
    user = CrawlerUser("constantin", 0, "http://localhost:8080/", login_data = {"username" : "admin", "pass" : "admin"}) 
    #user = CrawlerUser("constantin", 0, "https://plus.google.com/", login_data={"Email": "constantin.tschuertz@gmail.com","Passwd": "NmE4NjliZm"})
    user = c.crawl(user)
    
    
    #
    #c.crawl(user)
    #c.test()
    #c.crawl("web.de")
    
    
    logging.info("Crawler finished")
    

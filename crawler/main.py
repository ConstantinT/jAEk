'''
Created on 12.11.2014

@author: constantin
'''
import logging
import models
from models import CrawlerUser, CrawlConfig
from crawler import Crawler



logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s: %(levelname)s - %(message)s',
                    datefmt='%d.%m.%Y %H:%M:%S',
                    #filename='Crawler.log',
                    #filemode='w'
                    )

if __name__ == '__main__':
    
    
    logging.info("Crawler started...")
     
    
    
    #url = "http://localhost:8080/"
    url = "https://plus.google.com/"

    crawler_config = CrawlConfig("Google", url, max_depth=0, max_click_depth=5, crawl_speed = models.CrawlSpeed.Slow)
    c = Crawler(crawl_config=crawler_config)#, proxy="localhost", port=8080)
    
    user = CrawlerUser("constantin" , 0)
    user = CrawlerUser("constantin", 0, "http://localhost:8080/wp-login.php", login_data = {"log" : "admin", "pwd" : "admin"})
    #user = CrawlerUser("constantin", 0, "http://localhost:8081/", login_data = {"username" : "Admin", "pass" : "admin"}) 
    user = CrawlerUser("constantin", 0, "https://plus.google.com/", login_data={"Email": "constantin.tschuertz@gmail.com","Passwd": "NmE4NjliZm"})
    user = c.crawl(user)
    
    for url in user.visited_urls:
        logging.debug(url.toString())
    
    #
    #c.crawl(user)
    #c.test()
    #c.crawl("web.de")
    
    
    logging.info("Crawler finished")
    
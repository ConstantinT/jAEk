'''
Created on 23.02.2015

@author: constantin
'''
from models.utils import CrawlSpeed

class CrawlConfig():
    
    def __init__(self, name, domain, max_depth = 5, max_click_depth = 5, crawl_speed = CrawlSpeed.Medium):
        self.name = name
        self.max_depth = max_depth
        self.max_click_depth = max_click_depth
        self.domain = domain
        self.crawl_speed = crawl_speed
        
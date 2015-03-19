'''
Created on 23.02.2015

@author: constantin

This class contains everything that is important for a crawl session:
    - name
    - start_page - is the start page, where the crawler should start
    - max_depth - How deep the crawler should go
    - max_click_depth - How deep a crawler should click
    - speed - interaction speed between Jäk and JS

'''
from models.utils import CrawlSpeed

class CrawlConfig():
    
    def __init__(self, name, start_page, max_depth = 5, max_click_depth = 5, crawl_speed = CrawlSpeed.Medium):
        self.name = name
        self.max_depth = max_depth
        self.max_click_depth = max_click_depth
        self.start_page_url = start_page
        self.crawl_speed = crawl_speed



class AttackConfig():
    """
    Right now more a dummy than something usefull
    """
    def __init__(self):
        attack = "XSS"

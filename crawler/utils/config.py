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

This class contains everything that is important for a crawl session:
    - name
    - start_page - is the start page, where the crawler should start
    - max_depth - How deep the crawler should go
    - max_click_depth - How deep a crawler should click
    - speed - interaction speed between Jäk and JS

'''
from models.utils import CrawlSpeed

class CrawlConfig():
    
    def __init__(self, name, start_page, max_depth = 5, max_click_depth = 5, crawl_speed=CrawlSpeed.Medium):
        self.name = name
        self.max_depth = max_depth
        self.max_click_depth = max_click_depth
        self.start_page_url = start_page
        self.process_speed = crawl_speed



class AttackConfig():
    """
    Right now more a dummy than something usefull
    """
    def __init__(self, start_page_url, crawl_speed=CrawlSpeed.Medium):
        attack = "XSS"
        self.start_page_url = start_page_url
        self.process_speed = crawl_speed


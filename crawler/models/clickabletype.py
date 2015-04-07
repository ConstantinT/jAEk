'''
Created on 23.02.2015

@author: constantin
'''
from enum import Enum

class ClickableType(Enum):
    UIChange = 0
    Link = 1
    CreatesNewNavigatables = 2
    Error = 3
    SendingAjax = 4
    IgnoredByCrawler = 5
    UnsupportedEvent = 6
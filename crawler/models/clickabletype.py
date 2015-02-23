'''
Created on 23.02.2015

@author: constantin
'''
from enum import Enum

class ClickableType(Enum):
    UI_Change = 0
    Link = 1
    Creates_new_navigatables = 2
    Error = 3
    SendingAjax = 4
    Ignored_by_Crawler = 5
    Unsuported_Event = 6
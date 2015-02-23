'''
Created on 23.02.2015

@author: constantin
'''


   
    
class CrawlerUser():
    
    def __init__(self, username,  user_level, url_with_login_form = None, login_data = None):
        self.login_data = login_data
        self.username = username
        self.url_with_login_form = url_with_login_form
        self.user_id = None
        self.user_level =   user_level
        self.sessions = []
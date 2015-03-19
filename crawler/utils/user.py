'''
Created on 23.02.2015

@author: constantin

This class contains everything, that is important for a user. It specifies, mainly the login behaviour.
Notice: A crawl session(one config) can have multiple users
    - username - for identifying later the user
    - user_level - can be interesting for later comparison for different views
    - url_with_login_form - what can that be??
    - login_data = dict, that contains mainly username and password

'''
import uuid


class User():
    
    def __init__(self, username,  user_level, url_with_login_form = None, login_data = None):
        self.login_data = login_data
        self.username = username
        self.url_with_login_form = url_with_login_form
        self.user_level = user_level
        self.session = uuid.uuid4()
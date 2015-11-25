'''
Copyright (C) 2015 Constantin Tschuertz

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


This class contains everything, that is important for a user. It specifies, mainly the login behaviour.
Notice: A crawl session(one config) can have multiple users
    - username - for identifying later the user
    - user_level - can be interesting for later comparison for different views
    - url_with_login_form - what can that be??
    - login_data = dict, that contains mainly username and password

'''

import uuid


class User():
    
    def __init__(self, username,  user_level, url_with_login_form=None, login_data=None, session=uuid.uuid4()):
        self.login_data = login_data
        self.username = username
        self.url_with_login_form = url_with_login_form
        self.user_level = user_level
        self.session = session
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
'''

class LoginFormNotFound(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
    
class PageNotFound(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
    
class LoginFailed(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
     
class ElementNotFound(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
    
class DomainHandlerNotSet(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)  
    
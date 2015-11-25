# -*- coding: latin-1 -*-"
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
'''
  
class Link():
    
    def __init__(self, url, dom_address, html_id = "", html_class = ""):
        self.url = url 
        self.dom_address = dom_address
        self.html_id = html_id
        self.html_class = html_class
        
    def toString(self):
        res = "["
        res += "A-HREF: " + self.url.abstract_url + " - {}".format(self.url.url_hash)
        res += " - Domadress: " + self.dom_address
        if self.html_id != "":
            res += " - ID: " + self.html_id
        if self.html_class != "":
            res += " - Class: " + self.html_class
        res += "]"
        return res
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.url == other.url

    def __ne__(self, other):
        return not self.__eq__(other) 
  
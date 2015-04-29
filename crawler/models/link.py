'''
Created on 23.02.2015

@author: constantin
'''
  
class Link():
    
    def __init__(self, url, dom_adress, html_id = "", html_class = ""):
        self.url = url 
        self.dom_address = dom_adress
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
  
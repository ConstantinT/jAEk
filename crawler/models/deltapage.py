'''
Created on 23.02.2015

@author: constantin
'''

from models.webpage import WebPage

class DeltaPage(WebPage):
    
    def __init__(self, id, url = None, html = None, cookiesjar = None, depth = None, generator = None, parent_id = None, delta_depth = None, base_url = None):
        WebPage.__init__(self, id, url, html, cookiesjar, depth, base_url=base_url)
        self.generator = generator
        self.generator_requests = []
        self.parent_id = parent_id
        self.ajax_requests = []
        self.delta_depth = delta_depth
        
    def toString(self):
        msg = "[ Page: " + str(self.url) + " - ID: " + str(self.id) + " - Depth:" + str(self.current_depth) +" \n"
        msg += "Parent-ID: " + str(self.parent_id) + " - Generator: " + self.generator.toString() + " - Delta Depth: " + str(self.delta_depth) + " \n"
        if len(self.generator_requests) > 0:
            msg += "Generator AsyncRequests: \n"
            for r in self.generator_requests:
                msg += " - " + r.toString() + " \n"
        if self.cookiejar is not None:
            c = dict_from_cookiejar(self.cookiejar)
            if len(c) > 0:
                msg += "Cookies: \n"
                for k in c: 
                    msg += str(k) + " - " + str(c[k]) + " \n" 
        if len(self.clickables) > 0: 
            msg += "Clickable: \n"
            for elem in self.clickables:
                msg += elem.toString() + " \n"
        if len(self.timing_requests) > 0:
            msg += "Timingrequests: \n"
            for elem in self.timing_requests:
                msg += elem.toString() + " \n"
        if len(self.links) > 0: 
            msg += "Static Links: \n"
            for link in self.links:
                tmp = link.toString()
                msg += tmp + " \n"
        if len(self.forms) > 0: 
            msg += "Forms: \n"
            for elem in self.forms:
                msg += elem.toString() + " \n"
        return msg + "]"    
    


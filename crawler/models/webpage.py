'''
Created on 23.02.2015

@author: constantin
'''
class WebPage:
    
    def __init__(self, id, url = None, html = None, cookiesjar = None, depth = None, base_url = None):
        self.id = id
        self.cookiejar = cookiesjar
        self.url = url
        self.html = html
        self.clickables = []
        self.timing_requests = []
        self.links = []
        self.forms = []
        self.current_depth = depth
        self.ajax_requests = []
        self.base_url = None # Defines if a page contains a <base> tag
        
    def toString(self):
        try:
            url = self.url.toString()
        except AttributeError:
            url = self.url
        msg = "[ Page: " + url + " - ID: " + str(self.id) + " - Depth:" + str(self.current_depth) + " \n"
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
        if len(self.ajax_requests) > 0: 
            msg += "Ajax-AsyncRequests: \n"
            for elem in self.ajax_requests:
                msg += elem.toString() + " \n"
        return msg + "]"
    
'''
Created on 12.11.2014

@author: constantin
'''

from urllib.parse import urlparse
from PyQt5.QtCore import QObject
from pip._vendor.requests.utils import dict_from_cookiejar
from enum import Enum
import hashlib

class WebPage:
    
    def __init__(self, id, url = None, html = None, cookiesjar = None, depth = None, ):
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
        
    def toString(self):
        msg = "[ Page: " + str(self.url) + " - ID: " + str(self.id) + " - Depth:" + str(self.current_depth) + " \n"
        if self.cookiejar is not None:
            msg += "Cookies: \n"
            c = dict_from_cookiejar(self.cookiejar)
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
        if len(self.ajax_requests) > 0: 
            msg += "Ajax-Requests: \n"
            for elem in self.ajax_requests:
                msg += elem.toString() + " \n"
        return msg + "]"
    
class DeltaPage(WebPage):
    
    def __init__(self, id, url = None, html = None, cookiesjar = None, depth = None, generator = None, parent_id = None, delta_depth = None):
        WebPage.__init__(self, id, url, html, cookiesjar, depth)
        self.generator = generator
        self.generator_requests = []
        self.parent_id = parent_id
        self.ajax_requests = []
        self.delta_depth = delta_depth
        
    def toString(self):
        msg = "[ Page: " + str(self.url) + " - ID: " + str(self.id) + " - Depth:" + str(self.current_depth) +" \n"
        msg += "Parent-ID: " + str(self.parent_id) + " - Generator: " + self.generator.toString() + " - Delta Depth: " + str(self.delta_depth) + " \n"
        if len(self.generator_requests) > 0:
            msg += "Generator Requests: \n"
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
    


class AjaxRequest():
    '''
    Models an Ajax-Request
    '''
    def __init__(self, method, url, trigger, parameter = None):
        self.method = method
        self.url = url
        self.trigger = trigger
        self.parameter = parameter
    
    def toString(self):
        msg =  "[Ajax - Methode: " + self.method + " - Url: "+ self.url + " - Trigger: " + self.trigger.toString() + " \n"
        for param_pair in self.parameter:
            msg += " - Parameter pair: " + str(param_pair)
        return msg
        
class TimemingRequest():
    '''
    Models an Ajax-Request
    '''
    def __init__(self, method, url, time , trigger ,function_id = None):
        self.method = method
        self.url = url
        self.event = trigger #Timout or Intervall
        self.function_id = function_id #ID of the function that is called from the event
        self.time = time
    def toString(self):
        return "[Timeming - Methode: " + str(self.method) + " - Url: "+ str(self.url) + " - Trigger: " + str(self.event) +" - FunctionID: " + str(self.function_id) + "]"
        
class Clickable():
    '''
    Models interesting element with events as attributes
    '''
    
    def __init__(self, event, tag, dom_adress, id = None, html_class = None, clickable_depth = None, function_id = None):
        self.event = event
        self.tag = tag
        self.dom_adress = dom_adress
        self.id = id
        self.html_class = html_class
        self.links_to = None
        self.clicked = False
        self.clickable_type = None
        self.clickable_depth = clickable_depth
        self.function_id = function_id
        
    def toString(self):
        msg = ""
        msg += "[TAG: " + self.tag
        if self.id is not None and not self.id == "":
            msg += " - ID: " + self.id
        if self.event is not None and not self.event == "":
            msg += " - Event: " + self.event
        if self.html_class is not None and not self.html_class == "":
            msg += " - Class: " + self.html_class
        msg += " - Domadress: " + self.dom_adress
        if self.links_to is not None:
            msg += " - Links to: " + self.links_to
        if self.clickable_depth is not None:
            msg += " - Clickable Depth: " + str(self.clickable_depth)
        if self.function_id is not None:
            msg += " - FunctionID: " + self.function_id
        if self.clickable_type is not None:
            if self.clickable_type == ClickableType.Creates_new_navigatables:
                msg += " - ClickableType: Create_new_navigatable"
            elif self.clickable_type == ClickableType.Link:
                msg += " - ClickableType: Link"
            elif self.clickable_type == ClickableType.SendingAjax:
                msg += " - ClickableType: SendingAjax"
            elif self.clickable_type == ClickableType.UI_Change:
                msg += " - ClickableType: UiChange"
            elif self.clickable_type == ClickableType.Error:
                msg += " - ClickableType: Error"
        msg += "]"  
        return msg
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.dom_adress == other.dom_adress and self.event == other.event

    def __ne__(self, other):
        return not self.__eq__(other)        


class KeyClickable(Clickable):
    
    def __init__(self, clickable, key_event):
        Clickable.__init__(self, clickable.event, clickable.tag, clickable.dom_adress, clickable.id, clickable.html_class, clickable.clickable_depth, clickable.function_id)
        self.random_char = key_event #Is the key typed in for triggering the clickabel
    
    def toString(self):   
        msg = ""
        msg += "[TAG: " + self.tag
        if self.id is not None and not self.id == "":
            msg += " - ID: " + self.id
        if self.event is not None and not self.event == "":
            msg += " - Event: " + self.event
        if self.html_class is not None and not self.html_class == "":
            msg += " - Class: " + self.html_class
        msg += " - Domadress: " + self.dom_adress
        if self.links_to is not None:
            msg += " - Links to: " + self.links_to
        if self.clickable_depth is not None:
            msg += " - Clickable Depth: " + str(self.clickable_depth)
        if self.function_id is not None:
            msg += " - FunctionID: " + self.function_id
        if self.clickable_type is not None:
            if self.clickable_type == ClickableType.Creates_new_navigatables:
                msg += " - ClickableType: Create_new_navigatable"
            elif self.clickable_type == ClickableType.Link:
                msg += " - ClickableType: Link"
            elif self.clickable_type == ClickableType.SendingAjax:
                msg += " - ClickableType: SendingAjax"
            elif self.clickable_type == ClickableType.UI_Change:
                msg += " - ClickableType: UiChange"
            elif self.clickable_type == ClickableType.Error:
                msg += " - ClickableType: Error"
        if self.random_char is not None:
            msg += self.random_char
        msg += "]"  
        return msg
       
class Url():
    def __init__(self, url, depth_of_finding = None):
        self.complete_url = url
        parsed_url = urlparse(url)
        self.scheme = parsed_url.scheme
        self.domain = parsed_url.netloc
        if parsed_url.path != "/":
            self.path = parsed_url.path
        else:
            self.path = ""
        self.query = parsed_url.query
        
        self.params = {}
        self.depth_of_finding = depth_of_finding
        
        if len(parsed_url.query) > 0:
            query_splitted = self.query.split("&")
            for splits in query_splitted:
                tmp = splits.split("=")
                if len(tmp) == 2:
                    param_name = tmp[0]
                    param_value = tmp[1]
                else:
                    param_name = tmp[0]
                    param_value = None
                if param_name in self.params:
                    self.params[param_name].append(param_value)
                else:
                    self.params[param_name] = [param_value]
            keys = self.params.keys()
            keys = sorted(keys)
            tmp_params = {}
            for key in keys:
                tmp_params[key] = self.params[key]           
            self.params = tmp_params
        
    def get_url_structure(self):
        url = self.scheme + "://" + self.domain + self.path
        params = self.params
        return url, params
    
    
    def get_hash(self):
        path, params = self.get_url_structure()
        s_to_hash = path
        for k in params:
            s_to_hash += "++" + k
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()
         
        
    def toString(self):
        return self.complete_url
        
        
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.toString() == other.toString()

    def __ne__(self, other):
        return not self.__eq__(other)        
   
class Link():
    
    def __init__(self, url, dom_adress, html_id = "", html_class = ""):
        self.url = url 
        self.dom_adress = dom_adress
        self.html_id = html_id
        self.html_class = html_class
        
    def toString(self):
        res = "["
        res += "HREF: " + self.url.toString()
        res += " - Domadress: " + self.dom_adress
        if self.html_id != "":
            res += " - ID: " + self.html_id
        if self.html_class != "":
            res += " - Class: " + self.html_class
        res += "]"
        return res
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.url.toString() == other.url.toString()

    def __ne__(self, other):
        return not self.__eq__(other) 
         
class HtmlForm():
    def __init__(self, parameters, action, method, submit, dom_adress):
        self.parameter = parameters # Array of FormInput's
        self.action = action
        self.method = method
        self.submit = submit # Forminput triggering submission
        self.dom_adress = dom_adress
        self.parameter = sorted(self.parameter, key = lambda parameter: parameter.name)
        
    def toString(self):
        msg = "[Form: Action: '" + self.action + "' Method:' "+ self.method +"' - DomAdress: " + self.dom_adress +"  \n"
        for elem in self.parameter:
            msg += "[Param: " + str(elem.tag) + " Name: " + str(elem.name) + " Inputtype: " + str(elem.input_type) + " Values: " + str(elem.values) + "] \n"
        return msg + "]"
    
    def hasSubmit(self):
        return self.submit != None
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.get_hash() == other.get_hash()

    def __ne__(self, other):
        return not self.__eq__(other) 
    
    def get_hash(self):
        s_to_hash = self.action + ";" + self.method + ";"
        for p in self.parameter:
            s_to_hash += p.name + ";" + p.tag + ";" + str(p.input_type) + ";"
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()
     
class FormInput():
    
    def __init__(self, tag, name, input_type = "", values = None):
        self.tag = tag
        self.name = name
        self.values = values
        self.input_type = input_type
        
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.values is not None:
            for val in self.values:
                if other.values is None or not val in other.values:
                    return False
        return self.tag == other.tag and self.name == other.name and self.input_type == other.input_type 

    def __ne__(self, other):
        return not self.__eq__(other) 

class InputField():
    
    def __init__(self, input_type, dom_adress, html_id = None, html_class = None, value = None):
        self.input_type = input_type
        self.html_id = html_id
        self.html_class = html_class
        self.value = value  #Predifiend value, if available... 
        
class ClickableType(Enum):
    UI_Change = 0
    Link = 1
    Creates_new_navigatables = 2
    Error = 3
    SendingAjax = 4
    Ignored_by_Crawler = 5
    Unsuported_Event = 6
    
class CrawlerUser():
    
    def __init__(self, username,  user_level, url_with_login_form = None, login_data = None):
        self.login_data = login_data
        self.username = username
        self.url_with_login_form = url_with_login_form
        self.visited_urls = []
        self.visited_pages = {}
        self.visited_delta_pages = {}
        self.user_id = None
        self.user_level =   user_level
        self.sessions = []

class CrawlSpeed(Enum):
    Slow = 0
    Medium = 1
    Fast = 2
    Speed_of_Lightning = 3        
        
class CrawlConfig():
    
    def __init__(self, name, domain, max_depth = 5, max_click_depth = 5, crawl_speed = CrawlSpeed.Medium):
        self.name = name
        self.max_depth = max_depth
        self.max_click_depth = max_click_depth
        self.domain = domain
        self.crawl_speed = crawl_speed
        

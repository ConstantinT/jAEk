'''
Created on 12.11.2014

@author: constantin
'''
import logging
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkCookie,\
    QNetworkCookieJar
from PyQt5.QtCore import QUrl
from pip._vendor.requests.utils import dict_from_cookiejar
from time import time, sleep
from models import FormInput, InputField, CrawlSpeed
from models import HtmlForm
from PyQt5.Qt import QWebPage
from urllib.parse import urlparse
import models


class AbstractFilter(QWebPage):
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium):
        QWebPage.__init__(self, parent)
        self.app = parent.app
        self.wait_intervall = .1
        self.mainFrame().javaScriptWindowObjectCleared.connect(self.jsWinObjClearedHandler)
        self.loadFinished.connect(self.loadFinishedHandler)     
        
        if crawl_speed == CrawlSpeed.Slow:
            self.wait_for_processing = 1
            self.wait_for_event = 2
        if crawl_speed == CrawlSpeed.Medium:
            self.wait_for_processing = 0.3
            self.wait_for_event = 1
        if crawl_speed == CrawlSpeed.Fast:
            self.wait_for_processing = 0.1
            self.wait_for_event = 0.5
        if crawl_speed == CrawlSpeed.Speed_of_Lightning:
            self.wait_for_processing = 0.01
            self.wait_for_event = 0.1
        
        f = open('js/lib.js', 'r')
        self._js_lib = f.read()
        f.close()
        
        if proxy != "" and port != 0: 
            manager = QNetworkAccessManager()
            p = QNetworkProxy(QNetworkProxy.HttpProxy, proxy, port, None, None)
            manager.setProxy(p)
            self.setNetworkAccessManager(manager)
    
    def updateCookieJar(self, cookiejar, requested_url):     
        qnetworkcookie_list = []
        c = dict_from_cookiejar(cookiejar)
        qcookiejar = QNetworkCookieJar()
        for k in c: 
            tmp_cookiejar = QNetworkCookie(k, c[k])
            qnetworkcookie_list.append(tmp_cookiejar) 
            qcookiejar.setCookiesFromUrl(qnetworkcookie_list,QUrl(requested_url))
        self.networkAccessManager().setCookieJar(qcookiejar)
    
    def userAgentForUrl(self, url):
        return "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
    
    def loadFinishedHandler(self, result):
        pass
    
    def _wait(self, waittime=1):
        """Wait for delay time
        """
        deadline = time() + waittime
        while time() < deadline:
            sleep(0)
            self.app.processEvents()
        
    def get_dom_address(self, elem):
        dom_address = []
        elem = elem.parent()
        while elem.tagName() != "BODY":
            dom_address.append(elem.tagName())
            elem = elem.parent()
        tmp = dom_address[::-1] # Trick to revert lists        
        return tmp 
    
    def jsWinObjClearedHandler(self): #Adding here the js-scripts corresponding to the phases
        self.mainFrame().evaluateJavaScript(self._js_lib)
    
class LinkExtractor(AbstractFilter):
    '''
    Simple Link extractor, extracts links to own page
    '''
    def __init__(self, parent, proxy = "" , port = 0, crawl_speed = CrawlSpeed.Medium):
        super(LinkExtractor, self).__init__(parent, proxy, port, crawl_speed)
        
        self._process_finished = False        
        self.domain_handler = None
        
    def extract_elements(self, html, requested_url, timeout = 10):
        if self.domain_handler is None:
            raise DomainHandlerNotSetException("You must set the DomainHandler before extracting Links...")
           
        logging.debug("Start extracting links on " + requested_url + "...") 
        t = 0
        self.found_paths = []
        self._process_finished = False 
        self._requested_url = requested_url
        self.domain = self.get_domain(requested_url)
        self.mainFrame().setHtml(html, QUrl(requested_url))
        
        while(not self._process_finished and t < timeout):
            t += self.wait_for_processing
            self._wait(self.wait_for_processing)
        
        if not self._process_finished:
            logging.debug("Timeout Occurs")
        
        self.mainFrame().setHtml(None)
        return self.found_paths
    
    def get_domain(self, url):
        o = urlparse(url)
        return o.netloc
        
    
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(LinkExtraktor): " + message + " at: " + str(lineNumber) + " SourceID: " + str(sourceID))
        pass
    
    def loadFinishedHandler(self, result):
        if not self._process_finished:
            elems = self.mainFrame().findAllElements("a")
            res = self._extract_links(elems)
            self.found_paths.extend(res)
            self._process_finished = True
        
    def javaScriptConfirm(self, frame, msg):
        return True
    
    def _extract_links(self, elems):
        found_links = []
        if(len(elems) == 0):
            #logging.debug("No links found...")
            pass
        else:
            for elem in elems:
                href = elem.attribute("href")
                #logging.debug(str(type(elem)) + " href: " + str(href) + " Tagname: " + str(elem.tagName()))
                if href == "/" or href == "#" or href == self._requested_url or href == "" or "javascript:" in href: #or href[0] == '#':
                    continue
                elif self.domain in href or len(href) > 1:
                    html_id = elem.attribute("id")
                    html_class = elem.attribute("class")
                    dom_adress = elem.evaluateJavaScript("getXPath(this)")
                    url = self.domain_handler.create_url(href, self._requested_url)
                    link = models.Link(url, dom_adress, html_id, html_class)
                    found_links.append(link)
                elif "http://" in href or "https://" in href:
                    continue                
                else:
                    logging.debug("Elem has attribute href: " + str(elem.attribute("href") + " and matches no criteria"))
        return found_links  
    
class FormExtractor(AbstractFilter):
    """
    Class that is able to extract forms with their input-elements. Now supported:
    <input type="text, button, radio">, <button>, <select>
    Todo: <textarea>, <datalist> together with <input>, <keygen>, (<output>
    """
    
    def __init__(self, parent, proxy, port, crawl_speed = CrawlSpeed.Medium):
        super(FormExtractor, self).__init__(parent, proxy, port, crawl_speed)
        self._process_finished = False
            
    def extract_forms(self, html, requested_url, timeout = 60):   
        logging.debug("Start extracting forms on {}...".format(requested_url)) 
        t = 0
        self.forms = []
        self._process_finished = False
        self._requested_url = requested_url
        self.mainFrame().setHtml(html, QUrl(requested_url))
        
        while(not self._process_finished and t < timeout):
            t += self.wait_for_processing
            self._wait(self.wait_for_processing)
        
        if not self._process_finished:
            logging.debug("timeout occurs")
        
        self.mainFrame().setHtml(None)
        return self.forms
         
    
    def loadFinishedHandler(self, result):
        if not self._process_finished:
            self.mainFrame().evaluateJavaScript(self._js_lib)
            forms = self.mainFrame().findAllElements("form")
            for form in forms:
                action = form.attribute("action")
                method = form.attribute("method")
                form_params = self._extracting_information(form)
            
                self.forms.append(HtmlForm(form_params, action, method))
        self._process_finished = True  
    
    def _extracting_information(self, elem):
        result = []
        inputs = elem.findAll("input")
        radio_buttons = {} # key = name, value = array mit values

        for input_el in inputs:
            tagname = input_el.tagName()
            if input_el.hasAttribute("type"):
                input_type = input_el.attribute("type")
                if input_type != "radio": #no radio button
                    if input_el.hasAttribute("name"):
                        name = input_el.attribute("name")
                    else:
                        continue
                    if input_el.hasAttribute("value"):
                        value = [input_el.attribute("value")]
                    else:
                        value = None
                    result.append(FormInput(tagname, name, input_type, value)) 
                else: # input is radiobutton
                    name = input_el.attribute("name")
                    if name in radio_buttons: # Radio-Button name exists
                        radio_buttons[name].append(input_el.attribute("value"))
                    else: #Radiobutton name exists not
                        radio_buttons[name] = []
                        radio_buttons[name].append(input_el.attribute("value"))
        for key in radio_buttons:
            result.append(FormInput(tagname, key, input_type, radio_buttons[key]))
        buttons = elem.findAll("button")
        for button in buttons:
            tagname = button.tagName()
            if button.hasAttribute("type"):
                button_type = button.attribute("type")
            else:
                button_type = None
                logging.debug("Something mysterious must have happened...")
            if button.hasAttribute("name"):
                name = button.attribute("name")
            else:
                continue
            if button.hasAttribute("value"):
                value = [button.attribute("value")]
            else:
                value = None
                    #logging.debug(tagname + " " + name + " " + input_type + " " + value)
            result.append(FormInput(tagname, name, button_type, value)) 
        
        selects = elem.findAll("select")#<select> <option>
        for select in selects:  
            select_name = select.attribute("name")
            options = select.findAll("option")
            values = []
            for option in options:
                values.append(option.attribute("value"))
            f_input = FormInput(select.tagName(), select_name, None, values)
            result.append(f_input) 
        return result

class InputFinder(AbstractFilter):
    '''
    Finds input fields, not in forms...
    '''
    def __init__(self, parent, proxy = "" , port = 0):
        super(InputFinder, self).__init__(parent, proxy, port)
        self._process_finished = False        
        
    def extract_elements(self, html, requested_url, timeout = 10):
        logging.debug("Start extracting static anchor-tags on " + requested_url + "...") 
        t = 0
        self.found_paths = []
        self._process_finished = False 
        self._requested_url = requested_url
        self.mainFrame().setHtml(html, QUrl(requested_url))
        
        while(not self._process_finished and t < timeout):
            t += self.wait_for_processing
            self._wait(self.wait_for_processing)
        
        if not self._process_finished:
            logging.debug("Timeout Occurs")
        
        self.mainFrame().setHtml(None)
        return self.found_paths
    
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(LinkExtraktor): " + message + " at: " + str(lineNumber) + " SourceID: " + str(sourceID))
        pass
    
    def loadFinishedHandler(self, result):
        if not self._process_finished:
            elems = self.mainFrame().findAllElements("<input>")
            res = self._extract_links(elems)
            self._process_finished = True
        
    
    def _extract_input_text_fields(self, elems):
        found_inputs = []
        if(len(elems) == 0):
            #logging.debug("No links found...")
            pass
        else:
            for elem in elems:
                if elem.attribute("type") == "text":
                    input_type = elem.attribute("type")
                    html_id = elem.attribute("id")
                    html_class = elem.attribute("class")
                    std_value = elem.attribute("value")
                    dom_adress = elem.evaluateJavaScript("getXPath(this)")
                    if not "form" in dom_adress:
                        tmp = InputField(input_type, dom_adress, html_id, html_class, std_value)
                        found_inputs.append(tmp)
                
            
            
        return found_inputs  
                        
class DomainHandlerNotSetException(Exception):  
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)  
    
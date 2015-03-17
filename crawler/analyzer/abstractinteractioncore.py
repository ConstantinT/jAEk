'''
Created on 21.11.2014

@author: constantin
'''

from PyQt5.Qt import QWebPage, pyqtSlot, QWebSettings
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkCookie,\
    QNetworkCookieJar
from PyQt5.QtCore import QObject, QUrl

import json

from time import time, sleep
from pip._vendor.requests.utils import dict_from_cookiejar
from models.utils import CrawlSpeed
import logging


class AbstractInteractionCore(QWebPage):
    '''
    classdocs
    '''    
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium, network_access_manager = None):
        QWebPage.__init__(self, parent)
        self.app = parent.app
        self._jsbridge = JsBridge(self)
        self.loadFinished.connect(self.loadFinishedHandler)
        self.mainFrame().javaScriptWindowObjectCleared.connect(self.jsWinObjClearedHandler)
        self.frameCreated.connect(self.frameCreatedHandler)

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
        
        f = open("js/lib.js", "r")
        self._lib_js = f.read()
        f.close()
        
        f = open("js/ajax_observer.js")
        self._xhr_observe_js = f.read()
        f.close()
        
        f = open("js/timing_wrapper.js")
        self._timeming_wrapper_js = f.read()
        f.close()
        
        
        f = open("js/ajax_interceptor.js")
        self._xhr_interception_js = f.read()
        f.close()
        
        f = open("js/addeventlistener_wrapper.js")
        self._addEventListener = f.read()
        f.close()
        
        f = open("js/md5.js")
        self._md5 = f.read()
        f.close()

        f = open('js/property_obs.js', 'r')
        self._property_obs_js = f.read()
        f.close()

        enablePlugins = False
        loadImages = False
        self.settings().setAttribute(QWebSettings.PluginsEnabled, enablePlugins)
        self.settings().setAttribute(QWebSettings.JavaEnabled, enablePlugins)
        self.settings().setAttribute(QWebSettings.AutoLoadImages, loadImages)
        self.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        self.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
        
        if network_access_manager:
            self.setNetworkAccessManager(network_access_manager)
        
        if proxy != "" and port != 0: 
            manager = self.networkAccessManager()
            p = QNetworkProxy(QNetworkProxy.HttpProxy, proxy, port, None, None)
            manager.setProxy(p)
            self.setNetworkAccessManager(manager)
        self.networkAccessManager().finished.connect(self.loadComplete)

    def analyze(self, html, requested_url, timeout = 20):
        raise NotImplementedException()
    
    def userAgentForUrl(self, url):
        return "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
    
    def loadFinishedHandler(self, result):
        pass
    
    def frameCreatedHandler(self, frame):
        pass
    
    def jsWinObjClearedHandler(self):
        pass
    
    def javaScriptConfirm(self, frame, msg):
        return True
    
    def javaScriptPrompt(self, *args, **kwargs):
        return True
            
    def updateCookieJar(self, cookiejar, requested_url):     
        qnetworkcookie_list = []
        c = dict_from_cookiejar(cookiejar)
        qcookiejar = QNetworkCookieJar()
        for k in c: 
            tmp_cookiejar = QNetworkCookie(k, c[k])
            qnetworkcookie_list.append(tmp_cookiejar)
        qcookiejar.setCookiesFromUrl(qnetworkcookie_list,QUrl(requested_url))
        self.networkAccessManager().setCookieJar(qcookiejar)
    
    def _wait(self, waittime=1):
        """Wait for delay time
        """
        deadline = time() + waittime
        while time() < deadline:
            sleep(0)
            self.app.processEvents()
            
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console: " + message + " at: " + str(lineNumber))
        pass

    def loadComplete(self, reply):
        pass

    def search_element_with_id(self, element_id):
        elem = self.mainFrame().findAllElements("#" + str(element_id))
        if len(elem) > 0:
            return elem[0] # maybe check if there is more than one element
        else:
            return None

    def search_element_with_class(self, cls, dom_adress):
        css_cls_definition = ""
        classes = cls.split(" ")
        for cls in classes: #converting class names in css-compatible classnames
            cls = "." + cls
            css_cls_definition = css_cls_definition + cls + " "
        elems = self.mainFrame().findAllElements(css_cls_definition)
        for elem in elems:
            if dom_adress == elem.evaluateJavaScript("getXPath(this)"):
                return elem

    def search_element_without_id_and_class(self, dom_adress):
        check_dom_adress = dom_adress
        dom_address = dom_adress.split("/")
        current_element_in_dom = self.mainFrame().documentElement() #Is HTML-Element
        while len(dom_address) > 0 and current_element_in_dom is not None:
            target_tag_name = dom_address.pop(0) # Get and remove the first element
            target_tag_name = target_tag_name.upper()
            if len(target_tag_name) == 0:
                continue
            elif target_tag_name == "HTML": #or target_tag_name == "body":
                continue
            else:
                tmp = target_tag_name.find("[")
                if tmp > 0: # target_tag_name looks like tagname[index]
                    target_tag_name = target_tag_name.split("[")
                    index = int(target_tag_name[1].split("]")[0]) # get index out of target_tag_name
                    target_tag_name = target_tag_name[0] # target_tag_name name
                    last_child = current_element_in_dom.lastChild()
                    tmp_element = current_element_in_dom.findFirst(target_tag_name) # takes first child
                    if tmp_element.tagName() == target_tag_name: # if firstchild is from type of target_tag_name, subtrakt 1 from index
                        index -= 1;
                    counter = 9999 #Sometimes comparing with last child went wrong, therefore we have an backup counter
                    while index > 0 and tmp_element != last_child: # take next sibbling until index is 0, if target_tag_name is equal subtrakt one
                        tmp_element = tmp_element.nextSibling() #
                        if tmp_element.tagName() == target_tag_name:
                            index -= 1
                        counter -= 1
                        if counter == 0: #If counter 0 then break, we wont find it anymore
                            current_element_in_dom = None
                            break
                    if index == 0 and tmp_element.tagName() == target_tag_name:
                        current_element_in_dom = tmp_element
                    else: #We miss the element
                        current_element_in_dom = None
                else: #target_tag_name is the only of his type, or the first...is die hell
                    tmp_element = current_element_in_dom.firstChild()
                    last_child = current_element_in_dom.lastChild()
                    counter = 9999
                    while tmp_element.tagName() != target_tag_name and tmp_element != last_child and counter > 0:
                        #logging.debug(tmp_element.tagName())
                        counter -= 1
                        if tmp_element.tagName() == target_tag_name:
                            current_element_in_dom = tmp_element
                            break
                        else:
                            tmp_element = tmp_element.nextSibling()
                    if tmp_element.tagName() != target_tag_name or counter == 0:
                        current_element_in_dom = None
                    else:
                        current_element_in_dom = tmp_element

        tmp_element = None
        last_child = None
        dom_address = None

        if current_element_in_dom == None:
            #logging.debug("Current Elem is None")
            return None
        if current_element_in_dom.evaluateJavaScript("getXPath(this)") != check_dom_adress:
            logging.debug("Element not found: " + str(current_element_in_dom.evaluateJavaScript("getXPath(this)")) + " : " + str(check_dom_adress))
            return None
        else:
            #logging.debug("Element: " + str(current_element_in_dom.evaluateJavaScript("getXPath(this)")) + " found...")
            return current_element_in_dom




class JsBridge(QObject):

    
    def __init__(self, analyzer):
        QObject.__init__(self)
        self.anyalyzer = analyzer
        self._ajax_request = []
    @pyqtSlot(str)
    def add_EventListener_to_Element(self, msg):
        msg = json.loads(msg)
        self.anyalyzer.add_eventlistener_to_element(msg)
    @pyqtSlot(str)
    def xmlHTTPRequestOpen(self, msg):
        msg = json.loads(msg)
        self._ajax_request.append(msg)
    @pyqtSlot(str)   
    def xmlHTTPRequestSend(self, msg):
        msg = json.loads(msg)
        according_open = self._ajax_request.pop(0)
        according_open['parameter'] = msg['parameter']
        self.anyalyzer.capturing_requests(according_open)
    @pyqtSlot(str)
    def timeout(self, msg):
        msg = json.loads(msg)
        msg['type'] = "timeout"
        self.anyalyzer.capture_timeout_call(msg)
    @pyqtSlot(str)
    def intervall(self, msg):
        msg = json.loads(msg)
        msg['type'] = "intervall"
        #logging.debug(msg)
        self.anyalyzer.capture_timeout_call(msg)
    @pyqtSlot(str)
    def watch(self, msg):
        #msg = json.loads(msg)
        msg['type'] = "intervall"
        #logging.debug(msg)
    @pyqtSlot(str)
    def add_eventlistener_to_element(self, msg):
        msg = json.loads(msg)
        #logging.debug(msg)
        self.anyalyzer.add_eventlistener_to_element(msg)
        
class NotImplementedException(Exception):  
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value) 
    


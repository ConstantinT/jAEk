'''
Created on 21.11.2014

@author: constantin
'''

from PyQt5.Qt import QWebPage, pyqtSlot, QWebSettings
import json

from time import time, sleep
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkCookie,\
    QNetworkCookieJar
from PyQt5.QtCore import QObject, QUrl
from pip._vendor.requests.utils import dict_from_cookiejar
import models

class AbstractAnalyzer(QWebPage):
    '''
    classdocs
    '''    
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = models.CrawlSpeed.Medium):
        QWebPage.__init__(self, parent)
        self.app = parent.app
        self._jsbridge = JsBridge(self)
        self.loadFinished.connect(self.loadFinishedHandler)
        self.mainFrame().javaScriptWindowObjectCleared.connect(self.jsWinObjClearedHandler)
        self.frameCreated.connect(self.frameCreatedHandler)

        if crawl_speed == models.CrawlSpeed.Slow:
            self.wait_for_processing = 1
            self.wait_for_event = 2
        if crawl_speed == models.CrawlSpeed.Medium:
            self.wait_for_processing = 0.3
            self.wait_for_event = 1
        if crawl_speed == models.CrawlSpeed.Fast:
            self.wait_for_processing = 0.1
            self.wait_for_event = 0.5
        if crawl_speed == models.CrawlSpeed.Speed_of_Lightning:
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
        
        enablePlugins = False
        loadImages = False
        self.settings().setAttribute(QWebSettings.PluginsEnabled, enablePlugins)
        self.settings().setAttribute(QWebSettings.JavaEnabled, enablePlugins)
        self.settings().setAttribute(QWebSettings.AutoLoadImages, loadImages)
        self.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        self.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
        
        if proxy != "" and port != 0: 
            manager = QNetworkAccessManager()
            p = QNetworkProxy(QNetworkProxy.HttpProxy, proxy, port, None, None)
            manager.setProxy(p)
            self.setNetworkAccessManager(manager)

    def analyze(self, html, requested_url, timeout = 20):
        raise NotImplementedException()
    
    def userAgentForUrl(self, url):
        return "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
    
    def loadFinishedHandler(self, result):
        pass
    
    def frameCreatedHandler(self):
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
        #logging.debug("Console: " + message + " at: " + str(lineNumber))
        pass

class JsBridge(QObject):

    
    def __init__(self, webpage):
        QObject.__init__(self)
        self._webpage = webpage
        self._ajax_request = []
    @pyqtSlot(str)
    def addEventListener(self, msg):
        msg = json.loads(msg)
        #logging.debug(msg)
        self._webpage.add_element_with_event(msg)
    @pyqtSlot(str)
    def xmlHTTPRequestOpen(self, msg):
        msg = json.loads(msg)
        #logging.debug("xmHTTPRequestOpen: " + str(msg))
        self._ajax_request.append(msg)
    @pyqtSlot(str)   
    def xmlHTTPRequestSend(self, msg):
        msg = json.loads(msg)
        according_open = self._ajax_request.pop(0)
        according_open['parameter'] = msg['parameter']
        self._webpage.capturing_requests(according_open)
    @pyqtSlot(str)
    def timeout(self, msg):
        msg = json.loads(msg)
        msg['type'] = "timeout"
        self._webpage.capture_timeout_call(msg)
    @pyqtSlot(str)
    def intervall(self, msg):
        msg = json.loads(msg)
        msg['type'] = "intervall"
        #logging.debug(msg)
        self._webpage.capture_timeout_call(msg)
    @pyqtSlot(str)
    def watch(self, msg):
        #msg = json.loads(msg)
        msg['type'] = "intervall"
        #logging.debug(msg)
    @pyqtSlot(str)
    def add_element_with_event(self, msg):
        msg = json.loads(msg)
        #logging.debug(msg)
        self._webpage.add_element_with_event(msg)
        
class NotImplementedException(Exception):  
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value) 
    


'''
Created on 23.02.2015

@author: constantin
'''
from PyQt5.Qt import QWebPage, QNetworkAccessManager, QNetworkProxy,\
    QNetworkCookie, QNetworkCookieJar, QUrl
from models.utils import CrawlSpeed
from requests.utils import dict_from_cookiejar
from time import sleep, time


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
        return "MyCrawlerTest1"
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
    
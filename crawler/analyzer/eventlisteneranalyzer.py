'''
Created on 23.02.2015

@author: constantin
'''
from analyzer.abstractanalyzer import AbstractAnalyzer
import logging
from PyQt5.Qt import QUrl
from models.utils import CrawlSpeed
from models.clickable import Clickable


    
class EventlistenerAnalyzer(AbstractAnalyzer):
    
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium):
        super(EventlistenerAnalyzer, self).__init__(parent, proxy, port, crawl_speed)
        self._loading_complete = False     
        
        f = open('js/lib.js', 'r')
        self._js_lib = f.read()
        f.close()
        f = open('js/addeventlistener_wrapper.js', 'r')
        self._add_listener_wrapper = f.read()
        f.close()


    def analyze(self, html, requested_url, timeout=20):
        logging.debug("AddEventlistenerObserver started on {}...".format(requested_url))
        self._loading_complete = False
        self._analyzing_finished = False
        self.new_clickables = []
        self.mainFrame().setHtml(html, QUrl(requested_url))
        t = 0
        while(not self._loading_complete and t < timeout ): # Waiting for finish processing
            #logging.debug("Waiting...")
            self._wait(self.wait_for_processing) 
            t += self.wait_for_processing
        
        if not self._loading_complete:
            logging.debug("Timeout occured...")
        
        
        self._wait(self.wait_for_event)
        self._analyzing_finished = True
        self.mainFrame().setHtml(None)
        
        tmp = []
        for c in self.new_clickables:
            if c not in tmp:
                tmp.append(c)
        
        return tmp
    
    def add_eventlistener_to_element(self, msg):
        try:
            #logging.debug(msg)
            if "id" in msg:
                if msg != "":
                    id = msg['id']
                else:
                    id = None
            
            domadress = msg['addr']
            
            event = msg['event']
            
            if event == "": 
                event = None
            
            if "tag" in msg:
                tag = msg['tag']
            else:
                tag = None
            
            if "class" in msg:
                if msg['class'] != "":
                    html_class = msg['class']
                else:
                    html_class = None
                    
            function_id = msg['function_id']
            if tag is not None and domadress != "":
                tmp = Clickable(event, tag, domadress, id, html_class, function_id=function_id)
                self.new_clickables.append(tmp)
        except KeyError as err:
            logging.debug(err)
            pass
        
    def loadFinishedHandler(self, result):
        if not self._analyzing_finished:
            if result:
                self._loading_complete = True
            
    def jsWinObjClearedHandler(self): #Adding here the js-scripts corresponding to the phases
        if not self._analyzing_finished:
            self.mainFrame().addToJavaScriptWindowObject("jswrapper", self._jsbridge)
            self.mainFrame().evaluateJavaScript(self._js_lib)
            self.mainFrame().evaluateJavaScript(self._md5)
            self.mainFrame().evaluateJavaScript(self._add_listener_wrapper) 
       
    
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(AddEventlistenerObserver): " + message + " at: " + str(lineNumber) + " SourceID: " + str(sourceID))
        pass




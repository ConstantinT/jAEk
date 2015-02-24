'''
Created on 23.02.2015

@author: constantin
'''
from analyzer.abstractanalyzer import AbstractAnalyzer
from models.utils import CrawlSpeed
import logging
from PyQt5.Qt import QUrl
from models.clickable import Clickable



class PropertyAnalyzer(AbstractAnalyzer):
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium):
        super(PropertyAnalyzer, self).__init__(parent, proxy, port, crawl_speed)
        
        
        # Loading necessary files
        f = open('js/lib.js', 'r')
        self._js_lib = f.read()
        f.close()
        f = open('js/property_obs.js', 'r')
        self._property_obs_js = f.read()
        f.close()


    def analyze(self, html, requested_url, timeout=20):
        logging.debug("PropertyAnalyzer on {} started...".format(requested_url))
        self._loading_complete = False
        self._analyzing_finished = False 
        self.new_clickables = []
        
        self.mainFrame().setHtml(html, QUrl(requested_url))
        t = 0
        while(not self._loading_complete and t < timeout ): # Waiting for finish processing
            self._wait(self.wait_for_processing) 
            t += self.wait_for_processing
            
        if not self._loading_complete:
            logging.debug("Timeout Occurs")
       
        self._analyzing_finished = True
        self.mainFrame().setHtml(None)
        return self.new_clickables
    
    def add_eventlistener_to_element(self, msg):
        try:
            if msg['id'] != None and msg['id'] != "":
                id = msg['id']
            else: 
                id = None
            dom_adress = msg['dom_adress']
            event = msg['event']
            if event == "":
                event = None
            tag = msg['tag']
            if msg['class'] != None and msg['class'] != "":
                html_class = msg['class']
            else:
                html_class = None
            function_id = msg['function_id']
            tmp = Clickable(event, tag, dom_adress, id, html_class, function_id=function_id)
            self.new_clickables.append(tmp)
        except KeyError as err:
            logging.debug(err)
                
    def loadFinishedHandler(self, result):
        if not self._analyzing_finished:
            if result:
                self.mainFrame().evaluateJavaScript(self._property_obs_js)
                self._loading_complete = True
    
            
    def jsWinObjClearedHandler(self): #Adding here the js-scripts corresponding to the phases
        if not self._analyzing_finished:
            self.mainFrame().addToJavaScriptWindowObject("jswrapper", self._jsbridge)
            self.mainFrame().evaluateJavaScript(self._md5)
            self.mainFrame().evaluateJavaScript(self._js_lib)
       

    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(PropertyAnalyzer): " + message + " at: " + str(lineNumber) + " SourceID: " + str(sourceID))
        pass
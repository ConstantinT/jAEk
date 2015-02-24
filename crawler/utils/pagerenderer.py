'''
Created on 23.02.2015

@author: constantin
'''
from analyzer.abstractanalyzer import AbstractAnalyzer
from models.utils import CrawlSpeed
import logging
from time import sleep, time

"""
This Class prepares a page for analyzing... it renders the initial page and removes all <video> because of memory corruption during processing.
"""  
class PageRenderer(AbstractAnalyzer):
    def __init__(self, parent, proxy, port, crawl_speed = CrawlSpeed.Medium):
        super(PageRenderer, self).__init__(parent,proxy, port, crawl_speed)
        self._loading_complete = False
        f = open("js/lib.js", "r")
        self._lib_js = f.read()
        f.close()
        self._current_event = None
        self._html = None
        self._analyzing_finished = False
        self.element_to_click = None
        self.element_to_click_model = None
        
    def loadFinishedHandler(self, result):
        if not self._analyzing_finished: # Just to ignoring setting of non page....
            self._wait(0.5)
            self._load_finished = True
            
    def render(self, requested_url, html, timeout=10):
        logging.debug("Render page...")
        self._load_finished = False
        self._analyzing_finished = False
        t = 0
        self.mainFrame().setHtml(html)
        while not self._load_finished and t < timeout:
            self._wait(0.1)
            t += 0.1        
        
        if not self._load_finished:
            logging.debug("Renderer timeout...")
        
        
        videos = self.mainFrame().findAllElements("video")
        if len(videos) > 0:
            logging.debug(str(len(videos)) + " Videos found...now removing them")
            for v in videos:
                v.removeFromDocument() 
        
        
        base_url = None
        head = self.mainFrame().findFirstElement("head")
        base = head.findFirst("base")
        if base.attribute("href") is not None and base.attribute("href") != "":
            base_url = base.attribute("href")
        html = self.mainFrame().toHtml()
       
        logging.debug("Base Url is: {}".format(base_url))
        self._analyzing_finished = True
        self.mainFrame().setHtml(None)
        return base_url, html
    
    def _wait(self, timeout=1):
        """Wait for delay time
        """
        deadline = time() + timeout
        while time() < deadline:
            sleep(0)
            self.app.processEvents()
            
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        #logging.debug("Console(PageBuilder): " + message + " at: " + str(lineNumber))
        pass
    
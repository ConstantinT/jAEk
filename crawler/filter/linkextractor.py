'''
Created on 23.02.2015

@author: constantin
'''
from models.link import Link
import logging
from urllib.parse import urlparse
from PyQt5.Qt import QUrl
from models.utils import CrawlSpeed
from filter.abstractfilter import AbstractFilter
from utils.execptions import DomainHandlerNotSetException

class LinkExtractor(AbstractFilter):
    '''
    Simple Link extractor, extracts links to own page
    '''
    def __init__(self, parent, proxy = "" , port = 0, crawl_speed = CrawlSpeed.Medium):
        super(LinkExtractor, self).__init__(parent, proxy, port, crawl_speed)
        
        self._process_finished = False        
        self.domain_handler = None
        self._base_url = None
        
    def extract_elements(self, html, requested_url, timeout = 10, base_url = None):
        if self.domain_handler is None:
            raise DomainHandlerNotSetException("You must set the DomainHandler before extracting Links...")
           
        logging.debug("Start extracting links on " + requested_url + "...") 
        t = 0
        if base_url is None:
            self._base_url = requested_url
        else:
            self._base_url = base_url
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
                    url = self.domain_handler.create_url(href, self._base_url)
                    link = Link(url, dom_adress, html_id, html_class)
                    found_links.append(link)
                elif "http://" in href or "https://" in href:
                    continue                
                else:
                    logging.debug("Elem has attribute href: " + str(elem.attribute("href") + " and matches no criteria"))
        return found_links  
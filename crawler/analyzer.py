'''
Created on 12.11.2014

@author: constantin
'''
import logging
from PyQt5.QtCore import QUrl, QObject
from time import time
from models import Clickable, AjaxRequest, TimemingRequest, CrawlSpeed
from abstractanalyzer import AbstractAnalyzer

class TimingAnalyzer(AbstractAnalyzer):
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium):
        super(TimingAnalyzer, self).__init__(parent, proxy, port, crawl_speed)
        
        self._loading_complete = False
        self._timing_events = [] # Time to wait for timeout in the webpage
        self._waiting_for = None #Specifies if we are waitng for timout or intervall
        self._capture_requests = False #Indicates when it is time to capture requests
        self._current_timing_event = None
        
        # Loading necessary files
        f = open('js/lib.js', 'r')
        self._js_lib = f.read()
        f.close()
        f = open('js/timing_wrapper.js', 'r')
        self._timing_wrapper = f.read()
        f.close()
        f = open('js/ajax_observer.js', "r")
        self._ajax_wrapper = f.read()
        f.close()

    def analyze(self, html, requested_url, timeout=5):
        logging.debug("Timing analyze on {} started...".format(requested_url))
        self._analyzing_finished = False
        self._loading_complete = False
        self.ignore_new_timeouts = False
        self.ajax_requests = []
        self._capture_requests = True
        self.mainFrame().setHtml(html, QUrl(requested_url))
        
        self.ignore_new_timeouts = True
        delay = 500
        overall_waiting_time = 0
        while len(self._timing_events) > 0:
            self._current_timing_event = self._timing_events.pop(0) #Take the first event(ordered by needed time
            self._waiting_for = self._current_timing_event[1] # Setting kind of event
            waiting_time_in_milliseconds = (self._current_timing_event[0] - overall_waiting_time) # Taking waiting time and convert it from milliseconds to seconds
            overall_waiting_time += waiting_time_in_milliseconds
            waiting_time_in_milliseconds = ((waiting_time_in_milliseconds - delay) / 1000.0)
            if waiting_time_in_milliseconds < 0.0:
                waiting_time_in_milliseconds = 0
            logging.debug("Now waiting for: {} seconds for {}".format(str(waiting_time_in_milliseconds), self._waiting_for))
            self._wait(waiting_time_in_milliseconds) # Waiting for 100 millisecond befor expected event
        
          
        self._analyzing_finished = True
        self.mainFrame().setHtml(None)
        return self.ajax_requests
        
    def loadFinishedHandler(self, result):
        if not self._analyzing_finished: # Just to ignoring setting of non page....
            if result:
                self._loading_complete = True
            
    def jsWinObjClearedHandler(self): #Adding here the js-scripts corresponding to the phases
        self.mainFrame().addToJavaScriptWindowObject("jswrapper", self._jsbridge)
        self.mainFrame().evaluateJavaScript(self._md5)
        self.mainFrame().evaluateJavaScript(self._js_lib)
        self.mainFrame().evaluateJavaScript(self._timing_wrapper)
        self.mainFrame().evaluateJavaScript(self._ajax_wrapper)

    def capture_timeout_call(self, timingevent):
        try:
            if self.ignore_new_timeouts:
                logging.debug("Ignoring: " + str(timingevent))
                return
            if timingevent['time'] != "undefined":
                time = timingevent['time'] # millisecond
                event_type = timingevent['type']
                event_id = timingevent['function_id']
                for prev_timing in self._timing_events:
                    if event_id == prev_timing[2]:
                        return 
                self._timing_events.append((time,event_type, event_id ))
                self._timing_events = sorted(self._timing_events, key=lambda e : e[0]) # Sort list
        except KeyError:
            pass
            #logging.debug("Key error occured")
    
    def capturing_requests(self, request):
        if self._capture_requests:
            logging.debug("Event captured..." + str(request))
            if self._current_timing_event is not None:
                ajax_request = TimemingRequest(request['method'], request['url'], self._current_timing_event[0], self._current_timing_event[1], self._current_timing_event[2])
            else:
                ajax_request = TimemingRequest(request['method'], request['url'], None, None, None)    
            self.ajax_requests.append(ajax_request)
        else:
            logging.debug("Missing Event: " + str(request))
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(TimingAnalyzer): " + message + " at: " + str(lineNumber) + " SourceID: " + str(sourceID))
        pass

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
    
    def add_element_with_event(self, msg):
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
    
    def add_element_with_event(self, msg):
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




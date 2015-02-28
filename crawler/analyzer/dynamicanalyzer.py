'''
Created on 24.02.2015

@author: constantin
'''
from analyzer.abstractanalyzer import AbstractAnalyzer
from models.utils import CrawlSpeed
import logging
from models.timemimngrequest import TimemingRequest
from models.clickable import Clickable
from PyQt5.Qt import QUrl



class Analyzer(AbstractAnalyzer):
    
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium):
        super(Analyzer, self).__init__(parent, proxy, port, crawl_speed)
        self._loading_complete = False
        self._analyzing_finished = False   
        
        
        
    def analyze(self, html, requested_url, timeout=20):
        logging.debug("Start with dynamic analyzing of {}...".format(requested_url))
        self._timemimg_requests = []
        self._add_eventlisteners_clickables = []
        self._timeming_events = []
        self._current_timeming_event = None
        self._loading_complete = False
        self._analyzing_finished = False  
        self.mainFrame().setHtml(html, QUrl(requested_url))
        
        t = 0
        while(not self._loading_complete and t < timeout ): # Waiting for finish processing
            #logging.debug("Waiting...")
            self._wait(self.wait_for_processing) 
            t += self.wait_for_processing

        overall_waiting_time = t
        buffer = 250
        while len(self._timeming_events) > 0:
            self._current_timeming_event = self._timeming_events.pop(0) #Take the first event(ordered by needed time
            self._waiting_for = self._current_timeming_event['event_type'] # Setting kind of event
            waiting_time_in_milliseconds = (self._current_timeming_event["time"] - overall_waiting_time) # Taking waiting time and convert it from milliseconds to seconds
            waiting_time_in_milliseconds = ((waiting_time_in_milliseconds + buffer) / 1000.0)
            if waiting_time_in_milliseconds < 0.0:
                waiting_time_in_milliseconds = 0
            logging.debug("Now waiting for: {} seconds for {}".format(str(waiting_time_in_milliseconds), self._waiting_for))
            self._wait(waiting_time_in_milliseconds) # Waiting for 100 millisecond before expected event
            overall_waiting_time += waiting_time_in_milliseconds
           
        
        self._analyzing_finished = True
        html_after_timeouts = self.mainFrame().toHtml()
        self.mainFrame().setHtml(None)
        return html_after_timeouts, self._add_eventlisteners_clickables, self._timemimg_requests
        
    
    def loadFinishedHandler(self, result):
        if not self._analyzing_finished: # Just to ignoring setting of non page....
            self._loading_complete = True
            
    def jsWinObjClearedHandler(self): #Adding here the js-scripts corresponding to the phases
        if not self._analyzing_finished:
            self.mainFrame().addToJavaScriptWindowObject("jswrapper", self._jsbridge)
            self.mainFrame().evaluateJavaScript(self._md5)
            self.mainFrame().evaluateJavaScript(self._lib_js)
            self.mainFrame().evaluateJavaScript(self._timeming_wrapper_js)
            self.mainFrame().evaluateJavaScript(self._xhr_observe_js)
            self.mainFrame().evaluateJavaScript(self._addEventListener)
    
    def capturing_requests(self, request):
        #logging.debug("Event captured..." + str(request))
        timeming_request = TimemingRequest(request['method'], request['url'], self._current_timeming_event["time"], self._current_timeming_event["event_type"], self._current_timeming_event["event_id"], request['paramter']) 
        self._timemimg_requests.append(timeming_request)
        
    def capture_timeout_call(self, timingevent):
        try:
            if timingevent['time'] != "undefined":
                time = timingevent['time'] # millisecond
                event_type = timingevent['type']
                event_id = timingevent['function_id']
                timeming_event = {"time": time, "event_type": event_type, "event_id": event_id}
                self._timeming_events.append(timeming_event)
                self._timeming_events = sorted(self._timeming_events, key=lambda e : e['time']) # Sort list
        except KeyError:
            pass
        
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
                self._add_eventlisteners_clickables.append(tmp)
        except KeyError as err:
            logging.debug(err)
            pass

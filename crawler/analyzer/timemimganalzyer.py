'''
Created on 23.02.2015

@author: constantin
'''
from analyzer.abstractanalyzer import AbstractAnalyzer
import logging
from PyQt5.Qt import QUrl
from models.timemimngrequest import TimemingRequest
from models.utils import CrawlSpeed

class TimingAnalyzer(AbstractAnalyzer):
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium):
        super(TimingAnalyzer, self).__init__(parent, proxy, port, crawl_speed)
        
        self._loading_complete = False
        self._timeming_events = [] # Time to wait for timeout in the webpage
        self._waiting_for = None #Specifies if we are waitng for timout or intervall
        self._capture_requests = False #Indicates when it is time to capture requests
        self._current_timeming_event = None
        
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
        while len(self._timeming_events) > 0:
            self._current_timeming_event = self._timeming_events.pop(0) #Take the first event(ordered by needed time
            self._waiting_for = self._current_timeming_event[1] # Setting kind of event
            waiting_time_in_milliseconds = (self._current_timeming_event[0] - overall_waiting_time) # Taking waiting time and convert it from milliseconds to seconds
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
                for prev_timing in self._timeming_events:
                    if event_id == prev_timing[2]:
                        return 
                self._timeming_events.append((time,event_type, event_id ))
                self._timeming_events = sorted(self._timeming_events, key=lambda e : e[0]) # Sort list
        except KeyError:
            pass
            #logging.debug("Key error occured")
    

    def capturing_requests(self, request):
        if self._capture_requests:
            logging.debug("Event captured..." + str(request))
            if self._current_timeming_event is not None:
                ajax_request = TimemingRequest(request['method'], request['url'], self._current_timeming_event[0], self._current_timeming_event[1], self._current_timeming_event[2])
            else:
                ajax_request = TimemingRequest(request['method'], request['url'], None, None, None)    
            self.ajax_requests.append(ajax_request)
        else:
            logging.debug("Missing Event: " + str(request))
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(TimingAnalyzer): " + message + " at: " + str(lineNumber) + " SourceID: " + str(sourceID))
        pass

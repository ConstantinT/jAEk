'''
Created on 24.02.2015

@author: constantin
'''
import logging

from PyQt5.QtCore import QByteArray
from PyQt5.QtNetwork import QNetworkRequest, QNetworkAccessManager
from PyQt5.Qt import QUrl

from core.interactioncore import InteractionCore
from analyzer.helper.formhelper import FormHelper
from analyzer.helper.linkhelper import LinkHelper
from models.utils import CrawlSpeed
from models.timemimngrequest import TimemingRequest
from models.clickable import Clickable


class MainAnalyzer(InteractionCore):
    def __init__(self, parent, proxy="", port=0, crawl_speed=CrawlSpeed.Medium, network_access_manager=None):
        super(MainAnalyzer, self).__init__(parent, proxy, port, crawl_speed, network_access_manager)
        self._loading_complete = False
        self._analyzing_finished = False
        self._link_helper = LinkHelper()
        self._form_helper = FormHelper()
        self._timemimg_requests = []
        self._new_clickables = []
        self._timeming_events = []
        self._current_timeming_event = None
        self.response_code = {}

    def analyze(self, url_to_request, timeout=10, current_depth=None, method="GET", data={}):
        logging.debug("Start with dynamic analyzing of {}...".format(url_to_request.toString()))
        self._timemimg_requests = []
        self._new_clickables = []
        self._timeming_events = []
        self._current_timeming_event = None
        self._loading_complete = False
        self._analyzing_finished = False
        self.response_code = {}
        if method == "GET":
            self.mainFrame().load(QUrl(url_to_request.toString()))
        else:
            request = self._make_request(url_to_request.toString())
            data = self.post_data_to_array(data)
            request.setRawHeader('Content-Type', QByteArray('application/x-www-form-urlencoded'))
            self.mainFrame().load(request,
                                  QNetworkAccessManager.PostOperation,
                                  data)
        t = 0
        while (not self._loading_complete and t < timeout ):  # Waiting for finish processing
            # logging.debug("Waiting...")
            self._wait(self.wait_for_processing)
            t += self.wait_for_processing

        overall_waiting_time = t
        buffer = 250
        while len(self._timeming_events) > 0 and overall_waiting_time < timeout:
            self._current_timeming_event = self._timeming_events.pop(0)  # Take the first event(ordered by needed time
            self._waiting_for = self._current_timeming_event['event_type']  # Setting kind of event
            waiting_time_in_milliseconds = (self._current_timeming_event[
                                                "time"] - overall_waiting_time)  # Taking waiting time and convert it from milliseconds to seconds
            waiting_time_in_milliseconds = ((waiting_time_in_milliseconds + buffer) / 1000.0)
            if waiting_time_in_milliseconds < 0.0:
                waiting_time_in_milliseconds = 0
            logging.debug(
                "Now waiting for: {} seconds for {}".format(str(waiting_time_in_milliseconds), self._waiting_for))
            self._wait(waiting_time_in_milliseconds)  # Waiting for 100 millisecond before expected event
            overall_waiting_time += waiting_time_in_milliseconds
        if overall_waiting_time < 1:
            self._wait((1-overall_waiting_time))
        self.mainFrame().evaluateJavaScript(self._property_obs_js)
        links, clickables = self._link_helper.extract_links(self.mainFrame(), url_to_request)
        forms = self._form_helper.extract_forms(self.mainFrame())
        self._wait(0.5)

        self._analyzing_finished = True
        html_after_timeouts = self.mainFrame().toHtml()
        response_url = self.mainFrame().url().toString()
        self.mainFrame().setHtml(None)
        f = open("main.txt", "w")
        f.write(html_after_timeouts)
        f.close()
        self._new_clickables.extend(clickables)
        response_code = None
        try:
            response_code = self.response_code[url_to_request.toString()]
        except KeyError:
            pass
        return response_code, response_url, html_after_timeouts, self._new_clickables, forms, links, self._timemimg_requests


    def loadFinishedHandler(self, result):
        if not self._analyzing_finished:  # Just to ignoring setting of non page....
            self._loading_complete = True


    def jsWinObjClearedHandler(self):  # Adding here the js-scripts corresponding to the phases
        if not self._analyzing_finished:
            self.mainFrame().addToJavaScriptWindowObject("jswrapper", self._jsbridge)
            self.mainFrame().evaluateJavaScript(self._md5)
            self.mainFrame().evaluateJavaScript(self._lib_js)
            self.mainFrame().evaluateJavaScript(self._timeming_wrapper_js)
            self.mainFrame().evaluateJavaScript(self._xhr_observe_js)
            self.mainFrame().evaluateJavaScript(self._addEventListener)

    def capturing_requests(self, request):
        # logging.debug("Event captured..." + str(request))
        try:
            params = request["parameter"]
        except KeyError:
            params = None
        try:
            timeming_request = TimemingRequest(request['method'], request['url'], self._current_timeming_event["time"],
                                               self._current_timeming_event["event_type"],
                                               self._current_timeming_event["event_id"], params)
            self._timemimg_requests.append(timeming_request)
        except TypeError:
            timeming_request = TimemingRequest(request['method'], request['url'], None, None, None, params)
            self._timemimg_requests.append(timeming_request)

    def capture_timeout_call(self, timingevent):
        try:
            if timingevent['time'] != "undefined":
                time = timingevent['time']  # millisecond
                event_type = timingevent['type']
                event_id = timingevent['function_id']
                timeming_event = {"time": time, "event_type": event_type, "event_id": event_id}
                self._timeming_events.append(timeming_event)
                self._timeming_events = sorted(self._timeming_events, key=lambda e: e['time'])  # Sort list
        except KeyError:
            pass


    def frameCreatedHandler(self, frame):
        logging.debug("Frame created")

    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(DynamicAnalyzer): " + message + " at: " + str(lineNumber) + " from: " + sourceID)

    def loadComplete(self, reply):
        if not self._analyzing_finished:
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) is None:
                logging.error("Response Code is None: Maybe, you dumb idiot, has set a proxy but not one running!!!")
                return
            self.response_code[reply.url().toString()] = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)


    def _make_request(self, url):
        request = QNetworkRequest()
        request.setUrl(QUrl(url))
        return request

    def post_data_to_array(self, post_data):
        post_params = QByteArray()
        for (key, value) in post_data.items():
            if isinstance(value, list):
                for val in value:
                    post_params.append(key + "=" + val + "&")
            else:
                post_params.append(key + "=" + value + "&")
        post_params.remove(post_params.length() - 1, 1)
        return post_params

    def add_eventlistener_to_element(self, msg):
        try:
            # logging.debug(msg)
            if "id" in msg:
                if msg != "":
                    id = msg['id']
                else:
                    id = None
            dom_address = msg['addr']
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
            if tag is not None and dom_address != "":
                tmp = Clickable(event, tag, dom_address, id, html_class, function_id=function_id)
                if tmp not in self._new_clickables:
                    self._new_clickables.append(tmp)
        except KeyError as err:
            # logging.debug(err)
            pass

    def javaScriptAlert(self, frame, msg):
        logging.debug("Alert occurs in frame: {} with message: {}".format(frame.baseUrl().toString(), msg))
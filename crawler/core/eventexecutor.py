'''
Created on 23.02.2015

@author: constantin
'''
import logging
import random
import string
from enum import Enum

from PyQt5.Qt import QUrl
from analyzer.helper.formhelper import extract_forms
from analyzer.helper.linkhelper import extract_links

from analyzer.helper.propertyhelper import property_helper
from models.ajaxrequest import AjaxRequest
from models.deltapage import DeltaPage
from models.enumerations import XHRBehavior
from models.keyclickable import KeyClickable
from core.interactioncore import InteractionCore
from models.utils import CrawlSpeed


class EventExecutor(InteractionCore):

    def __init__(self, parent, proxy="", port=0, crawl_speed=CrawlSpeed.Medium, network_access_manager=None):
        super(EventExecutor, self).__init__(parent, proxy, port, crawl_speed, network_access_manager)
        self._url_changed = False  # Inidicates if a event changes a location => treat it as link!
        self._new_url = None
        self.timeming_events = None
        self.none_key_events = ['click', 'focus', 'blur', 'dblclick', 'input', 'change',
                                 'mousedown', 'mousemove', 'mouseout', 'mouseover', 'mouseup',
                                 'resize', 'scroll', 'select', 'submit', 'load', 'unload', 'mouseleave']
        self.key_events = ['keyup', 'keydown', 'keypress']
        self.supported_events = self.none_key_events + self.key_events

        self.seen_timeouts = {}
        self.mainFrame().urlChanged.connect(self._url_changes)

    def execute(self, webpage, timeout=5, element_to_click=None, xhr_options=XHRBehavior.ObserveXHR, pre_clicks=[]):
        logging.debug(
            "EventExecutor test started on {}...".format(webpage.url) + " with " + element_to_click.toString())
        self._analyzing_finished = False
        self._loading_complete = False
        self.xhr_options = xhr_options
        self.element_to_click = None
        self.ajax_requests = []
        self._new_url = None
        self.timeming_events = None
        self._capturing_ajax = False
        self._new_clickables = []
        self.element_to_click = element_to_click
        self.mainFrame().setHtml(webpage.html, QUrl(webpage.url))
        target_tag = element_to_click.dom_address.split("/")
        target_tag = target_tag[-1]
        if target_tag in ['video']:
            return EventResult.UnsupportedTag, None

        t = 0.0
        while (not self._loading_complete and t < timeout ):  # Waiting for finish processing
            self._wait(0.1)
            t += 0.1
        if not self._loading_complete:
            logging.debug("Timeout occurs while initial page loading...")
            return EventResult.ErrorWhileInitialLoading, None
        # Prepare Page for clicking...
        self._wait(0.1)
        for click in pre_clicks:
            pre_click_elem = None
            logging.debug("Click on: " + click.toString())
            if click.id != None and click.id != "":
                pre_click_elem = self.search_element_with_id(click.id)
            if click.html_class != None and pre_click_elem == None:
                pre_click_elem = self.search_element_with_class(click.html_class, click.dom_address)
            if pre_click_elem == None:
                pre_click_elem = self.search_element_without_id_and_class(click.dom_address)

            if pre_click_elem is None:
                logging.debug("Preclicking element not found")
                return EventResult.PreviousClickNotFound, None

            js_code = click.event
            if js_code[0:2] == "on":
                js_code = js_code[2:]  # if event beginns with on, escape it
            js_code = "Simulate." + js_code + "(this);"
            pre_click_elem.evaluateJavaScript(js_code)  # Waiting for finish processing
            self._wait(self.wait_for_event)

            # Now execute the target event

        self._url_changed = False
        js_code = element_to_click.event
        if js_code[0:2] == "on":
            js_code = js_code[2:]  # if event begins with on, escape it
        is_key_event = False
        if js_code in self.key_events:
            is_key_event = True
            random_char = random.choice(string.ascii_letters)
            js_code = "Simulate." + js_code + "(this, '" + random_char + "');"
        else:
            js_code = "Simulate." + js_code + "(this);"
        self.mainFrame().evaluateJavaScript(
            self._addEventListener)  # This time it is here, because I dont want to have the initial addings

        real_clickable = None
        if element_to_click.id != None and element_to_click.id != "":
            real_clickable = self.search_element_with_id(element_to_click.id)
        if element_to_click.html_class != None and real_clickable == None:
            real_clickable = self.search_element_with_class(element_to_click.html_class, element_to_click.dom_address)
        if real_clickable == None:
            real_clickable = self.search_element_without_id_and_class(element_to_click.dom_address)

        if real_clickable is None:
            logging.debug("Target Clickable not found")
            return EventResult.TargetElementNotFound, None

        self._capturing_ajax = True
        real_clickable.evaluateJavaScript(js_code)
        self._wait(0.5)
        self._capturing_ajax = False
        links, clickables = extract_links(self.mainFrame(), webpage.url)
        forms = extract_forms(self.mainFrame())
        elements_with_event_properties = property_helper(self.mainFrame())

        html = self.mainFrame().toHtml()
        f = open("test.txt", "w")
        f.write(html)
        f.close()

        if is_key_event:
            generator = KeyClickable(element_to_click, random_char)
        else:
            generator = element_to_click
        if self._url_changed and self._new_url.toString() != webpage.url:
            delta_page = DeltaPage(-1, self._new_url.toString(), html=None, generator=generator, parent_id=webpage.id,
                                   cookiesjar=webpage.cookiejar)
            self._analyzing_finished = True
            self.mainFrame().setHtml(None)
            return EventResult.URLChanged, delta_page
        else:
            delta_page = DeltaPage(-1, webpage.url, html, generator=generator, parent_id=webpage.id,
                                   cookiesjar=webpage.cookiejar)
            delta_page.clickables = self._new_clickables  # Set by add eventlistener code
            delta_page.clickables.extend(clickables)
            delta_page.clickables.extend(elements_with_event_properties)
            delta_page.links = links
            delta_page.forms = forms
            delta_page.ajax_requests = self.ajax_requests
            self._analyzing_finished = True
            self.mainFrame().setHtml(None)
            return EventResult.Ok, delta_page

    def javaScriptAlert(self, frame, msg):
        logging.debug("Alert occurs in frame: {} with message: {}".format(frame.baseUrl().toString(), msg))

    def javaScriptConfirm(self, frame, msg):
        logging.debug("Confirm occurs in frame: {} with message: {}".format(frame.baseUrl().toString(), msg))
        return True

    def loadFinishedHandler(self, result):
        if not self._analyzing_finished:  # Just to ignoring setting of non page....
            self._loading_complete = True

    def jsWinObjClearedHandler(self):  # Adding here the js-scripts corresponding to the phases
        if not self._analyzing_finished:
            self.mainFrame().evaluateJavaScript(self._lib_js)
            self.mainFrame().evaluateJavaScript(self._md5)
            self.mainFrame().addToJavaScriptWindowObject("jswrapper", self._js_bridge)
            if self.xhr_options == XHRBehavior.ObserveXHR:
                self.mainFrame().evaluateJavaScript(self._xhr_observe_js)
            if self.xhr_options == XHRBehavior.InterceptXHR:
                self.mainFrame().evaluateJavaScript(self._xhr_interception_js)

    def createWindow(self, win_type):
        logging.debug("Creating new window...{}".format(win_type))

    def capturing_requests(self, request):
        if self._capturing_ajax:
            logging.debug("Ajax to: {} captured...".format(request['url']))
            ajax_request = AjaxRequest(request['method'], request['url'], self.element_to_click, request['parameters'])
            if ajax_request not in self.ajax_requests:
                self.ajax_requests.append(ajax_request)

    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        #logging.debug("Console(EventExecutor): " + message + " at: " + str(lineNumber))
        pass

    def capture_timeout_call(self, timingevent):
        try:
            # logging.debug(timingevent)
            if timingevent['time'] != "undefined":
                time = timingevent['time']  # millisecond
                event_type = timingevent['type']
                event_id = timingevent['function_id']
                if self.timeming_events is not None:
                    if time > self.timeming_events[0]:
                        self.timeming_events = (time, event_type, event_id)
                else:
                    self.timeming_events = (time, event_type, event_id)
        except KeyError as err:
            logging.debug("Key error occurred in Events " + str(err))


    def _url_changes(self, url):
        self._url_changed = True
        self._new_url = url


class EventResult(Enum):
    Ok = 0
    PreviousClickNotFound = 1
    TargetElementNotFound = 2
    ErrorWhileInitialLoading = 3
    URLChanged = 4
    UnsupportedTag = 5

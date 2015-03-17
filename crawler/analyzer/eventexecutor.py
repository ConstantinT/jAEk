'''
Created on 23.02.2015

@author: constantin
'''
import logging
import random
import string
from enum import Enum
from analyzer.helper.formhelper import FormHelper
from analyzer.helper.linkhelper import LinkHelper
from models.ajaxrequest import AjaxRequest
from models.clickable import Clickable
from models.deltapage import DeltaPage
from models.keyclickable import KeyClickable
from analyzer.abstractinteractioncore import AbstractInteractionCore
from models.utils import CrawlSpeed
from PyQt5.Qt import QUrl


class EventExecutor(AbstractInteractionCore):
    def __init__(self, parent, proxy="", port=0, crawl_speed=CrawlSpeed.Medium, network_access_manager=None):
        super(EventExecutor, self).__init__(parent, proxy, port, crawl_speed, network_access_manager)
        self._url_changed = False  # Inidicates if a event changes a location => treat it as link!
        self._new_url = None
        self.timeming_events = None
        self.supported_events = ['click', 'focus', 'blur', 'dblclick', 'input', 'change',
                                 'mousedown', 'mousemove', 'mouseout', 'mouseover', 'mouseup',
                                 'resize', 'scroll', 'select', 'submit', 'load', 'unload', 'mouseleave', 'keyup',
                                 'keydown', 'keypress']
        self.key_events = ['keyup', 'keydown', 'keypress']

        self.seen_timeouts = {}
        self.mainFrame().urlChanged.connect(self._url_changes)

        self._link_helper = LinkHelper()
        self._form_helper = FormHelper()


    def execute(self, webpage, timeout=5, element_to_click=None, xhr_options=None, pre_clicks=None):
        logging.debug(
            "EventExecutor test started on {}...".format(webpage.url) + " with " + element_to_click.toString())
        self._analyzing_finished = False
        self._loading_complete = False
        self.xhr_options = xhr_options
        self.element_to_click = None
        self.ajax_requests = []
        self._new_url = None
        self.timeming_events = None
        self._preclicking_ready = False
        self._new_clickables = []
        self.element_to_click = element_to_click
        self.mainFrame().setHtml(webpage.html, QUrl(webpage.url))
        target_tag = element_to_click.dom_adress.split("/")
        target_tag = target_tag[-1]
        if target_tag in ['video']:
            return Event_Result.Unsupported_Tag, None

        t = 0.0
        while (not self._loading_complete and t < timeout ):  # Waiting for finish processing
            self._wait(0.1)
            t += 0.1
        if not self._loading_complete:
            logging.debug("Timeout occurs while initial page loading...")
            return Event_Result.Error_While_Initial_Loading, None
        # Prepare Page for clicking...
        for click in pre_clicks:
            pre_click_elem = None
            logging.debug("Click on: " + click.toString())
            if click.id != None and click.id != "":
                pre_click_elem = self.search_element_with_id(click.id)
            if click.html_class != None and pre_click_elem == None:
                pre_click_elem = self.search_element_with_class(click.html_class, click.dom_adress)
            if pre_click_elem == None:
                pre_click_elem = self.search_element_without_id_and_class(click.dom_adress)

            if pre_click_elem is None:
                logging.debug("Preclicking element not found")
                return Event_Result.Previous_Click_Not_Found, None

            js_code = click.event
            if js_code[0:2] == "on":
                js_code = js_code[2:]  # if event beginns with on, escape it
            js_code = "Simulate." + js_code + "(this);"
            pre_click_elem.evaluateJavaScript(js_code)  # Waiting for finish processing
            self._wait(self.wait_for_event)

            # Now execute the target event
        self._preclicking_ready = True
        self._url_changed = False
        self.mainFrame().urlChanged.connect(self._url_changes)
        js_code = element_to_click.event
        if js_code[0:2] == "on":
            js_code = js_code[2:]  # if event beginns with on, escape it
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
            real_clickable = self.search_element_with_class(element_to_click.html_class, element_to_click.dom_adress)
        if real_clickable == None:
            real_clickable = self.search_element_without_id_and_class(element_to_click.dom_adress)

        if real_clickable is None:
            logging.debug("Target Clickable not found")
            return Event_Result.Target_Element_Not_Found, None

        real_clickable.evaluateJavaScript(js_code)
        self._wait(0.5)

        links, clickables = self._link_helper.extract_links(self.mainFrame(), webpage.url, webpage.current_depth)
        forms = self._form_helper.extract_forms(self.mainFrame())
        self.mainFrame().evaluateJavaScript(self._property_obs_js)
        self._wait(0.5)

        html = self.mainFrame().toHtml()

        if is_key_event:
            generator = KeyClickable(element_to_click, random_char)
        else:
            generator = element_to_click
        if self._url_changed and self._new_url.toString() != webpage.url:
            delta_page = DeltaPage(-1, self._new_url.toString(), html=None, generator=generator, parent_id=webpage.id,
                                   cookiesjar=webpage.cookiejar)
            self._analyzing_finished = True
            self.mainFrame().setHtml(None)
            return Event_Result.URL_Changed, delta_page
        else:
            delta_page = DeltaPage(-1, webpage.url, html, generator=generator, parent_id=webpage.id,
                                   cookiesjar=webpage.cookiejar)
            delta_page.clickables = self._new_clickables  # Set by add eventlistener code
            delta_page.clickables.extend(clickables)
            delta_page.links = links
            delta_page.forms = forms
            delta_page.ajax_requests = self.ajax_requests
            self._analyzing_finished = True
            self.mainFrame().setHtml(None)
            return Event_Result.Ok, delta_page

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
            self.mainFrame().addToJavaScriptWindowObject("jswrapper", self._jsbridge)
            if self.xhr_options == XHR_Behavior.observe_xhr:
                self.mainFrame().evaluateJavaScript(self._xhr_observe_js)
            if self.xhr_options == XHR_Behavior.intercept_xhr:
                self.mainFrame().evaluateJavaScript(self._xhr_interception_js)

    def createWindow(self, win_type):
        logging.debug("Creating new window...{}".format(win_type))


    def capturing_requests(self, request):
        if self._preclicking_ready:
            logging.debug("Ajax to: {} captured...".format(request['url']))
            ajax_request = AjaxRequest(request['method'], request['url'], self.element_to_click, request['parameter'])
            self.ajax_requests.append(ajax_request)

    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(EventExecutor): " + message + " at: " + str(lineNumber))
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
            logging.debug("Key error occured in Events " + str(err))


    def _url_changes(self, url):
        self._url_changed = True
        self._new_url = url

    def add_eventlistener_to_element(self, msg):
        try:
            # logging.debug(msg)
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
                self._new_clickables.append(tmp)
        except KeyError as err:
            # logging.debug(err)
            pass


class Event_Result(Enum):
    Ok = 0
    Previous_Click_Not_Found = 1
    Target_Element_Not_Found = 2
    Error_While_Initial_Loading = 3
    URL_Changed = 4
    Unsupported_Tag = 5


class XHR_Behavior(Enum):
    ignore_xhr = 0
    observe_xhr = 1
    intercept_xhr = 2 
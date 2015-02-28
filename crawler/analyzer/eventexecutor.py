'''
Created on 23.02.2015

@author: constantin
'''
import logging
import random
import string
from enum import Enum
from models.ajaxrequest import AjaxRequest
from models.clickable import Clickable
from models.deltapage import DeltaPage
from models.keyclickable import KeyClickable
from analyzer.abstractanalyzer import AbstractAnalyzer
from models.utils import CrawlSpeed
from PyQt5.Qt import QUrl



class EventExecutor(AbstractAnalyzer):
    
    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium):
        super(EventExecutor, self).__init__(parent, proxy, port, crawl_speed)
        self._url_changed = False #Inidicates if a event changes a location => treat it as link!
        self._new_url = None
        self.timeming_events = None
        self.supported_events = [ 'click', 'focus', 'blur', 'dblclick', 'input', 'change',
            'mousedown', 'mousemove', 'mouseout', 'mouseover', 'mouseup',
            'resize', 'scroll', 'select', 'submit' ,'load', 'unload', 'mouseleave', 'keyup', 'keydown', 'keypress' ]
        self.key_events = ['keyup', 'keydown', 'keypress']
        
        self.seen_timeouts = {}
        self.mainFrame().urlChanged.connect(self._url_changes)
        
        

        
        
    def execute(self, webpage, timeout=5, element_to_click = None, xhr_options = None, pre_clicks = None):
        logging.debug("EventExecutor test started on {}...".format(webpage.url) + " with " + element_to_click.toString())
        self._analyzing_finished = False
        self._loading_complete = False
        self.xhr_options = xhr_options
        self.element_to_click = None
        self.new_clickables = []
        self.ajax_requests = []
        self._new_url = None
        self.timeming_events = None
        self._preclicking_ready = False
        self.element_to_click = element_to_click
        self.mainFrame().setHtml(webpage.html, QUrl(webpage.url))
        target_tag = element_to_click.dom_adress.split("/")
        target_tag = target_tag[-1]
        if target_tag in ['video']:
            return Event_Result.Unsupported_Tag, None
        
        t = 0.0
        while(not self._loading_complete and t < timeout ): # Waiting for finish processing
            self._wait(0.1) 
            t += 0.1
        if not self._loading_complete:
            logging.debug("Timeout occurs while initial page loading...")  
            return Event_Result.Error_While_Initial_Loading, None
        #Prepare Page for clicking...            
        for click in pre_clicks:
            pre_click_elem = None
            logging.debug("Click on: " + click.toString())
            if click.id != None and click.id != "":
                pre_click_elem = self.search_element_with_id(click.id)
            if click.html_class != None and pre_click_elem == None:
                pre_click_elem =  self.search_element_with_class(click.html_class, click.dom_adress)
            if pre_click_elem == None:
                pre_click_elem = self.search_element_without_id_and_class(click.dom_adress)
            
            if pre_click_elem is None:
                logging.debug("Preclicking element not found")
                return Event_Result.Previous_Click_Not_Found, None
            
            js_code = click.event
            if js_code[0:2] == "on":
                js_code = js_code[2:]  # if event beginns with on, escape it
            js_code = "Simulate." + js_code + "(this);"
            pre_click_elem.evaluateJavaScript(js_code) # Waiting for finish processing
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
            js_code = "Simulate."+js_code+"(this, '" + random_char +"');"
        else: 
            js_code = "Simulate." + js_code + "(this);"
        self.mainFrame().evaluateJavaScript(self._addEventListener) # This time it is here, because I dont want to have the initial addings
        
        real_clickable = None
        if element_to_click.id != None and element_to_click.id != "":
            real_clickable = self.search_element_with_id(element_to_click.id)
        if element_to_click.html_class != None and real_clickable == None:
            real_clickable =  self.search_element_with_class(element_to_click.html_class, element_to_click.dom_adress)
        if real_clickable == None:
            real_clickable = self.search_element_without_id_and_class(element_to_click.dom_adress)
        
        if real_clickable is None:
            logging.debug("Target Clickable not found")
            return Event_Result.Target_Element_Not_Founs, None
        
        real_clickable.evaluateJavaScript(js_code)
        self._wait(0.5)

        
        html = self.mainFrame().toHtml()
        if is_key_event:
            generator = KeyClickable(element_to_click, random_char)
        else:
            generator = element_to_click
        if self._url_changed and self._new_url.toString() != webpage.url:
            delta_page = DeltaPage(-1, self._new_url.toString(), html=None, generator=generator, parent_id=webpage.id, cookiesjar=webpage.cookiejar)
            self._analyzing_finished = True
            self.mainFrame().setHtml(None)
            return Event_Result.URL_Changed, delta_page
        else:
            delta_page = DeltaPage(-1, webpage.url, html, generator=generator, parent_id=webpage.id, cookiesjar=webpage.cookiejar)
            delta_page.clickables = self.new_clickables # Set by add eventlistener code
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
        if not self._analyzing_finished: # Just to ignoring setting of non page....                
            self._loading_complete = True
            
    def jsWinObjClearedHandler(self): #Adding here the js-scripts corresponding to the phases
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
    
    def add_eventlistener_to_element(self, msg):
        if self._preclicking_ready:
            try:
                if msg['id'] != None and msg['id'] != "":
                    id = msg['id']
                else: 
                    id = None
                domadress = msg['addr']
                event = msg['event']
                if event == "": 
                    event = None
                tag = msg['tag']
                
                if msg['class'] != None and msg['class'] != "":
                    html_class = msg['class']
                else:
                    html_class = None
                function_id = msg['function_id']
                tmp = Clickable(event, tag, domadress, id, html_class, function_id=function_id)
                self.new_clickables.append(tmp)
            except KeyError:
                pass
          
    def capturing_requests(self, request):
        if self._preclicking_ready:
            logging.debug("Ajax to: {} captured...".format(request['url']))
            ajax_request = AjaxRequest(request['method'], request['url'], self.element_to_click, request['parameter'])
            self.ajax_requests.append(ajax_request)
        
              
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console(EventExecutor): " + message + " at: " + str(lineNumber))
        pass
    
    def search_element_with_id(self, element_id):
        elem = self.mainFrame().findAllElements("#" + str(element_id))
        if len(elem) > 0:
            return elem[0] # maybe check if there is more than one element
        else:
            return None

    def search_element_with_class(self, cls, dom_adress):
        css_cls_definition = ""
        classes = cls.split(" ")
        for cls in classes: #converting class names in css-compatible classnames
            cls = "." + cls 
            css_cls_definition = css_cls_definition + cls + " "
        elems = self.mainFrame().findAllElements(css_cls_definition)
        for elem in elems:
            if dom_adress == elem.evaluateJavaScript("getXPath(this)"):
                return elem
    
    def capture_timeout_call(self, timingevent):
        try:
            #logging.debug(timingevent)
            if timingevent['time'] != "undefined":
                time = timingevent['time'] # millisecond
                event_type = timingevent['type']
                event_id = timingevent['function_id']
                if self.timeming_events is not None:
                    if time > self.timeming_events[0]:
                        self.timeming_events = (time,event_type,event_id)
                else:
                    self.timeming_events = (time,event_type, event_id)
        except KeyError as err:
            logging.debug("Key error occured in Events " + str(err))         
    
    def search_element_without_id_and_class(self, dom_adress):
        check_dom_adress = dom_adress
        dom_address = dom_adress.split("/")
        current_element_in_dom = self.mainFrame().documentElement() #Is HTML-Element
        while len(dom_address) > 0 and current_element_in_dom is not None:
            target_tag_name = dom_address.pop(0) # Get and remove the first element
            target_tag_name = target_tag_name.upper()   
            if len(target_tag_name) == 0:
                continue
            elif target_tag_name == "HTML": #or target_tag_name == "body":
                continue
            else: 
                tmp = target_tag_name.find("[")
                if tmp > 0: # target_tag_name looks like tagname[index]
                    target_tag_name = target_tag_name.split("[")
                    index = int(target_tag_name[1].split("]")[0]) # get index out of target_tag_name
                    target_tag_name = target_tag_name[0] # target_tag_name name
                    last_child = current_element_in_dom.lastChild()
                    tmp_element = current_element_in_dom.findFirst(target_tag_name) # takes first child
                    if tmp_element.tagName() == target_tag_name: # if firstchild is from type of target_tag_name, subtrakt 1 from index
                        index -= 1;
                    counter = 9999 #Sometimes comparing with last child went wrong, therefore we have an backup counter
                    while index > 0 and tmp_element != last_child: # take next sibbling until index is 0, if target_tag_name is equal subtrakt one
                        tmp_element = tmp_element.nextSibling() #
                        if tmp_element.tagName() == target_tag_name:
                            index -= 1
                        counter -= 1
                        if counter == 0: #If counter 0 then break, we wont find it anymore
                            current_element_in_dom = None
                            break
                    if index == 0 and tmp_element.tagName() == target_tag_name: 
                        current_element_in_dom = tmp_element
                    else: #We miss the element
                        current_element_in_dom = None
                else: #target_tag_name is the only of his type, or the first...is die hell
                    tmp_element = current_element_in_dom.firstChild()
                    last_child = current_element_in_dom.lastChild()
                    counter = 9999
                    while tmp_element.tagName() != target_tag_name and tmp_element != last_child and counter > 0:
                        #logging.debug(tmp_element.tagName())
                        counter -= 1
                        if tmp_element.tagName() == target_tag_name:
                            current_element_in_dom = tmp_element
                            break
                        else:
                            tmp_element = tmp_element.nextSibling()
                    if tmp_element.tagName() != target_tag_name or counter == 0:
                        current_element_in_dom = None
                    else:
                        current_element_in_dom = tmp_element
                    
        tmp_element = None
        last_child = None
        dom_address = None
        
        if current_element_in_dom == None:
            #logging.debug("Current Elem is None")
            return None
        if current_element_in_dom.evaluateJavaScript("getXPath(this)") != check_dom_adress:
            logging.debug("Element not found: " + str(current_element_in_dom.evaluateJavaScript("getXPath(this)")) + " : " + str(check_dom_adress))
            return None 
        else:
            #logging.debug("Element: " + str(current_element_in_dom.evaluateJavaScript("getXPath(this)")) + " found...")
            return current_element_in_dom
        
    def _url_changes(self, url):
        self._url_changed = True
        self._new_url = url
       

        
class Event_Result(Enum):
    Ok = 0
    Previous_Click_Not_Found = 1
    Target_Element_Not_Founs = 2
    Error_While_Initial_Loading = 3
    URL_Changed = 4
    Unsupported_Tag = 5
    
class XHR_Behavior(Enum):
    ignore_xhr = 0
    observe_xhr = 1
    intercept_xhr = 2 
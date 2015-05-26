import logging

from PyQt5.Qt import QUrl

from core.interactioncore import InteractionCore
from core.eventexecutor import EventResult
from analyzer.helper.formhelper import extract_forms
from analyzer.helper.linkhelper import extract_links
from models.clickable import Clickable
from models.utils import CrawlSpeed, purge_dublicates

__author__ = 'constantin'


class FormHandler(InteractionCore):


    def __init__(self, parent, proxy = "", port = 0, crawl_speed = CrawlSpeed.Medium, network_access_manager = None):
        super(FormHandler, self).__init__(parent, proxy, port, crawl_speed, network_access_manager)
        #self.mainFrame().urlChanged.connect(self._url_changes)

    def submit_form(self, form, webpage, data=dict(), timeout=5):
        logging.debug("FormHandler on Page: {} started...".format(webpage.url))
        self._loading_complete = False
        self._analyzing_finished = False
        try:
            url = webpage.url.toString()
        except AttributeError:
            url = webpage.url
        self.mainFrame().setHtml(webpage.html, QUrl(url))
        self._new_clickables = []

        t = 0.0
        while not self._loading_complete and t < timeout: # Waiting for finish processing
            self._wait(0.1)
            t += 0.1
        if not self._loading_complete:
            logging.debug("Timeout occurs while initial page loading...")
            return EventResult.ErrorWhileInitialLoading, None

        target_form = None
        p_forms = self.mainFrame().findAllElements("form")
        for tmp_form in p_forms:
            path = tmp_form.evaluateJavaScript("getXPath(this)")
            if path == form.dom_address:
                target_form = tmp_form
                break
        if target_form is None:
            return EventResult.TargetElementNotFound, None

        for elem in form.parameter: #Iterate through abstract form representation
            if elem.name in data: #Check if we have the data we must set
                elem_found = False # Indicates if we found the element in the html
                value_to_set = data[elem.name]
                for tmp in target_form.findAll(elem.tag): #Locking in the target form, if we found the element we have to set
                    if tmp.attribute("name") == elem.name: # Has the current element in the html the same name as our data
                        tmp.evaluateJavaScript("this.value = '" + value_to_set + "';")
                        elem_found = True
                        break
                if not elem_found:
                    return EventResult.TargetElementNotFound, None
        # Now we should have set all known parameters, next click the submit button
        q_submit_button = None
        if "submit" in form.toString():
            inputs = target_form.findAll("input") + target_form.findAll("button")
            for el in inputs:
                if el.attribute("type") == "submit":
                    q_submit_button = el
                    break
            #q_submit_button.evaluateJavaScript("this.id='oxyfrymbel'")
        else:
            logging.debug(form.toString())

        if q_submit_button is None:
            inputs = target_form.findAll("button")
            q_submit_button = None
            if len(inputs) > 1:
                logging.debug("Cannot locate login button...")
                return EventResult.TargetElementNotFound, None
            elif len(inputs) == 1:
                q_submit_button = inputs[0]

        method = target_form.attribute("onsubmit")
        if method is not None and method != "":
            js_code_snippets = method.split(";")
            for snippet in js_code_snippets:
                if "return" in snippet or snippet == "":
                    logging.debug("Ignoring snippet: {}".format(snippet))
                    continue
                logging.debug("Eval: {}".format(snippet+";"))
                self.mainFrame().evaluateJavaScript(snippet+";")
                self._wait(3)
            self.mainFrame().evaluateJavaScript(self._addEventListener)
            self._wait(3)
        else:
            #TODO: Implement way for sending forms without onsubmit-method
            # check between: target_form.evaluateJavaScript("Simulate or document.?form?.submit())
            # or submit_button click
            if q_submit_button is not None:
                logging.debug("Click on submit button...")
                q_submit_button.evaluateJavaScript("Simulate.click(this);")
                self._wait(3)
            else:
                logging.debug("Trigger submit event on form...")
                target_form.evaluateJavaScript("Simulate.submit(this);")
                self._wait(3)

        links, clickables = extract_links(self.mainFrame(), url)
        forms = extract_forms(self.mainFrame())
        html = self.mainFrame().toHtml()
        #f = open("html.txt", "w")
        #f.write(html)
        #f.close()
        self.mainFrame().setHtml(None)
        self._new_clickables.extend(clickables)
        self._new_clickables = purge_dublicates(self._new_clickables)
        return EventResult.Ok, html, self._new_clickables, forms, links, []

    def jsWinObjClearedHandler(self): #Adding here the js-scripts corresponding to the phases
        if not self._analyzing_finished:
            self.mainFrame().evaluateJavaScript(self._lib_js)
            self.mainFrame().evaluateJavaScript(self._md5)
            self.mainFrame().addToJavaScriptWindowObject("jswrapper", self._js_bridge)

    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        #logging.debug("Console(FormHandler): " + message + " at: " + str(lineNumber))
        pass

    def javaScriptAlert(self, frame, msg):
        logging.debug("Alert occurs in frame: {} with message: {}".format(frame.baseUrl().toString(), msg))

    def javaScriptConfirm(self, frame, msg):
        logging.debug("Confirm occurs in frame: {} with message: {}".format(frame.baseUrl().toString(), msg))
        return True

    def loadFinishedHandler(self, result):
        if not self._analyzing_finished: # Just to ignoring setting of non page....
            self._loading_complete = True

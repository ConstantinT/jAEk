'''
Created on 23.02.2015

@author: constantin
'''
from filter.abstractfilter import AbstractFilter
import logging
from PyQt5.Qt import QUrl
from models.utils import CrawlSpeed
from models.form import HtmlForm, FormInput


class FormExtractor(AbstractFilter):
    """
    Class that is able to extract forms with their input-elements. Now supported:
    <input type="text, button, radio">, <button>, <select>
    Todo: <textarea>, <datalist> together with <input>, <keygen>, (<output>
    """
    
    def __init__(self, parent, proxy, port, crawl_speed = CrawlSpeed.Medium):
        super(FormExtractor, self).__init__(parent, proxy, port, crawl_speed)
        self._process_finished = False
            
    def extract_forms(self, html, requested_url, timeout = 60):   
        logging.debug("Start extracting forms on {}...".format(requested_url)) 
        t = 0
        self.forms = []
        self._process_finished = False
        self._requested_url = requested_url
        self.mainFrame().setHtml(html, QUrl(requested_url))
        
        while(not self._process_finished and t < timeout):
            t += self.wait_for_processing
            self._wait(self.wait_for_processing)
        
        if not self._process_finished:
            logging.debug("timeout occurs")
        
        self.mainFrame().setHtml(None)
        return self.forms
         
    
    def loadFinishedHandler(self, result):
        if not self._process_finished:
            self.mainFrame().evaluateJavaScript(self._js_lib)
            forms = self.mainFrame().findAllElements("form")
            for form in forms:
                action = form.attribute("action")
                method = form.attribute("method")
                form_params = self._extracting_information(form)
                self.forms.append(HtmlForm(form_params, action, method))
        self._process_finished = True  
    
    def _extracting_information(self, elem):
        result = []
        inputs = elem.findAll("input")
        radio_buttons = {} # key = name, value = array mit values

        for input_el in inputs:
            tagname = input_el.tagName()
            if input_el.hasAttribute("type"):
                input_type = input_el.attribute("type")
                if input_type != "radio": #no radio button
                    if input_el.hasAttribute("name"):
                        name = input_el.attribute("name")
                    else:
                        continue
                    if input_el.hasAttribute("value"):
                        value = [input_el.attribute("value")]
                    else:
                        value = None
                    result.append(FormInput(tagname, name, input_type, value)) 
                else: # input is radiobutton
                    name = input_el.attribute("name")
                    if name in radio_buttons: # Radio-Button name exists
                        radio_buttons[name].append(input_el.attribute("value"))
                    else: #Radiobutton name exists not
                        radio_buttons[name] = []
                        radio_buttons[name].append(input_el.attribute("value"))
        for key in radio_buttons:
            result.append(FormInput(tagname, key, input_type, radio_buttons[key]))
        buttons = elem.findAll("button")
        for button in buttons:
            tagname = button.tagName()
            if button.hasAttribute("type"):
                button_type = button.attribute("type")
            else:
                button_type = None
                logging.debug("Something mysterious must have happened...")
            if button.hasAttribute("name"):
                name = button.attribute("name")
            else:
                continue
            if button.hasAttribute("value"):
                value = [button.attribute("value")]
            else:
                value = None
                    #logging.debug(tagname + " " + name + " " + input_type + " " + value)
            result.append(FormInput(tagname, name, button_type, value)) 
        
        selects = elem.findAll("select")#<select> <option>
        for select in selects:  
            select_name = select.attribute("name")
            options = select.findAll("option")
            values = []
            for option in options:
                values.append(option.attribute("value"))
            f_input = FormInput(select.tagName(), select_name, None, values)
            result.append(f_input) 
        return result
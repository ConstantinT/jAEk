'''
Copyright (C) 2015 Constantin Tschuertz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import logging
from models.form import HtmlForm, FormInput

def extract_forms(frame):
    result = []
    forms = frame.findAllElements("form")
    for form in forms:
        action = form.attribute("action")
        method = form.attribute("method") if form.attribute("method") == "post" else "get"
        dom_address = form.evaluateJavaScript("getXPath(this)")
        form_params = _extracting_information(form)
        result.append(HtmlForm(form_params, action, method, dom_address))
    return result

def _extracting_information(elem):
    result = []
    inputs = elem.findAll("input")
    radio_buttons = {} # key = name, value = array mit values

    for input_el in inputs:
        tag_name = input_el.tagName()
        if input_el.hasAttribute("type"):
            input_type = input_el.attribute("type")
            if input_type != "radio": #no radio button
                if input_el.hasAttribute("name") or input_type == "submit":
                    name = input_el.attribute("name")
                else:
                    continue #A input-element without name has no impact, why waste memory? Ok jaek you are alright, if it is a submit element we need it...
                if input_el.hasAttribute("value"):
                    value = [input_el.attribute("value")]
                else:
                    value = [None]
                result.append(FormInput(tag_name, name, input_type, value))
            else: # input is radiobutton
                name = input_el.attribute("name")
                if name in radio_buttons: # Radio-Button name exists
                    radio_buttons[name].append(input_el.attribute("value"))
                else: #Radiobutton name exists not
                    radio_buttons[name] = []
                    radio_buttons[name].append(input_el.attribute("value"))
        else:
            if input_el.hasAttribute("name"):
                name = input_el.attribute("name")
                tag_name = input_el.tagName()
                result.append(FormInput(tag_name, name, None, None))
    for key in radio_buttons:
        result.append(FormInput(tag_name, key, input_type, radio_buttons[key]))
    buttons = elem.findAll("button")
    for button in buttons:
        tag_name = button.tagName()
        if button.hasAttribute("type"):
            button_type = button.attribute("type")
        else:
            button_type = None
        if button.hasAttribute("name"):
            name = button.attribute("name")
        else:
            name = None
        if button.hasAttribute("value"):
            value = [button.attribute("value")]
        else:
            value = None
        result.append(FormInput(tag_name, name, button_type, value))

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
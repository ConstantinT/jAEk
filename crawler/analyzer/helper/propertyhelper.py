import logging
from models.clickable import Clickable

__author__ = 'constantin'


def property_helper(frame):
    all_elements = frame.findAllElements("*")
    result = []
    properties = ['onclick', "onmouseover", "onabort", "onblur", "onchange", "onblclick", "onerror", "onfocus", "onkeydown",
                  "onkeypress", "onkeyup", "onmousedown", "onmousemove", "onmouseout", "onmouseup"]
    for element in all_elements:
        element_id = None
        element_class = None
        if element.hasAttribute("id"):
            element_id = element.attribute("id")
        if element.hasAttribute("class"):
            element_class = element.attribute("class")
        element_dom_address = None
        for prop in properties:
            if element.hasAttribute(prop):
                if element_dom_address is None:
                    element_dom_address = element.evaluateJavaScript("getXPath(this)")
                result.append(Clickable(prop, element.tagName(), element_dom_address, element_id, element_class, function_id="None"))
    return result
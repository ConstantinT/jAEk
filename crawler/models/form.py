'''
Created on 23.02.2015

@author: constantin
'''
import hashlib


class HtmlForm():
    def __init__(self, parameters, action, method, dom_address=None):
        self.parameter = parameters  # Array of FormInput's
        self.parameter = sorted(self.parameter, key=lambda parameter: parameter.name)
        self.action = action
        self.method = method
        self.dom_address = dom_address

    @property
    def form_hash(self):
        return self.get_hash()

    def toString(self):
        msg = "[Form: Action: '" + self.action.abstract_url + "' Method:' " + self.method + " - Formhash: " + self.get_hash() + " \n"
        if self.dom_address is not None:
            msg += "Dom Address: " + self.dom_address + " \n"
        for elem in self.parameter:
            msg += "[Param: " + str(elem.tag) + " Name: " + str(elem.name) + " Inputtype: " + str(
                elem.input_type) + " Values: " + str(elem.values) + "] \n"
        return msg + "]"

    def hasSubmit(self):
        return self.submit != None

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.get_hash() == other.get_hash()

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_hash(self):
        s_to_hash = self.action.abstract_url + ";" + self.method + ";"
        for p in self.parameter:
            s_to_hash += p.name + ";" + p.tag + ";" + str(p.input_type) + ";"
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()


class FormInput():
    def __init__(self, tag, name, input_type="", values=None):
        self.tag = tag
        self.name = name
        self.values = values
        self.input_type = input_type

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.values is not None:
            for val in self.values:
                if other.values is None or not val in other.values:
                    return False
        return self.tag == other.tag and self.name == other.name and self.input_type == other.input_type

    def __ne__(self, other):
        return not self.__eq__(other)


class InputField():
    def __init__(self, input_type, html_id=None, html_class=None, value=None):
        self.input_type = input_type
        self.html_id = html_id
        self.html_class = html_class
        self.value = value  # Predifiend value, if available...

'''
Created on 23.02.2015

@author: constantin
'''
import hashlib
from models.asyncrequests import AsyncRequests


class AjaxRequest(AsyncRequests):
    '''
    Models an Ajax-Request issued by an event
    '''
    def __init__(self, method, url, trigger, parameters=None):
        super(AjaxRequest, self).__init__(method, url, parameters)
        self.trigger = trigger

    def toString(self):
        msg =  "[Ajax - Methode: " + self.method + " - Url: "+ self.url.toString() + " - Trigger: " + self.trigger.toString() + " \n"
        for param_pair in self.parameters:
            msg += " - Parameter pair: " + str(param_pair)
        return msg

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.method == other.method and self.url.complete_url == other.url.complete_url and self.trigger == other.trigger

    def __neg__(self):
        return not  self.__eq__()

    def get_hash(self):
        s_to_hash = self.url.abstract_url + "+" + self.method
        for k in [x[0] for x in self.parameters]:
            s_to_hash += "++" + k
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()
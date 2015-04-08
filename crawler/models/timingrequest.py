'''
Created on 23.02.2015

@author: constantin
'''
import hashlib
from models.asyncrequests import AsyncRequests


class TimingRequest(AsyncRequests):
    '''
    Models an Ajax-Request issued after timeout or intervall
    '''
    def __init__(self, method, url, time, event, parameters=None):
        super(TimingRequest, self).__init__(method, url, parameters)
        self.event = event #Timout or Intervall
        self.time = time

    def toString(self):
        return "[Timeming - Methode: " + str(self.method) + " - Url: "+ str(self.url.toString()) + " - Trigger: " + str(self.event) +" - FunctionID: " + str(self.function_id) + "]"

    def get_hash(self):
        s_to_hash = self.url.abstract_url + "+" + self.method
        s_to_hash += ";" + self.event + ";"
        for k in self.parameters:
            s_to_hash += "++" + k
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()
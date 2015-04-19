'''
Created on 23.02.2015

@author: constantin
'''

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
        return "[Timing - Method: " + str(self.method) + " - Url: "+ str(self.url.toString()) + " - Trigger: " + str(self.event) + "]"

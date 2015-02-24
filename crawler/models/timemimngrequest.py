'''
Created on 23.02.2015

@author: constantin
'''

class TimemingRequest():
    '''
    Models an Ajax-Request issued after timeout or intervall
    '''
    def __init__(self, method, url, time , trigger ,function_id = None, paramters = None):
        self.method = method
        self.url = url
        self.event = trigger #Timout or Intervall
        self.function_id = function_id #ID of the function that is called from the event
        self.time = time
        self.parameters = paramters
    def toString(self):
        return "[Timeming - Methode: " + str(self.method) + " - Url: "+ str(self.url) + " - Trigger: " + str(self.event) +" - FunctionID: " + str(self.function_id) + "]"
        
'''
Created on 23.02.2015

@author: constantin
'''

class AjaxRequest():
    '''
    Models an Ajax-Request
    '''
    def __init__(self, method, url, trigger, parameter = None):
        self.method = method
        self.url = url
        self.trigger = trigger
        self.parameter = parameter
    
    def toString(self):
        msg =  "[Ajax - Methode: " + self.method + " - Url: "+ self.url + " - Trigger: " + self.trigger.toString() + " \n"
        for param_pair in self.parameter:
            msg += " - Parameter pair: " + str(param_pair)
        return msg
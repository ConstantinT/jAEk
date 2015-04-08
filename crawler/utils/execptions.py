


class LoginFormNotFound(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
    
class PageNotFound(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
    
class LoginFailed(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
     
class ElementNotFound(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
    
class DomainHandlerNotSet(Exception):
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)  
    
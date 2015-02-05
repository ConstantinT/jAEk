


class LoginFormNotFoundException(Exception):  
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
    
class PageNotFoundException(Exception):  
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
    
class LoginErrorException(Exception):  
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
     
class ElementNotFoundException(Exception):  
    def __init__(self, value):
        self.value = value     
    def __str__(self):
        return repr(self.value)
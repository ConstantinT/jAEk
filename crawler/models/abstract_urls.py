__author__ = 'constantin'


class AbstractUrl():

    def __init__(self, path, paramters = [], url_hash = None):
        self.path = path
        self.parameters = paramters
        self.url_hash = url_hash

    def toString(self):
        msg = "[Url: {} \n".format(self.path)
        for param in self.parameters:
            msg += "{} - {} \n".format(param[0], param[1])
        msg += "Hash: {}]".format(self.url_hash)
        return msg
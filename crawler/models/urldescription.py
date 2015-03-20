from enum import Enum
import hashlib

__author__ = 'constantin'


class UrlDescription():

    def __init__(self, path, paramters = {}, hash = None):
        self.path = path
        self.parameters = paramters # List of dict: parametername, parametertype, origin, generating <= change of the param creates a new page
        self.hash = hash

    def toString(self):
        msg = "[Url: {} \n".format(self.path)
        for param in self.parameters:
            msg += "{} - {} - {} - {} \n".format(param, ParameterType(self.parameters[param]['parameter_type']), ParameterOrigin(self.parameters[param]['origin']), self.parameters[param]['generating'])
        msg += "Hash: {}]".format(self.url_hash)
        return msg

class ParameterOrigin(Enum):
    ServerGenerated = 0
    ClientGenerated = 1

class ParameterType(Enum):
    """
    This describes the type of the parameter:
        - Digit: Single digit, exp: 0,1,2, ...
        - Float: Float value, exp: 1.5, 99,32, 3,1415...
        - Char; Single digit, float or character, exp: a, B, X, 5, ...
        - Integer: Normal Integer > 9, exp, 23, 39, 42, ...
        - String: String contains only Characters, exp: Turing, Captain Jack
        - Alpha-Numerical: Contains the rest, exp: diofjiodjr23jreß9324jr3j0ew9rj 0r9 j3029j

    """
    Digit = 0
    Float = 1
    Char = 2
    Integer = 3
    String = 4
    AlphaNumerical = 5
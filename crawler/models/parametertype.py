from enum import Enum

__author__ = 'constantin'

class ParameterType(Enum):
    """
    This describes the type of the parameters:
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
    NoParameter = 6
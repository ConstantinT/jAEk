from enum import Enum

__author__ = 'constantin'


class XHRBehavior(Enum):
    IgnoreXHR = 0
    ObserveXHR = 1
    InterceptXHR = 2
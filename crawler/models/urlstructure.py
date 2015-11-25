# -*- coding: latin-1 -*-"
'''
Copyright (C) 2015 Constantin Tschürtz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from enum import Enum
import hashlib
from models.parametertype import ParameterType

__author__ = 'constantin'


class UrlStructure():

    def __init__(self, path, paramters = {}, url_hash = None):
        self.path = path
        self.parameters = paramters # List of dict: parametername, parametertype, origin, generating <= change of the param creates a new page
        self.url_hash = url_hash

    def get_parameter_type(self, parameter_name):
        if parameter_name not in self.parameters:
            raise KeyError("{} not found".format(parameter_name))
        return ParameterType(self.parameters[parameter_name]['parameter_type'])

    def get_parameter_origin(self, parameter_name):
        if parameter_name not in self.parameters:
            raise KeyError("{} not found".format(parameter_name))
        return ParameterType(self.parameters[parameter_name]['origin'])

    def toString(self):
        msg = "[Url: {} \n".format(self.path)
        for param in self.parameters:
            msg += "{} - {} - {} - {} \n".format(param, ParameterType(self.parameters[param]['parameter_type']), ParameterOrigin(self.parameters[param]['origin']), self.parameters[param]['generating'])
        msg += "Hash: {}]".format(self.url_hash)
        return msg

class ParameterOrigin(Enum):
    ServerGenerated = 0
    ClientGenerated = 1


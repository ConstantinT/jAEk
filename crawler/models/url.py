'''
Copyright (C) 2015 Constantin Tschuertz

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

import hashlib
from urllib.parse import urlparse


class Url():
    def __init__(self, url, depth_of_finding = None):
        self.complete_url = url
        parsed_url = urlparse(url)
        self.scheme = parsed_url.scheme
        self.domain = parsed_url.netloc
        if parsed_url.path != "/":
            self.path = parsed_url.path
        else:
            self.path = ""
        self.query = parsed_url.query
        self.fragment = parsed_url.fragment

        self.parameters = {}
        self.depth_of_finding = depth_of_finding
        self.url_structure = None
        self.abstract_url = None

        if len(parsed_url.query) > 0:
            query_splitted = self.query.split("&")
            for splits in query_splitted:
                tmp = splits.split("=")
                if len(tmp) == 2:
                    param_name = tmp[0]
                    param_value = tmp[1]
                else:
                    param_name = tmp[0]
                    param_value = None
                if param_name in self.parameters:
                    self.parameters[param_name].append(param_value)
                else:
                    self.parameters[param_name] = [param_value]
            keys = self.parameters.keys()
            keys = sorted(keys)
            tmp_params = {}
            for key in keys:
                tmp_params[key] = self.parameters[key]
            self.parameters = tmp_params

        self.url_hash = self.get_hash()

    def get_values_to_parameter(self, parameter_name):
        if parameter_name not in self.parameters:
            raise KeyError("{} is not in parameters".format(parameter_name))
        return self.parameters[parameter_name]

    def get_url_description(self):
        return self.url_structure

    def get_path(self):
        result = self.scheme + "://" + self.domain
        if self.path is not None and len(self.path) > 0:
            if self.path[0] == "/":
                result = self.scheme + "://" + self.domain + self.path
            else:
                result = self.scheme + "://" + self.domain + "/" + self.path
            return result
        else:
            return ""

    def get_hash(self):
        s_to_hash = self.path
        for k in self.parameters:
            s_to_hash += "++" + k
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()

    def toString(self):
        return self.complete_url

    def has_equal_description(self, other):
        if not isinstance(other, self.___class__):
            return False
        return self.url_hash == other.url_hash

    def equal_abstract_url(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.abstract_url == other.abstract_url

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.toString() == other.toString()

    def __ne__(self, other):
        return not self.__eq__(other)        
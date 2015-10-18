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


__author__ = 'constantin'

import hashlib
class AsyncRequests():

    def __init__(self, method, url, parameters=None):
        self.method = method
        self.url = url
        self.request_structure = None
        self.structure = None

        self.parameters = parameters
        if not isinstance(self.parameters, dict) and self.parameters is not None:
            self.handle_parameters()

    @property
    def request_hash(self):
        try:
            return self.get_hash()
        except AttributeError:
            raise AttributeError("You need first to analyze url")


    def handle_parameters(self):
        try:
            key_value_pairs = self.parameters.split("&")
            tmp = {}
            for key_value_pair in key_value_pairs:
                try:
                    key, value = key_value_pair.split("=")
                except ValueError:
                    continue
                tmp[key] = value
            tmp = sorted(tmp.items())
            self.parameters = {}
            for key, val in tmp:
                self.parameters[key] = val
        except AttributeError:
            self.parameters = None

    def get_hash(self):
        s_to_hash = self.url.abstract_url + "+" + self.method
        try:
            for k in [x[0] for x in self.parameters]:
                s_to_hash += "++" + k
        except TypeError:
            pass
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()
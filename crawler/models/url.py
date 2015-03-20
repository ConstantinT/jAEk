'''
Created on 23.02.2015

@author: constantin
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
        
        self.parameters = {}
        self.depth_of_finding = depth_of_finding

        self.url_description = None
       
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
        
    def get_abstract_url(self):
        return self.url_description

    def get_path(self):
        return self.scheme + "://" + self.domain + "/" + self.path

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
    
    def has_equal_abstract_url(self, other):
        if not isinstance(other, self.___class__):
            return False
        return self.url_hash == other.url_hash
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.toString() == other.toString()

    def __ne__(self, other):
        return not self.__eq__(other)        
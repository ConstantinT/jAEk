'''
Created on 23.02.2015

@author: constantin
'''
import string
from urllib.parse import urlparse, urljoin
from models.url import Url
from models.urldescription import ParameterType, ParameterOrigin, UrlDescription


class DomainHandler():
    def __init__(self, domain, persistence_manager):
        o = urlparse(domain)
        self.domain = o.netloc
        self.scheme = o.scheme
        self.persistence_manager = persistence_manager
        
    def get_next_url_for_crawling(self):
        url = self.persistence_manager.get_next_url_for_crawling()
        return self.create_url(url)

    def create_url(self, url, requested_url=None, depth_of_finding=None):

        if requested_url is not None:
            try:
                url = url.toString()
            except AttributeError:
                url = url
            new_url = urljoin(requested_url, url)
            url = Url(new_url)
        else:
            try:
                new_url = url.toString() # if there is nor error we have already a Url Object
            except AttributeError:
                url = Url(url, depth_of_finding) # else we must create one

        if url.url_description is None:
            url_description = self.persistence_manager.get_url_description_to_hash(url.url_hash)
            if url_description is None: # We have not seen a url of that structure
                url_path = url.get_path()
                url_description_parameters = {}
                for key in url.parameters:
                    new_parameter = {}
                    current_parameter_type = None
                    new_parameter['origin'] = ParameterOrigin.ServerGenerated.value
                    for value in url.parameters[key]: #This is for the case that a url has the same parameter multiple times
                        current_parameter_type = self.calculate_new_url_type(current_parameter_type, value)
                    new_parameter['parameter_type'] = current_parameter_type.value
                    new_parameter['generating'] = False
                    url_description_parameters[key] = new_parameter
                url_description = UrlDescription(url_path, url_description_parameters, url.url_hash)
                self.persistence_manager.insert_url_description_into_db(url_description)
            else:
                for key in url.parameters:
                    current_parameter_type = ParameterType(url_description.parameters[key]["parameter_type"])
                    for value in url.parameters[key]: #This is for the case that a url has the same parameter multiple times
                        current_parameter_type = self.calculate_new_url_type(current_parameter_type, value)
                    url_description.parameters[key]["parameter_type"] = current_parameter_type.value
                self.persistence_manager.insert_url_description_into_db(url_description)
            url.url_description = url_description
        return url
    
    def is_in_scope(self, url):
        url_splits = url.toString().split(".")
        end_of_url = url_splits[len(url_splits) - 1]
        if end_of_url in ['png', "jpg"]:
            return False
        parsed_url = urlparse(url.toString())
        if parsed_url.netloc.find(self.domain) != -1 and parsed_url.fragment == "":
            return True
        else:
            return False

    @staticmethod
    def append_http_to_domain(domain):
        return "http://" + domain

    def has_urls_same_structure(self, url1, url2):
        if url1.__class__ != url2.__class__:
            raise ValueError("Both must be Url...")
        
        if url1.toString() == url2.toString():
            return True
        
        if url1.domain != url2.domain or url1.path != url2.path or len(url1.params) != len(url2.params):
            return False
          
        for key in url1.params:
            if key not in url2.params:
                return False
            
        for key in url2.params:
            if key not in url1.params:
                return False
        
        return True

    def complete_urls(self, web_page):

        if web_page.base_url is not None:
            base_url = web_page.base_url
        else:
            base_url = web_page.url

        for link in web_page.links:
            link.url = self.create_url(link.url, web_page.url, web_page.current_depth)

        for request in web_page.timeming_requests:
            request.url = urljoin(base_url, request.url)
        for form in web_page.forms:
            form.action = urljoin(base_url, form.action)

        try:
            for ajax in web_page.ajax_requests:
                ajax.url = urljoin(base_url, ajax.url)
        except AttributeError:
            pass

        return web_page

    def calculate_new_url_type(self, current_type, value):
        if current_type is None: # When we see it the first time, then we just set this param to None
            if len(value) == 1:
                if value in string.ascii_lowercase + string.ascii_uppercase:
                    return ParameterType.Char
                elif self._is_int(value):
                    return ParameterType.Digit
                elif self._is_float(value):
                    return ParameterType.Float
                else:
                    raise ValueError("Len is one but I have not specified a case for: {}".format(value))
            else:
                if self._is_int(value):
                    return ParameterType.Integer
                elif self._is_float(value):
                    return ParameterType.Float
                elif isinstance(value, str):
                    if self._has_number(value):
                        return ParameterType.AlphaNumerical
                    else:
                        return ParameterType.String
                else:
                    raise ValueError("Is ling but not specified...")

        else:
            if current_type == ParameterType.Digit:
                return self._handle_digit(value)
            elif current_type == ParameterType.Float:
                return self._handle_float(value)
            elif current_type == ParameterType.Char:
                return self._handle_char(value)
            elif current_type == ParameterType.Integer:
                return self._handle_integer(value)
            elif current_type == ParameterType.String:
                return self._handle_string(value)
            else:
                return ParameterType.AlphaNumerical # One time alphanumerical erverytime alphanumerical


    def _is_int(self, value):
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _is_float(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False


    def _has_number(self, input):
        return any(self._is_int(char) or self._is_float(char) for char in input)

    def _handle_digit(self, value):
        if len(value) == 1:
            if self._is_int(value):
                return ParameterType.Digit
            if self._is_float(value):
                return ParameterType.Float
            if value in string.ascii_uppercase + string.ascii_lowercase:
                return ParameterType.Char
        else:
            if self._is_int(value):
                return ParameterType.Integer
            if self._is_float(value):
                return ParameterType.Float
            else:
                return ParameterType.AlphaNumerical

    def _handle_float(self, value):
        if self._is_float(value) or self._is_int(value):
                return ParameterType.Float
        if isinstance(value, str):
            return ParameterType.AlphaNumerical
        else:
            raise  ValueError("{}".format(value))


    def _handle_char(self, value):
        if len(value) == 1:
            return ParameterType.Char
        else:
            return ParameterType.AlphaNumerical

    def _handle_integer(self, value):
        if self._is_int(value):
            return ParameterType.Integer
        elif self._is_float(value):
            return ParameterType.Float
        else:
            return ParameterType.AlphaNumerical

    def _handle_string(self, value):
        if self._has_number(value):
            return ParameterType.AlphaNumerical
        else:
            return ParameterType.String




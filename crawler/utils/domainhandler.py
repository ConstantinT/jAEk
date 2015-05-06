'''
Created on 23.02.2015

@author: constantin
'''
import logging
import string
from urllib.parse import urlparse, urljoin

from models.url import Url
from models.urlstructure import ParameterType, ParameterOrigin, UrlStructure

INGORE_FILES = ['.png', ".jpg", ".js", ".swf"]

class DomainHandler():

    def __init__(self, domain, database_manager, cluster_manager):
        o = urlparse(domain)
        self.domain = o.netloc
        self.scheme = o.scheme
        self.database_manager = database_manager
        self.cluster_manager = cluster_manager
        
    def get_next_url_for_crawling(self):
        url = self.database_manager.get_next_url_for_crawling()
        if url is None:
            return None
        return url

    def is_in_scope(self, url):
        try:
            url = url.toString()
        except AttributeError:
            url = url
        url_splits = url.split("?")
        interesting_part = url_splits[0]
        for file_ending in INGORE_FILES:
            if file_ending in interesting_part:
                return False
        parsed_url = urlparse(url)
        if parsed_url.netloc.find(self.domain) != -1 and parsed_url.fragment == "":
            return True
        else:
            return False

    def handle_url(self, new_url, requested_url):
        if not isinstance(new_url, Url):
            new_url = Url(new_url)
        if requested_url is not None:
            if not isinstance(requested_url, Url):
                requested_url = Url(requested_url)
            new_url.abstract_url = self.calculate_abstract_url(new_url, requested_url)

        if not self.database_manager.url_exists(new_url):
            new_url.url_structure = self.calculate_url_structure(new_url)
        return new_url

    def calculate_url_structure(self, url):
        url_structure = self.database_manager.get_url_structure_to_hash(url.url_hash)
        if url_structure is None: # We have not seen a url of that structure
            url_path = url.get_path()
            url_description_parameters = {}
            for key in url.parameters:
                new_parameter = {}
                current_parameter_type = None
                new_parameter['origin'] = ParameterOrigin.ServerGenerated.value
                for value in url.parameters[key]: #This is for the case that a url has the same parameters multiple times
                    if value is not None:
                        current_parameter_type = self.calculate_new_url_type(current_parameter_type, value)
                    else:
                        current_parameter_type = ParameterType.NoParameter
                if current_parameter_type is not None:
                    new_parameter['parameter_type'] = current_parameter_type.value
                    new_parameter['generating'] = False
                    url_description_parameters[key] = new_parameter
            url_structure = UrlStructure(url_path, url_description_parameters, url.url_hash)
            self.database_manager.insert_url_structure_into_db(url_structure)
        else:
            for key in url.parameters:
                try:
                    current_parameter_type = ParameterType(url_structure.parameters[key]["parameter_type"])
                except KeyError:
                    logging.debug("Could not find parameter {} in url-structure with hash: {}".format(key, url_structure.url_hash))
                for value in url.parameters[key]: #This is for the case that a url has the same parameters multiple times
                    if value is not None:
                        current_parameter_type = self.calculate_new_url_type(current_parameter_type, value)
                        url_structure.parameters[key]["parameter_type"] = current_parameter_type.value
            self.database_manager.insert_url_structure_into_db(url_structure)
        return url_structure

    def calculate_abstract_url(self, new_url, requested_url):
        if new_url.complete_url == requested_url:
            return "[WEBPAGE_URL]"
        elif new_url.domain == requested_url.domain and new_url.path == requested_url.path:
            if new_url.query != "" and new_url.fragment != "":
                return "[WEBPAGE_PATH]" + "?" + new_url.query + "#" +new_url.fragment
            elif new_url.query != "" and new_url.fragment == "":
                return "[WEBPAGE_PATH]" + "?" + new_url.query
            elif new_url.query == "" and new_url.fragment != "":
                return "[WEBPAGE_PATH]" + "#" + new_url.fragment
            else:
                return "[WEBPAGE_PATH]"
        elif new_url.domain == requested_url.domain:
            if new_url.path == "" and new_url.query == "" and new_url.fragment == "":
                return "[WEBPAGE_DOMAIN]"
            elif new_url.path != "" and new_url.query == "" and new_url.fragment == "":
                return "[WEBPAGE_DOMAIN]" + new_url.path
            elif new_url.path == "" and new_url.query != "" and new_url.fragment == "":
                return "[WEBPAGE_DOMAIN]" + "?" + new_url.query
            elif new_url.path != "" and new_url.query != "" and new_url.fragment == "":
                return "[WEBPAGE_DOMAIN]" + new_url.path + "?" + new_url.query
            elif new_url.path == "" and new_url.query == "" and new_url.fragment != "":
                return "[WEBPAGE_DOMAIN]" + "#" + new_url.fragment
            elif new_url.path != "" and new_url.query == "" and new_url.fragment != "":
                return "[WEBPAGE_DOMAIN]" + new_url.path + "#" + new_url.fragment
            elif new_url.path == "" and new_url.query != "" and new_url.fragment != "":
                return "[WEBPAGE_DOMAIN]" + "?" + new_url.query + "#" + new_url.fragment
            elif new_url.path != "" and new_url.query != "" and new_url.fragment != "":
                return "[WEBPAGE_DOMAIN]" + new_url.path + "?" + new_url.query + "#" + new_url.fragment
        else:
            return new_url.complete_url # If we have a url to an foreign target, we have no abstraction




    @staticmethod
    def append_http_to_domain(domain):
        return "http://" + domain

    @staticmethod
    def has_urls_same_structure(url1, url2):
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

    def analyze_urls(self, web_page):
        base_url = self._get_base_url(web_page)
        for link in web_page.links:
            link.url = self.handle_url(link.url, base_url)
        for request in web_page.timing_requests:
            request.url = self.handle_url(request.url, base_url)
        for form in web_page.forms:
            form.action = self.handle_url(form.action, base_url)
        for ajax in web_page.ajax_requests:
            ajax.url = self.handle_url(ajax.url, base_url)
        try:
            if web_page.popup_url is not None:
                web_page.popup_url = self.handle_url(web_page.popup_url)
        except AttributeError:
            pass
        return web_page

    def set_url_depth(self, web_page, depth_of_finding):
        for link in web_page.links:
            link.url.depth_of_finding = depth_of_finding
        for request in web_page.timing_requests:
            request.url.depth_of_finding = depth_of_finding
        for form in web_page.forms:
            form.action.depth_of_finding = depth_of_finding
        for ajax in web_page.ajax_requests:
            ajax.url.depth_of_finding = depth_of_finding

        try:
            if web_page.popup_url is not None:
                web_page.popup_url.depth_of_finding = depth_of_finding
        except AttributeError:
            pass
        return web_page

    def _get_base_url(self, web_page):
        if web_page.base_url is not None:
            base_url = web_page.base_url
        else:
            base_url = web_page.url
        return base_url


    def complete_urls_in_page(self, web_page):
        base_url = self._get_base_url(web_page)

        for link in web_page.links:
            link.url = urljoin(base_url, link.url)
        for request in web_page.timing_requests:
            request.url = urljoin(base_url, request.url)
        for form in web_page.forms:
            form.action = urljoin(base_url, form.action)
        try:
            for ajax in web_page.ajax_requests:
                ajax.url = urljoin(base_url, ajax.url)
        except AttributeError:
            pass
        return web_page

    def extract_new_links_for_crawling(self, page):
        for link in page.links:
            if self.cluster_manager.need_more_urls_of_this_type(link.url.url_hash) \
                    and self.database_manager.num_of_ignored_urls(link.url.url_hash) < 10 \
                    and self.database_manager.count_visited_url_per_hash(link.url.url_hash) < 50:
                self.database_manager.insert_url_into_db(link.url)
        for ajax in page.ajax_requests + page.timing_requests:
            if self.cluster_manager.need_more_urls_of_this_type(ajax.url.url_hash) \
                    and self.database_manager.num_of_ignored_urls(ajax.url.url_hash) < 10 \
                    and self.database_manager.count_visited_url_per_hash(ajax.url.url_hash) < 50:
                self.database_manager.insert_url_into_db(ajax.url)
        for form in page.forms:
            if self.cluster_manager.need_more_urls_of_this_type(form.action.url_hash) \
                    and self.database_manager.num_of_ignored_urls(form.action.url_hash) < 10 \
                    and self.database_manager.count_visited_url_per_hash(form.action.url_hash) < 50:
                self.database_manager.insert_url_into_db(form.action)

    def calculate_new_url_type(self, current_type, value):
        if current_type is None: # When we see it the first time, then we just set this param to None
            if len(value) == 1:
                if value in string.ascii_lowercase + string.ascii_uppercase + "/":
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




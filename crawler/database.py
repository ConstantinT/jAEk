from models import WebPage, ClickableType, CrawlerUser
from pymongo.connection import Connection
import pymongo
import hashlib
from IPython.config.configurable import LoggingConfigurable
import logging
import models

class Database():
    
    def __init__(self, db_name):
        self.connection=Connection()
        self.database = self.connection[db_name]
        
        
        self.pages = self.database.pages
        self.pages.drop() #Clear database
        #self.pages.ensure_index( "id", pymongo.ASCENDING, unique=True)
        
        
        self.visited_urls = self.database.visited_urls
        self.visited_urls.drop() #Clear database
        self.visited_urls.ensure_index( "url", pymongo.ASCENDING, unique=True)
        
        self.abstract_urls = self.database.abstract_urls
        self.abstract_urls.drop() #Clear database
        
        self.clickables = self.database.clickables
        self.clickables.drop()
        
        self.delta_pages = self.database.delta_pages
        self.delta_pages.drop()
        
        self.forms = self.database.forms
        self.forms.drop()
        
        self.users = self.database.users
        self.users.drop()
        
        self._current_session_id = None
        
    def __del__(self):
        self.connection.close()
     
    def get_user_to_username(self, username):
        search_doc = {'username' :username}
        user = self.users.find_one(search_doc)
        if user is None:
            return None
        if user['username'] == username:
            tmp = CrawlerUser(user['username'], user['user_level'], user['url_with_login_form'], user['login_data']) 
            tmp.sessions = user['sessions']
            return tmp

    
    def add_user_session(self, user_id, session):
        self.users.update({"_id" : user_id}, {"$addToSet" : {"sessions" : session}}) 
        self._current_session_id = session   
        
    def insert_user(self, user):
        doc = {}
        doc['_id'] = user.user_id
        doc['user_level'] = user.user_level
        doc['username'] = user.username
        doc['sessions'] = user.sessions
        if user.login_data is not None:
            doc['login_data'] = user.login_data
        self._current_session_id = user.sessions[-1]
        self.users.save(doc)
    
    
    def insert_abstract_url(self, url):
        url_hash = self.calculate_url_hash(url)
        search_doc = {"url_hash" : url_hash, "user_session" : self._current_session_id}
        result = self.abstract_urls.find_one(search_doc)
        path, params = url.get_url_structure()
        document = {}
        document["path"] = path
        document['user_session'] = self._current_session_id
        document['url_hash'] = url_hash
        
        if result is not None:
            document["_id"] = result["_id"]
            for k,v in result['params'].items():
                if v not in params.values():
                    params[k].extend(v)
            document["params"] = params
        else:
            document["params"] = params
        self.abstract_urls.save(document)
    
    def insert_url(self, url):
        self.insert_abstract_url(url)
        document = {}
        document["url"] = url.toString()
        document['user_session'] = self._current_session_id
        document["page_id"] = None
        document["visited"] = False
        document["response_code"] = None
        return self.visited_urls.save(document)
    
    def calculate_url_hash(self, url):
        s_to_hash = url.get_hash()
        s_to_hash += "+/+" + str(self._current_session_id)
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()
    
        
    def visit_url(self, url, webpage_id, response_code):
        search_doc = {}
        search_doc['url'] = url.toString()
        search_doc['user_session'] = self._current_session_id
        
        update_doc = {}
        update_doc['response_code'] = response_code
        update_doc['visited'] = True
        update_doc['page_id'] = webpage_id
        self.visited_urls.update(search_doc, {"$set": update_doc})
             
    def insert_page(self, web_page):
        for clickable in web_page.clickables:
            self._insert_clickable(web_page.id, clickable)
        for form in web_page.forms:
            self.insert_form(form, web_page.id)
        
        document = self._create_webpage_doc(web_page)
        document['user_session'] = self._current_session_id
        self.pages.save(document)
            
    def insert_delta_page(self, delta_page):
        for clickable in delta_page.clickables:
            self._insert_clickable(delta_page.id, clickable)
        for form in delta_page.forms:
            self.insert_form(form, delta_page.id)
            
        document = self._create_webpage_doc(delta_page)
        clickable_id = self.clickables.find_one({"session_id" : self._current_session_id, "web_page_id":delta_page.parent_id, "dom_adress":delta_page.generator.dom_adress, "event":delta_page.generator.event})
        clickable_id = clickable_id["_id"]
        document['generator'] = clickable_id
        generator_request_doc = []
        for r in delta_page.generator_requests:
            doc = {}
            doc["url"] = r.url
            doc["method"] = r.method
            trigger_id = self.clickables.find_one({"session_id" : self._current_session_id, "dom_adress" : r.trigger.dom_adress, "web_page_id": delta_page.parent_id, "event": r.trigger.event})
            trigger_id = trigger_id["_id"]
            doc["trigger"] = trigger_id
            generator_request_doc.append(doc)
        document["generator_requests"] = generator_request_doc
        
        document['parent_id'] = delta_page.parent_id
        ajax_request_docs = []
        for ajax in delta_page.ajax_requests:
            doc = {}
            doc["url"] = ajax.url
            doc["method"] = ajax.method
            trigger_id = self.clickables.find_one({"session_id" : self._current_session_id, "dom_adress" : ajax.trigger.dom_adress, "web_page_id": delta_page.id, "event": ajax.trigger.event})
            trigger_id = trigger_id["_id"]
            doc["trigger"] = trigger_id
            ajax_request_docs.append(doc)
        document["ajax_requests"] = ajax_request_docs
        document['user_id'] = self._current_session_id
        self.delta_pages.save(document)
        
        
    def _create_webpage_doc(self, web_page):
        document = {}
        document["web_page_id"] = web_page.id
        document["url"] = web_page.url
        document["html"] = web_page.html
        document["links"] = []
        for link in web_page.links:
            document["links"].append(self._parse_link(link)) 
        timeming_requests_doc = []
        for timing_request in web_page.timing_requests:
            timeming_requests_doc.append(self._parse_timeming_request(timing_request))
        document['session_id'] = self._current_session_id
        document['timeming_requests'] = timeming_requests_doc
        document["current_depth"] = web_page.current_depth
        return document
    
    def insert_form(self, form, page_id):
        form_hash = self.calculating_form_hash(form, page_id)
        result = self.forms.find_one({"form_hash":form_hash})
        
        if result is not None:
            for p_db in result['parameters']:
                for p_form in form.parameter:
                    if p_db['name'] == p_form.name:
                        p_form.values.extend(p_db['values'])
                        p_form.values = sorted(set(p_form.values), key=lambda x: p_form.values.index(x)) #Deduplicates the list
        form_doc = {}
        if result is not None:
            form_doc['_id'] = result["_id"]
        form_doc["web_page_id"] = page_id
        form_doc["method"] = form.method
        form_doc["action"] = form.action
        if form.submit is not None:
            form_doc["submit"] = self._parse_form_parameter(form.submit)
        param_doc = []
        for parameter in form.parameter:
            param_doc.append(self._parse_form_parameter(parameter))
        form_doc['parameters'] = param_doc
        form_doc['session_id'] = self._current_session_id
        form_doc['form_hash'] = form_hash
        self.forms.save(form_doc)
    
    def _parse_timeming_request(self, request):
        res = {}
        res['method'] = request.method
        res['url'] = request.url
        res['event'] = request.event
        res['function_id'] = request.function_id
        return res
        
    def _parse_link(self, link):
        res = {}
        res['url'] = link.url.toString()
        res['dom_adress'] = link.dom_adress
        res['html_id'] = link.html_id
        res['html_class'] = link.html_class
        return res
    
    def _parse_form_parameter(self, form_parameter):
        param = {}
        param["tag"] = form_parameter.tag
        param["name"] = form_parameter.name
        param["values"] = form_parameter.values
        param["input_type"] = form_parameter.input_type
        return param
        
    def set_clickable_clicked(self, web_page_id, clickable_dom_adress, clickable_event, clickable_type = None):
        search_doc = {}
        set_doc = {}
        
        search_doc["web_page_id"] = web_page_id
        search_doc["dom_adress"] = clickable_dom_adress
        search_doc["event"] = clickable_event
        search_doc['session_id'] = self._current_session_id
        
        if clickable_type is not None:
            clickable_type = self._clickable_type_to_num(clickable_type)
            set_doc["clickable_type"] = clickable_type
            
        set_doc["clicked"] = "True"
        set_doc = {"$set": set_doc}
        result = self.clickables.update(search_doc, set_doc)
        return result
    
    def set_clickable_ignored(self, web_page_id, clickable_dom_adress, clickable_event, clickable_type = None):
        search_doc = {}
        set_doc = {}
        
        search_doc["web_page_id"] = web_page_id
        search_doc["dom_adress"] = clickable_dom_adress
        search_doc["event"] = clickable_event
        search_doc['session_id'] = self._current_session_id
        
        if clickable_type is not None:
            clickable_type = self._clickable_type_to_num(clickable_type)
            set_doc["clickable_type"] = clickable_type
            
        set_doc["clicked"] = "False"
        set_doc = {"$set": set_doc}
        result = self.clickables.update(search_doc, set_doc)
        return result
    
    def _parse_ajax_request(self, ajax_request, web_page_id):
        doc = {}
        doc["url"] = ajax_request.url
        doc["method"] = ajax_request.method
        trigger_id = self.clickables.find_one({"session_id": self._current_session_id, "dom_adress" : ajax_request.trigger.dom_adress, "web_page_id": web_page_id, "event": ajax_request.trigger.event})
        trigger_id = trigger_id["_id"]
        doc['parameters'] = ajax_request.parameter
        doc["trigger"] = trigger_id
        return doc
    
    def _extend_ajax_requests_to_webpage(self, webpage, ajax_reuqests):
        ajax_reuqests_doc = []
        for r in ajax_reuqests:
            ajax_reuqests_doc.append(self._parse_ajax_request(r, web_page_id=webpage.id))
        self.pages.update({"web_page_id": webpage.id, "session_id":self._current_session_id}, {"$addToSet" : {"ajax_requests": ajax_reuqests_doc}})
       
    def _insert_clickable(self, web_page_id, clickable):
        document = {}
        document["event"]= clickable.event
        document["tag"] = clickable.tag
        document["class"] = clickable.html_class
        document["html_id"] = clickable.id
        document["dom_adress"] = clickable.dom_adress
        document["links_to"] = clickable.links_to
        document["clicked"] = clickable.clicked
        document["clickable_type"] = self._clickable_type_to_num(clickable.clickable_type)
        document["web_page_id"] = web_page_id
        document["function_id"] = clickable.function_id
        if hasattr(clickable, "random_char"):
            document['random_char'] = clickable.random_char  
        document['session_id'] = self._current_session_id      
        self.clickables.save(document)
        
    def _clickable_type_to_num(self, clickable_type):
        if clickable_type == ClickableType.UI_Change:
            return 0
        if clickable_type == ClickableType.Link:
            return 1
        if clickable_type == ClickableType.Creates_new_navigatables:
            return 2
        if clickable_type == ClickableType.Error:
            return 3
        if clickable_type == ClickableType.SendingAjax:
            return 4
        if clickable_type == ClickableType.Ignored_by_Crawler:
            return 5
        if clickable_type == ClickableType.Unsuported_Event:
            return 6
        
    def calculating_form_hash(self, form, web_page_id):
        s_to_hash = str(self._current_session_id) + ";" + form.action + ";" + form.method + ";" + str(web_page_id) + ";"
        for p in form.parameter:
            s_to_hash += p.name + ";" + p.tag + ";" + str(p.input_type) + ";"
        b_to_hash = s_to_hash.encode("utf-8")
        d = hashlib.md5()
        d.update(b_to_hash)
        return d.hexdigest()
        
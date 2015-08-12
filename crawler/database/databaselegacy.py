import logging
from pymongo.connection import Connection
import pymongo
from models.timingrequest import TimingRequest
from models.urlstructure import UrlStructure

from utils.user import User
from models.url import Url
from models.webpage import WebPage
from models.clickable import Clickable
from models.ajaxrequest import AjaxRequest
from models.link import Link
from models.clickabletype import ClickableType
from models.form import HtmlForm, FormInput
from models.deltapage import DeltaPage


class DatabaseLegacy():
    
    def __init__(self, db_name):
        self.connection=Connection()
        self.database = self.connection[db_name]
        
        
        self.pages = self.database.pages
        #self.pages.drop() #Clear database
        #self.pages.ensure_index( "id", pymongo.ASCENDING, unique=True)
        
        
        self.visited_urls = self.database.visited_urls
        #self.visited_urls.drop() #Clear database
        #self.visited_urls.ensure_index( "url", pymongo.ASCENDING, unique=True)
        
        self.url_descriptions = self.database.url_describtion
        #self.url_descriptions.drop() #Clear database
        #self.url_descriptions.ensure_index("hash", pymongo.ASCENDING, unique=True)
        
        self.clickables = self.database.clickables
        #self.clickables.drop()
        
        self.delta_pages = self.database.delta_pages
        #self.delta_pages.drop()
        
        self.forms = self.database.forms
        #self.forms.drop()
        
        self.users = self.database.users
        #self.users.drop()
        #self._per_session_url_counter = 0
        
    def __del__(self):
        self.connection.close()
     
    def prepare_for_new_crawling(self):
        self._per_session_url_counter = 0
        
    def get_user_to_username(self, username):
        search_doc = {'username' :username}
        user = self.users.find_one(search_doc)
        if user is None:
            return None
        if user['username'] == username:
            tmp = User(user['username'], user['user_level'], user['url_with_login_form'], user['login_data'])
            tmp.sessions = user['sessions']
            return tmp

        
    def insert_user(self, user):
        doc = {}
        num_of_users = self.users.count()
        user_id = num_of_users + 1
        doc['_id'] = user_id
        doc['user_level'] = user.user_level
        doc['username'] = user.username
        doc['sessions'] = user.session
        if user.login_data is not None and user.url_with_login_form is not None:
            doc['url_with_login_form'] = user.url_with_login_form
            doc['login_data'] = user.login_data
        self.users.save(doc)
    
    def insert_url(self, current_crawl_session, url, is_redirected_url = False):
        if not is_redirected_url:
            if self.visited_urls.find({"url":url.toString(), "crawl_session":current_crawl_session}).count() > 0 and self.visited_urls.find({"redirected_to":url.toString(), "crawl_session":current_crawl_session}).count() > 0:
                return

        document = {}
        document["url"] = url.toString()
        document["url_hash"] = url.url_hash
        document['crawl_session'] = current_crawl_session
        document["page_id"] = None
        document["visited"] = False
        document["response_code"] = None
        document['redirected_to'] = None
        document["url_counter"] = self._per_session_url_counter
        document['depth_of_finding'] = url.depth_of_finding
        self._per_session_url_counter += 1
        self.visited_urls.save(document)
    
    def _parse_url_from_db_to_model(self, url):
        return Url(url['url'], url['depth_of_finding'])
    
    def get_next_url_for_crawling(self, current_crawl_session):
        urls = self.visited_urls.find({"crawl_session":current_crawl_session, "response_code" : None})
        if urls.count() == 0:
            return None
        result = None
        for url in urls:
            if result is None:
                result = url
            else:
                if url["url_counter"]<result['url_counter']:
                    result = url
        return self._parse_url_from_db_to_model(result)  
    
        
    def visit_url(self, current_crawl_session, url, webpage_id, response_code, redirected_to = None):
        search_doc = {}
        search_doc['url'] = url.toString()
        search_doc['crawl_session'] = current_crawl_session
        
        update_doc = {}
        update_doc['response_code'] = response_code
        if webpage_id != None:
            update_doc['visited'] = True
        update_doc['page_id'] = webpage_id
        update_doc['redirected_to'] = redirected_to
        self.visited_urls.update(search_doc, {"$set": update_doc})
             
    def insert_page(self, current_crawl_session, web_page):
        for clickable in web_page.clickables:
            self._insert_clickable(current_crawl_session, web_page.id, clickable)
        for form in web_page.forms:
            self.insert_form(current_crawl_session, form, web_page.id)
        
        document = self._create_webpage_doc(web_page)
        document['ajax_requests'] = []
        document['crawl_session'] = current_crawl_session
        self.pages.save(document)

    def get_all_pages(self, current_crawl_session):
        results = []
        counter = 1
        pages = self.pages.find({"crawl_session": current_crawl_session})
        for page in pages:
            results.append(self.get_web_page(current_crawl_session=current_crawl_session, page=page))
            #logging.debug("Round number: {} from {}".format(fragment_counter, pages.count()))
            counter += 1
        return results
        
    def get_web_page(self, page_id=None, current_crawl_session=0, page=None):
        if page is None:
            page = self.pages.find_one({"crawl_session": current_crawl_session,"web_page_id":page_id })
        if page is None:
            logging.debug("Return None")
            return None
        clickables = self.get_all_clickables_to_page_id(current_crawl_session, page["web_page_id"])
        forms = self.get_all_forms_to_page_id(current_crawl_session, page["web_page_id"])
        result = WebPage(page['web_page_id'], page['url'], page['html'], None, page['current_depth'], page['base_url'])
        result.clickables = clickables
        result.forms = forms
        links = []
        for link in page['links']:
            links.append(self._parse_link_from_db_to_model(link))
        result.links = links
        timemimg_requests = []
        for request in page['timing_requests']:
            timemimg_requests.append(self._parse_timemimg_request_from_db_to_model(request))
        result.timing_requests = timemimg_requests
        ajax = []
        for request in page['ajax_requests']:
            ajax.append(self._parse_ajax_request_from_db_to_model(request))
        result.ajax_requests = ajax
        return result  
    
    def _parse_clickable_from_db_to_model(self, clickable):
        c = Clickable(clickable['event'], clickable['tag'], clickable['dom_adress'], clickable['html_id'], clickable['html_class'], clickable['clickable_depth'], clickable['function_id'])
        c.clicked = clickable['clicked']
        c.clickable_type = self._num_to_clickable_type(clickable['clickable_type'])
        c.links_to = clickable['links_to']
        c.clickable_depth = clickable['clickable_depth']
        return c
    
    def _parse_timemimg_request_from_db_to_model(self, timemimg_request):
        return TimingRequest(timemimg_request['method'], timemimg_request['url'], timemimg_request['time'],
                             timemimg_request['event'])
    
    def _parse_ajax_request_from_db_to_model(self, ajax_request):
        tmp = self.clickables.find_one(ajax_request['trigger'])
        trigger = self._parse_clickable_from_db_to_model(tmp)
        return AjaxRequest(ajax_request['method'], ajax_request['url'], trigger, ajax_request['parameters'])
        
    def _insert_clickable(self, current_crawl_session , web_page_id, clickable):
        document = {}
        document["event"]= clickable.event
        document["tag"] = clickable.tag
        document["html_class"] = clickable.html_class
        document["html_id"] = clickable.id
        document["dom_adress"] = clickable.dom_adress
        document["links_to"] = clickable.links_to
        document["clicked"] = clickable.clicked
        document["clickable_type"] = self._clickable_type_to_num(clickable.clickable_type)
        document["web_page_id"] = web_page_id
        document["function_id"] = clickable.function_id
        document["clickable_depth"] = clickable.clickable_depth
        if hasattr(clickable, "random_char"):
            document['random_char'] = clickable.random_char  
        document['crawl_session'] = current_crawl_session      
        self.clickables.save(document)
        
    def insert_delta_page(self, current_crawl_session, delta_page):
        for clickable in delta_page.clickables:
            self._insert_clickable(current_crawl_session, delta_page.id, clickable)
        for form in delta_page.forms:
            self.insert_form(current_crawl_session, form, delta_page.id)
            
        document = self._create_webpage_doc(delta_page)
        clickable_id = self.clickables.find_one({"crawl_session" : current_crawl_session, "web_page_id":delta_page.parent_id, "dom_adress":delta_page.generator.dom_adress, "event":delta_page.generator.event})
        clickable_id = clickable_id["_id"]
        document['generator'] = clickable_id
        generator_request_doc = []
        for r in delta_page.generator_requests:
            doc = {}
            doc["url"] = r.url
            doc["method"] = r.method
            trigger_id = self.clickables.find_one({"crawl_session" : current_crawl_session, "dom_adress" : r.trigger.dom_adress, "web_page_id": delta_page.parent_id, "event": r.trigger.event})
            trigger_id = trigger_id["_id"]
            doc["trigger"] = trigger_id
            doc["parameters"] = r.parameter
            generator_request_doc.append(doc)
        document["generator_requests"] = generator_request_doc
        
        document['delta_depth'] = delta_page.delta_depth
        document['parent_id'] = delta_page.parent_id
        ajax_request_docs = []
        for ajax in delta_page.ajax_requests:
            doc = {}
            doc["url"] = ajax.url
            doc["method"] = ajax.method
            trigger_id = self.clickables.find_one({"crawl_session" : current_crawl_session, "dom_adress" : ajax.trigger.dom_adress, "web_page_id": delta_page.id, "event": ajax.trigger.event})
            trigger_id = trigger_id["_id"]
            doc["trigger"] = trigger_id
            doc["parameters"] = ajax.parameter
            ajax_request_docs.append(doc)
        document["ajax_requests"] = ajax_request_docs
        document['crawl_session'] = current_crawl_session
        self.delta_pages.save(document)
    
    def get_delta_page(self, page_id, current_crawl_session):
        page = self.delta_pages.find_one({"crawl_session": current_crawl_session,"web_page_id":page_id })
        if page is None:
            return None
        result = self._parse_delta_page_from_db(current_crawl_session, page)
        return result
        
    def _create_webpage_doc(self, web_page):
        document = {}
        document["web_page_id"] = web_page.id
        document["url"] = web_page.url
        document["html"] = web_page.html
        document["links"] = []
        for link in web_page.links:
            document["links"].append(self._parse_link(link)) 
        timeming_requests_doc = []
        for timing_request in web_page.timeming_requests:
            timeming_requests_doc.append(self._parse_timeming_request(timing_request))
        document['timing_requests'] = timeming_requests_doc
        document["current_depth"] = web_page.current_depth
        document['base_url'] = web_page.base_url
        return document
    
    def insert_form(self, current_crawl_session, form, page_id):
        form_hash = form.form_hash
        result = self.forms.find_one({"form_hash":form_hash, "crawl_session":current_crawl_session, "web_page_id": page_id})
        form_doc = {}
        
        if result is not None:
            for parameter_from_db_form in result['parameters']:
                for parameter_from_new_form in form.parameter:
                    if parameter_from_db_form['name'] == parameter_from_new_form.name:
                        parameter_from_new_form.values.extend(parameter_from_db_form['values'])
                    parameter_from_new_form.values = sorted(set(parameter_from_new_form.values), key=lambda x: parameter_from_new_form.values.index(x)) #Deduplicates the list
            form_doc['_id'] = result["_id"]
        form_doc["web_page_id"] = page_id
        form_doc["method"] = form.method
        form_doc["action"] = form.action
        form_doc["dom_address"] = form.dom_address
        param_doc = []
        for parameter in form.parameter:
            param_doc.append(self._parse_form_parameter(parameter))
        form_doc['parameters'] = param_doc
        form_doc['crawl_session'] = current_crawl_session
        form_doc['form_hash'] = form_hash
        self.forms.save(form_doc)
    
    def _parse_timeming_request(self, request):
        res = {}
        res['method'] = request.method
        res['url'] = request.url
        res['event'] = request.event
        res['function_id'] = request.function_id
        res['time'] = request.time
        return res
        
    def _parse_link(self, link):
        res = {}
        res['url'] = link.url.toString()
        res['abstract_url_hash'] = link.url.get_hash()
        res['dom_adress'] = link.dom_adress
        res['html_id'] = link.html_id
        res['html_class'] = link.html_class
        return res
    
    def _parse_link_from_db_to_model(self, link):
        url = Url(link['url'])
        result = Link(url, link['dom_adress'], link['html_id'], link['html_class'])
        return result
    
    def _parse_form_parameter(self, form_parameter):
        param = {}
        param["tag"] = form_parameter.tag
        param["name"] = form_parameter.name
        param["values"] = form_parameter.values
        param["input_type"] = form_parameter.input_type
        return param
        
    def set_clickable_clicked(self, current_crawl_session,web_page_id, clickable_dom_adress, clickable_event, clickable_depth = None ,clickable_type = None, links_to=None):
        search_doc = {}
        set_doc = {}
        
        search_doc["web_page_id"] = web_page_id
        search_doc["dom_adress"] = clickable_dom_adress
        search_doc["event"] = clickable_event
        search_doc['crawl_session'] = current_crawl_session
        
        if clickable_type is not None:
            clickable_type = self._clickable_type_to_num(clickable_type)
            set_doc["clickable_type"] = clickable_type
            
        if links_to is not None:
            set_doc['links_to'] = links_to
            
        if clickable_depth is not None:
            set_doc['clickable_depth'] = clickable_depth
            
        set_doc["clicked"] = True
        set_doc = {"$set": set_doc}
        result = self.clickables.update(search_doc, set_doc)
        return result
    
    def set_clickable_ignored(self, current_crawl_session, web_page_id, clickable_dom_adress, clickable_event, clickable_depth = None, clickable_type = None):
        search_doc = {}
        set_doc = {}
        
        search_doc["web_page_id"] = web_page_id
        search_doc["dom_adress"] = clickable_dom_adress
        search_doc["event"] = clickable_event
        search_doc['crawl_session'] = current_crawl_session
        
        if clickable_type is not None:
            clickable_type = self._clickable_type_to_num(clickable_type)
            set_doc["clickable_type"] = clickable_type
        
        if clickable_depth is not None:
            set_doc['clickable_depth'] = clickable_depth
            
        set_doc["clicked"] = "False"
        set_doc = {"$set": set_doc}
        result = self.clickables.update(search_doc, set_doc)
        return result
    
    def _parse_ajax_request(self, current_crawl_session, ajax_request, web_page_id):
        doc = {}
        doc["url"] = ajax_request.url
        doc["method"] = ajax_request.method
        trigger_id = self.clickables.find_one({"crawl_session": current_crawl_session, "dom_adress" : ajax_request.trigger.dom_adress, "web_page_id": web_page_id, "event": ajax_request.trigger.event})
        trigger_id = trigger_id["_id"]
        doc['parameters'] = ajax_request.parameter
        doc["trigger"] = trigger_id
        return doc
    
    def extend_ajax_requests_to_webpage(self, current_crawl_session, webpage, ajax_reuqests):
        ajax_reuqests_doc = []
        for r in ajax_reuqests:
            ajax_reuqests_doc.append(self._parse_ajax_request(current_crawl_session, r, web_page_id=webpage.id))
        if not hasattr(webpage, 'parent_id'):
            result = self.pages.update({"web_page_id": webpage.id, "crawl_session":current_crawl_session}, { "$addToSet" : {"ajax_requests": {"$each" :ajax_reuqests_doc}}})
        else:
            result = self.delta_pages.update({"web_page_id": webpage.id, "crawl_session":current_crawl_session}, { "$addToSet" : {"ajax_requests": {"$each" :ajax_reuqests_doc}}})      
        
        
    def _clickable_type_to_num(self, clickable_type):
        if clickable_type == ClickableType.UIChange:
            return 0
        if clickable_type == ClickableType.Link:
            return 1
        if clickable_type == ClickableType.CreatesNewNavigatables:
            return 2
        if clickable_type == ClickableType.Error:
            return 3
        if clickable_type == ClickableType.SendingAjax:
            return 4
        if clickable_type == ClickableType.IgnoredByCrawler:
            return 5
        if clickable_type == ClickableType.UnsupportedEvent:
            return 6
        
    def _num_to_clickable_type(self, num):
        if num is None:
            return None
        clickable_types = { 0 : ClickableType.UIChange,
                           1: ClickableType.Link,
                           2: ClickableType.CreatesNewNavigatables,
                           3: ClickableType.Error,
                           4: ClickableType.SendingAjax,
                           5: ClickableType.IgnoredByCrawler,
                           6: ClickableType.UnsupportedEvent
                           }
        return clickable_types[num]
    
    def get_all_clickables_to_page_id(self, current_crawl_session, page_id):
        clickables = self.clickables.find({"web_page_id" : page_id, "crawl_session":current_crawl_session})
        result = []
        for clickable in clickables:
            c = Clickable(clickable['event'], clickable['tag'], clickable['dom_adress'], clickable['html_id'], clickable['html_class'], clickable_depth=clickable['clickable_depth'], function_id=clickable['function_id'])
            c.links_to = clickable['links_to']
            c.clickable_type = self._num_to_clickable_type(clickable['clickable_type'])
            c.clicked = clickable['clicked']
            result.append(c)
        return result
    
    def get_all_forms_to_page_id(self, current_crawl_session, page_id):
        forms = self.forms.find({"web_page_id" : page_id, "crawl_session" : current_crawl_session})
        result = []
        for form in forms:
            parameters = []
            for p in form['parameters']:
                form_input = FormInput(p['tag'], p['name'], p['input_type'], p['values'])
                parameters.append(form_input)
            f = HtmlForm(parameters, form['action'], form['method'])
            result.append(f)
        return result
    
    def get_all_crawled_deltapages_to_url(self, current_crawl_session, url):
        pages = self.delta_pages.find({"url":url, "crawl_session":current_crawl_session})
        result = []
        for page in pages:
            result.append(self._parse_delta_page_from_db(current_crawl_session, page))
        return result
            
    def _parse_delta_page_from_db(self, current_crawl_session, page):
        clickables = self.get_all_clickables_to_page_id(current_crawl_session, page['web_page_id'])
        forms = self.get_all_forms_to_page_id(current_crawl_session, page['web_page_id'])
        generator = self.clickables.find_one({"_id":page['generator']})
        generator = self._parse_clickable_from_db_to_model(generator)
        generator_requests = []
        for g in page['generator_requests']:
            generator_requests.append(self._parse_ajax_request_from_db_to_model(g))
        result = DeltaPage(page['web_page_id'], page['url'], page['html'], None, page['current_depth'], generator, page['parent_id'], page['delta_depth'])
        links = []
        for link in page['links']:
            links.append(self._parse_link_from_db_to_model(link))
        result.links = links
        result.forms = forms
        result.clickables = clickables
        result.generator_requests = generator_requests
        return result
    
    def get_webpage_to_url(self, current_crawl_session ,url):
        result = self.visited_urls.find_one({"url": url, "crawl_session" : current_crawl_session})
        if result is not None and result["visited"] is True:
            return self.get_web_page(result['page_id'], current_crawl_session)

    def insert_url_description(self, current_session, url_description):
        search_doc = {"hash":url_description.url_hash}
        result = self.url_descriptions.find_one({"session": current_session, "url_hash": url_description.url_hash})
        document = {}
        if result is not None:
            document["_id"] = result["_id"]
        document["path"] = url_description.path
        document["parameters"] = url_description.parameters
        document["url_hash"] = url_description.url_hash
        document["session"] = current_session
        self.url_descriptions.save(document)

    def get_url_description(self, current_session, url_hash):
        result = self.url_descriptions.find_one({"session": current_session, "url_hash": url_hash})
        if result is None:
            return None
        return UrlStructure(result['path'], result["parameters"], result['url_hash'])
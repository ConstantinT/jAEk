import logging
from pymongo.connection import Connection
import pymongo
from models.asyncrequeststructure import AsyncRequestStructure
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

#Keywords

SESSION = "session"
DOM_ADDRESS = "dom_address"

class Database():
    
    def __init__(self, db_name, drop_dbs=True):
        self.connection=Connection()
        self.database = self.connection[db_name]
        self.pages = self.database.pages
        #self.pages.ensure_index( "id", pymongo.ASCENDING, unique=True)
        self.urls = self.database.urls
        self.url_descriptions = self.database.url_describtion
        self.clickables = self.database.clickables
        self.delta_pages = self.database.delta_pages
        self.forms = self.database.forms
        self.users = self.database.users
        self.clusters = self.database.clusters
        self.attack = self.database.attack
        self.async_requests = self.database.asyncrequests
        self.async_request_structure = self.database.asyncrequeststructure

        self._per_session_url_counter = 0

        if drop_dbs:
            self.pages.drop() #Clear database
            self.urls.drop() #Clear database
            self.url_descriptions.drop()
            self.delta_pages.drop()
            self.clickables.drop()
            self.forms.drop()
            self.users.drop()
            self.clusters.drop()
            self.attack.drop()
            self.async_requests.drop()
            self.async_request_structure.drop()
            self.urls.ensure_index("url", pymongo.ASCENDING, unique=True)
            #self.url_descriptions.ensure_index("hash", pymongo.ASCENDING, unique=True)

        
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

    def insert_user_into_db(self, user):
        num_of_users = self.users.count()
        user_id = num_of_users + 1
        doc = self._user_to_doc(user)
        doc['_id'] = user_id
        if user.login_data is not None and user.url_with_login_form is not None:
            doc['url_with_login_form'] = user.url_with_login_form
            doc['login_data'] = user.login_data
        self.users.save(doc)

    def _user_to_doc(self, user):
        doc = {}
        doc['user_level'] = user.user_level
        doc['username'] = user.username
        doc['session'] = user.session
        return doc

    def insert_url_into_db(self, current_session, url, is_redirected_url = False):
        """
        :param current_session:
        :param url:
        :param is_redirected_url:
        :return: True if url is insert, if url exists False
        """

        if self.urls.find({"url": url.toString(), "session": current_session}).count() > 0 or self.urls.find({"redirected_to": url.toString(), "session": current_session}).count() > 0:
            return False
        document = self._url_to_doc_without_abstract_url(url)
        document['session'] = current_session
        document["url_counter"] = self._per_session_url_counter
        self._per_session_url_counter += 1
        self.urls.save(document)
        return True

    def _url_to_doc_without_abstract_url(self, url):
        doc = {}
        doc["url"] = url.complete_url
        #doc["abstract_url"] = url.abstract_url
        doc["url_hash"] = url.url_hash
        doc["page_id"] = None
        doc["visited"] = False
        doc["response_code"] = None
        doc['redirected_to'] = None
        doc['depth_of_finding'] = url.depth_of_finding
        return doc

    def get_next_url_for_crawling(self, current_session):
        urls = self.urls.find({"session": current_session, "visited": False}).sort([('url_counter', pymongo.ASCENDING)]).limit(1)
        if urls is None or urls.count() == 0:
            return None
        else:
            url = self._parse_url_from_db(urls[0])
            url.url_structure = self.get_url_structure_from_db(current_session, url.url_hash)
            return url

    def get_all_unvisited_urls_sorted_by_hash(self, current_session):
        """
        @:returns dict(url_hash) = list(urls)
        """
        raw_data = self.urls.find({"session": current_session, "visited": False})
        result = {}
        for url in raw_data:
            tmp = self._parse_url_from_db_withou_abstract_url(url)
            tmp.url_structure = self.get_url_structure_from_db(current_session, tmp.url_hash)
            if tmp.url_hash in result:
                result[tmp.url_hash].append(tmp)
            else:
                result[tmp.url_hash] = [tmp]
        return result

    def _parse_url_from_db_withou_abstract_url(self, url):
        result = Url(url['url'], url['depth_of_finding'])
        return result
    """
    def _parse_url_from_db(self, url):
        result = Url(url['url'], url['depth_of_finding'])
        result.abstract_url = url["abstract_url"]
        return result
    """
    def get_urls_from_db_to_hash(self, current_session, url_hash):
        urls = self.urls.find({"session": current_session, "url_hash": url_hash})
        result = []
        url_description = self.get_url_structure_from_db(current_session, url_hash)
        for url in urls:
            url = self._parse_url_from_db(url)
            url.url_description = url_description
            result.append(url)
        return result

    def visit_url(self, current_session, url, webpage_id, response_code, redirected_to=None):
        search_doc = {}
        try:
            search_doc['url'] = url.toString()
        except AttributeError:
            search_doc['url'] = url
        search_doc['session'] = current_session
        update_doc = {'response_code': response_code, 'visited': True, 'page_id': webpage_id,
                      'redirected_to': redirected_to}
        self.urls.update(search_doc, {"$set": update_doc})

    def count_visited_urls_per_hash(self, current_session, url_hash):
        all_urls = self.urls.find({"session": current_session, "url_hash": url_hash, "visited": True})
        counter = 0
        for url in all_urls:
            if url['response_code'] > 100:
                counter += 1
        return counter


    def get_url_to_id(self, current_session, id):
        result = self.urls.find_one({"session":current_session, "page_id": id})
        if result is None:
            return None
        return result['url']
             
    def insert_page_into_db(self, current_session, web_page):
        for clickable in web_page.clickables:
            self._insert_clickable_into_db(current_session, web_page.id, clickable)
        for form in web_page.forms:
            self.insert_form(current_session, form, web_page.id)
        
        document = self._create_webpage_doc(web_page, current_session)
        document['ajax_requests'] = []
        document['session'] = current_session
        self.pages.save(document)

    def get_all_pages(self, current_session):
        results = []
        pages = self.pages.find({"session": current_session})
        for page in pages:
            results.append(self._get_web_page_from_db(current_session=current_session, page=page))
        return results

    def get_webpage_to_url_from_db(self, current_session, url):
        return self._get_web_page_from_db(current_session, url=url)

    def get_webpage_to_id_from_db(self, current_session, id):
        return self._get_web_page_from_db(current_session, page_id=id)
        
    def _get_web_page_from_db(self, current_session, page_id= None, url= None, page= None):
        if page is None:
            if page_id is not None:
                page = self.pages.find_one({"session": current_session,"web_page_id": page_id })
            elif url is not None:
                page = self.pages.find_one({"session": current_session,"url": url})
            else:
                raise AttributeError("You must specifies either page_id or url")
            if page is None:
                return None
        clickables = self.get_all_clickables_to_page_id_from_db(current_session, page['web_page_id'])
        forms = self.get_all_forms_to_page_id_from_db(current_session, page['web_page_id'])
        result = WebPage(page['web_page_id'], page['url'], page['html'], None, page['current_depth'], page['base_url'])
        result.clickables = clickables
        result.forms = forms
        links = []
        for link in page['links']:
            links.append(self._parse_link_from_db(link))
        result.links = links
        timemimg_requests = []
        for request in page['timing_requests']:
            timemimg_requests.append(self.get_asyncrequest_to_id(current_session, request))
        result.timing_requests = timemimg_requests
        ajax = []
        for request in page['ajax_requests']:
            ajax.append(self.get_asyncrequest_to_id(current_session, request))
        result.ajax_requests = ajax
        return result

    def insert_asyncrequest(self, current_session, ajax_request, web_page_id):
        url_doc = {"url": ajax_request.url.complete_url, "abstract_url": ajax_request.url.abstract_url, "url_hash": ajax_request.url.url_hash}
        structure_doc = {}
        structure_doc['request_hash'] = ajax_request.request_hash
        structure_doc["session"] = current_session
        structure_doc['parameters'] = ajax_request.request_structure.parameters
        previous_doc = self.async_request_structure.find_one({"session": current_session, "request_hash": ajax_request.request_hash})
        if previous_doc is not None:
            structure_doc["_id"] = previous_doc['_id']
        res = self.async_request_structure.save(structure_doc)

        doc = {}
        doc["request_hash"] = ajax_request.request_hash
        doc["url"] = url_doc
        doc["method"] = ajax_request.method
        doc["session"] = current_session
        try:
            trigger_id = self.clickables.find_one({"session": current_session, "dom_address" : ajax_request.trigger.dom_address, "web_page_id": web_page_id, "event": ajax_request.trigger.event})
            trigger_id = trigger_id["_id"]
            doc["trigger"] = trigger_id
        except AttributeError:
            try:
                doc['event'] = ajax_request.event
            except AttributeError:
                logging.debug("This should never happen...")
        except TypeError:
            find_string = "session: " + str(current_session) + " - dom_address: " + str(ajax_request.trigger.dom_address) + " - web_page_id: " + str(web_page_id) + " - event: "+ (ajax_request.trigger.event)
            logging.debug("Try to find: {}".format(find_string))
        doc['parameters'] = ajax_request.parameters
        return self.async_requests.save(doc)

    def get_asyncrequest_to_id(self, current_session, async_id):
        raw_data = self.async_requests.find_one({"session": current_session, "_id": async_id})
        if raw_data is None:
            return None
        raw_structure = self.async_request_structure.find_one({"session": current_session, "request_hash": raw_data['request_hash']})
        structure = AsyncRequestStructure(raw_structure['request_hash'], raw_structure['parameters'])
        url = Url(raw_data['url']['url'])
        url.abstract_url = raw_data['url']['abstract_url']
        if "event" in raw_data:
            tmp = TimingRequest(raw_data['method'], url, None, raw_data['event'], parameters=raw_data['parameters'])
            tmp.request_structure = structure
        else:
            trigger = self.clickables.find_one({"_id": raw_data['trigger']})
            trigger = self._parse_clickable_from_db_to_model(trigger)
            tmp = AjaxRequest(raw_data['method'], url, trigger, parameters=raw_data['parameters'])
            tmp.request_structure = structure
        return tmp

    
    def _parse_clickable_from_db_to_model(self, clickable):
        c = Clickable(clickable['event'], clickable['tag'], clickable['dom_address'], clickable['html_id'], clickable['html_class'], clickable['clickable_depth'], clickable['function_id'])
        c.clicked = clickable['clicked']
        c.clickable_type = self._num_to_clickable_type(clickable['clickable_type'])
        c.links_to = clickable['links_to']
        c.clickable_depth = clickable['clickable_depth']
        return c
        
    def _insert_clickable_into_db(self, current_session , web_page_id, clickable):
        document = {}
        document["event"]= clickable.event
        document["tag"] = clickable.tag
        document["html_class"] = clickable.html_class
        document["html_id"] = clickable.id
        document["dom_address"] = clickable.dom_address
        document["links_to"] = clickable.links_to
        document["clicked"] = clickable.clicked
        document["clickable_type"] = self._clickable_type_to_num(clickable.clickable_type)
        document["web_page_id"] = web_page_id
        document["function_id"] = clickable.function_id
        document["clickable_depth"] = clickable.clickable_depth
        if hasattr(clickable, "random_char"):
            document['random_char'] = clickable.random_char  
        document['session'] = current_session
        self.clickables.save(document)
        
    def insert_delta_page_into_db(self, current_session, delta_page):
        for clickable in delta_page.clickables:
            self._insert_clickable_into_db(current_session, delta_page.id, clickable)
        for form in delta_page.forms:
            self.insert_form(current_session, form, delta_page.id)
            
        document = self._create_webpage_doc(delta_page, current_session)
        clickable_id = self.clickables.find_one({"session" : current_session, "web_page_id": delta_page.parent_id, "dom_address":delta_page.generator.dom_address, "event":delta_page.generator.event})
        clickable_id = clickable_id["_id"]
        document['generator'] = clickable_id
        generator_request_doc = []
        for r in delta_page.generator_requests:
            generator_request_doc.append(self.insert_asyncrequest(current_session, r, delta_page.parent_id))
        document["generator_requests"] = generator_request_doc
        
        document['delta_depth'] = delta_page.delta_depth
        document['parent_id'] = delta_page.parent_id
        ajax_request_docs = []
        for ajax in delta_page.ajax_requests:
            ajax_request_docs.append(self.insert_asyncrequest(current_session, ajax, delta_page.id))
        document["ajax_requests"] = ajax_request_docs
        document['session'] = current_session
        self.delta_pages.save(document)
    
    def get_delta_page_to_id(self, current_session, page_id):
        page = self.delta_pages.find_one({"session": current_session,"web_page_id":page_id })
        if page is None:
            return None
        result = self._parse_delta_page_from_db(current_session, page)
        return result
        
    def _create_webpage_doc(self, web_page, current_session):
        document = {}
        document["web_page_id"] = web_page.id
        document["url"] = web_page.url
        document["html"] = web_page.html
        document["links"] = []
        for link in web_page.links:
            document["links"].append(self._parse_link_to_db_doc(link))
        timeming_requests_doc = []
        for timing_request in web_page.timing_requests:
            timeming_requests_doc.append(self.insert_asyncrequest(current_session, timing_request, web_page.id))
        document['timing_requests'] = timeming_requests_doc
        document["current_depth"] = web_page.current_depth
        document['base_url'] = web_page.base_url
        return document
    
    def insert_form(self, current_session, form, page_id):
        form_hash = form.get_hash()
        result = self.forms.find_one({"form_hash": form_hash, "session": current_session, "web_page_id": page_id})
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
        action_doc = {"url": form.action.complete_url, "abstract_url": form.action.abstract_url, "url_hash": form.action.url_hash}
        form_doc["action"] = action_doc
        form_doc["dom_address"] = form.dom_address
        param_doc = []
        for parameter in form.parameter:
            param_doc.append(self._parse_form_parameter_to_db_doc(parameter))
        form_doc['parameters'] = param_doc
        form_doc['session'] = current_session
        form_doc['form_hash'] = form_hash
        self.forms.save(form_doc)

    def _parse_link_to_db_doc(self, link):
        res = {}
        url = {"url": link.url.complete_url, "abstract_url": link.url.abstract_url, "url_hash": link.url.url_hash, "depth_of_finding": link.url.depth_of_finding}
        res['url'] = url
        res['dom_address'] = link.dom_address
        res['html_id'] = link.html_id
        res['html_class'] = link.html_class
        return res
    
    def _parse_link_from_db(self, link):
        url = Url(link['url']['url'])
        url.abstract_url = link['url']['abstract_url']
        url.depth_of_finding = link['url']['depth_of_finding']
        result = Link(url, link['dom_address'], link['html_id'], link['html_class'])
        return result
    
    def _parse_form_parameter_to_db_doc(self, form_parameter):
        param = {}
        param["tag"] = form_parameter.tag
        param["name"] = form_parameter.name
        param["values"] = form_parameter.values
        param["input_type"] = form_parameter.input_type
        return param
        
    def set_clickable_clicked(self, current_session,web_page_id, clickable_dom_address, clickable_event, clickable_depth = None ,clickable_type = None, links_to=None):
        search_doc = {}
        set_doc = {}
        
        search_doc["web_page_id"] = web_page_id
        search_doc["dom_address"] = clickable_dom_address
        search_doc["event"] = clickable_event
        search_doc['session'] = current_session
        
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
    
    def set_clickable_ignored(self, current_session, web_page_id, clickable_dom_address, clickable_event, clickable_depth = None, clickable_type = None):
        search_doc = {}
        set_doc = {}
        
        search_doc["web_page_id"] = web_page_id
        search_doc["dom_address"] = clickable_dom_address
        search_doc["event"] = clickable_event
        search_doc['session'] = current_session
        
        if clickable_type is not None:
            clickable_type = self._clickable_type_to_num(clickable_type)
            set_doc["clickable_type"] = clickable_type
        
        if clickable_depth is not None:
            set_doc['clickable_depth'] = clickable_depth
            
        set_doc["clicked"] = "False"
        set_doc = {"$set": set_doc}
        result = self.clickables.update(search_doc, set_doc)
        return result
    
    def extend_ajax_requests_to_webpage(self, current_session, webpage, ajax_requests):
        ajax_requests_doc = []
        for r in ajax_requests:
            ajax_requests_doc.append(self.insert_asyncrequest(current_session, r, webpage.id))
        if not hasattr(webpage, 'parent_id'):
            result = self.pages.update({"web_page_id": webpage.id, "session":current_session}, { "$addToSet" : {"ajax_requests": {"$each": ajax_requests_doc}}})
        else:
            result = self.delta_pages.update({"web_page_id": webpage.id, "session":current_session}, { "$addToSet" : {"ajax_requests": {"$each": ajax_requests_doc}}})
        
        
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
    
    def get_all_clickables_to_page_id_from_db(self, current_session, page_id):
        clickables = self.clickables.find({"web_page_id": page_id, "session": current_session})
        result = []
        for clickable in clickables:
            c = Clickable(clickable['event'], clickable['tag'], clickable['dom_address'], clickable['html_id'], clickable['html_class'], clickable_depth=clickable['clickable_depth'], function_id=clickable['function_id'])
            c.links_to = clickable['links_to']
            c.clickable_type = self._num_to_clickable_type(clickable['clickable_type'])
            c.clicked = clickable['clicked']
            result.append(c)
        return result
    
    def get_all_forms_to_page_id_from_db(self, current_session, page_id):
        forms = self.forms.find({"web_page_id" : page_id, "session": current_session})
        result = []
        for form in forms:
            result.append(self._parse_form_from_db(form))
        return result

    def _parse_form_from_db(self, form):
        parameters = []
        for p in form['parameters']:
            form_input = FormInput(p['tag'], p['name'], p['input_type'], p['values'])
            parameters.append(form_input)
        action = Url(form['action']["url"])
        action.abstract_url = form['action']["abstract_url"]
        return HtmlForm(parameters, action, form['method'], form["dom_address"])
    
    def get_all_crawled_deltapages_to_url_from_db(self, current_session, url):
        pages = self.delta_pages.find({"url":url, "session":current_session})
        result = []
        for page in pages:
            result.append(self._parse_delta_page_from_db(current_session, page))
        return result
            
    def _parse_delta_page_from_db(self, current_session, page):
        clickables = self.get_all_clickables_to_page_id_from_db(current_session, page['web_page_id'])
        forms = self.get_all_forms_to_page_id_from_db(current_session, page['web_page_id'])
        generator = self.clickables.find_one({"_id": page['generator']})
        generator = self._parse_clickable_from_db_to_model(generator)
        generator_requests = []
        for g in page['generator_requests']:
            generator_requests.append(self.get_asyncrequest_to_id(current_session, g))
        result = DeltaPage(page['web_page_id'], page['url'], page['html'], None, page['current_depth'], generator, page['parent_id'], page['delta_depth'])
        links = []
        for link in page['links']:
            links.append(self._parse_link_from_db(link))
        result.links = links
        result.forms = forms
        result.clickables = clickables
        result.generator_requests = generator_requests
        return result

    def insert_url_structure_into_db(self, current_session, url_description):
        search_doc = {"hash": url_description.url_hash}
        result = self.url_descriptions.find_one({"session": current_session, "url_hash": url_description.url_hash})
        document = {}
        if result is not None:
            document["_id"] = result["_id"]
        document["path"] = url_description.path
        document["parameters"] = url_description.parameters
        document["url_hash"] = url_description.url_hash
        document["session"] = current_session
        result = self.url_descriptions.save(document)

    def get_url_structure_from_db(self, current_session, url_hash):
        result = self.url_descriptions.find_one({"session": current_session, "url_hash": url_hash})
        if result is None:
            return None
        return UrlStructure(result['path'], result["parameters"], result['url_hash'])

    def url_exists(self, current_session, url):
        try:
            search_url = url.toString()
        except AttributeError:
            search_url = url
        return self.urls.find({"url": search_url, "session":current_session}).count() > 0

    def write_cluster(self, current_session, url_hash, clusters):
        self.clusters.remove({"session": current_session, "url_hash": url_hash})
        self.clusters.save({"session": current_session, "url_hash": url_hash, "clusters": clusters})

    def get_clusters(self, current_session, url_hash):
        result = self.clusters.find_one({"session": current_session, "url_hash": url_hash})
        try:
            return result["clusters"]
        except TypeError:
            return None

    def get_all_url_structures(self, current_session):
        raw_data = self.url_descriptions.find({"session": current_session})
        result = []
        for url_structure in raw_data:
            result.append(UrlStructure(url_structure['path'], url_structure["parameters"], url_structure['url_hash']))
        return result

    def get_all_visited_urls(self, current_session):
        raw_data = self.urls.find({"session": current_session, "visited": True})
        result = []
        for url in raw_data:
            if url["response_code"] == 200:
                result.append(self._parse_url_from_db(url))
        return result

    def get_one_visited_url_per_structure(self, current_session):
        raw_data = self.urls.find({"session": current_session, "visited": True})
        result = []
        seen_structures = []
        for url in raw_data:
            if url["response_code"] == 200:
                tmp = self._parse_url_from_db_withou_abstract_url(url)
                if tmp.url_hash not in seen_structures:
                    result.append(tmp)
                    seen_structures.append(tmp.url_hash)
        return result

    def insert_attack_result(self, current_session, result, attack_url):
        doc = {"session": current_session, "attack_url": attack_url, "result": result.value}
        self.attack.save(doc)

    def get_asyncrequest_structure(self, current_session, structure_hash= None):
        if structure_hash is not None:
            raw_data = self.async_request_structure.find_one({"session": current_session, "request_hash": structure_hash})
            if raw_data is None:
                return None
            return AsyncRequestStructure(raw_data['request_hash'], raw_data['parameters'])
        else:
            return None
            #TODO: Implement if I need all

    def get_all_get_forms(self, current_session):
        raw_data = self.forms.find({"session": current_session, "method": "get"})
        result = []
        for form in raw_data:
            tmp = self._parse_form_from_db(form)
            if tmp not in result:
                result.append(tmp)
        return result

    def _exclude_dupplicates_forms(self, forms):
        result = []
        for form in forms:
            already_in = False
            for res in result:
                if self._form_paramters_equal(form.parameter, res.parameter) and form.action.complete_url == res.action.complete_url:
                    already_in = True
                    break
            if not already_in:
                result.append(form)
        return result

    def get_one_form_per_destination(self, current_session):
        all_forms = self.get_all_get_forms(current_session)
        all_forms = self._exclude_dupplicates_forms(all_forms)
        return all_forms

    def _form_paramters_equal(self, p1, p2):
        for param in p1:
            is_in = False
            for param2 in p2:
                if param.input_type == param2.input_type and param.name == param2.name and param.tag == param2.tag:
                    is_in = True
                    break
            if not is_in:
                return False
        return True

    def num_of_ignored_urls(self, current_session, url_hash):
        return self.urls.find({"url_hash": url_hash, "session": current_session, "response_code": 0}).count()


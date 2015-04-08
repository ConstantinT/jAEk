"""

This Class is responsible for storage related things

"""
from database.database import Database
from models.clickabletype import ClickableType


class PersistenceManager(object):
    
    def __init__(self, user):
        self._database = Database(user.username)
        self._database.insert_user_into_db(user)
        self._web_page_cache = []
        self._deltapage_cache = []
        self._current_session = None
        self.MAX_CACHE_SIZE = 0
        self._current_session = user.session
        
    def store_web_page(self, web_page):
        if self.MAX_CACHE_SIZE > 0:
            if len(self._web_page_cache) + 1 > self.MAX_CACHE_SIZE:
                del self._web_page_cache[-1]
            self._web_page_cache.insert(0, web_page)
        self._database.insert_page_into_db(self._current_session, web_page)
    
    def get_page_to_id(self, page_id):
        page = self.get_web_page_to_id(page_id)
        if page is not None:
            return page
        page = self.get_delta_page_to_id(page_id)
        if page is not None:
            return page
        return None
    
    def store_delta_page(self, delta_page):
        if self.MAX_CACHE_SIZE > 0:
            if len(self._deltapage_cache) +1 > self.MAX_CACHE_SIZE:
                del self._deltapage_cache[-1]
            self._deltapage_cache.insert(0, delta_page)
        self._database.insert_delta_page_into_db(self._current_session, delta_page)

    def get_page_to_url(self, url):
        try:
            url = url.toString()
        except AttributeError:
            url = url
        
        return self._database.get_webpage_to_url_from_db(self._current_session, url)
    
    def get_web_page_to_id(self, page_id):
        for page in self._web_page_cache:
            if page_id == page.id:
                return page
        return self._database.get_webpage_to_id_from_db(self._current_session, page_id)
            
    
    def get_delta_page_to_id(self, delta_page_id):
        for page in self._deltapage_cache:
            if delta_page_id == page.id:
                return page
            
        return self._database.get_delta_page_to_id(self._current_session, delta_page_id)

    def url_exists(self, url):
        return self._database.url_exists(self._current_session, url)
    
    def get_next_url_for_crawling(self):
        return self._database.get_next_url_for_crawling(self._current_session)

    def get_all_unvisited_urls_sorted_by_hash(self):
        return self._database.get_all_unvisited_urls_sorted_by_hash(self._current_session)
    
    def insert_url_into_db(self, url):
        self._database.insert_url_into_db(self._current_session, url)
    
    def insert_redirected_url(self, url):
        self._database.insert_url_into_db(self._current_session, url, is_redirected_url=True)
        
    def visit_url(self, url, webpage_id, response_code, redirected_to = None):
        self._database.visit_url(self._current_session, url, webpage_id, response_code, redirected_to)
    
    def extend_ajax_requests_to_webpage(self, webpage, ajax_reuqests):
        self._database.extend_ajax_requests_to_webpage(self._current_session, webpage, ajax_reuqests)
    
    
    def get_all_crawled_delta_pages(self, url=None):
        return self._database.get_all_crawled_deltapages_to_url_from_db(self._current_session, url)
    
    
    def update_clickable(self, web_page_id, clickable):
        if clickable.clickable_type == ClickableType.IgnoredByCrawler or clickable.clickable_type == ClickableType.UnsupportedEvent:
            self._database.set_clickable_ignored(self._current_session, web_page_id, clickable.dom_address, clickable.event, clickable.clickable_depth, clickable.clickable_type)
        else:
            self._database.set_clickable_clicked(self._current_session, web_page_id, clickable.dom_address, clickable.event, clickable.clickable_depth, clickable.clickable_type, clickable.links_to)

    def get_url_structure(self, hash):
        return self._database.get_url_structure_from_db(self._current_session, hash)

    def insert_url_structure(self, url_description):
        self._database.insert_url_structure_into_db(self._current_session, url_description)

    def get_all_pages(self):
        return self._database.get_all_pages(self._current_session)

    def get_url_structure_to_hash(self, url_hash):
        return self._database.get_url_structure_from_db(self._current_session,url_hash)

    def insert_url_structure_into_db(self, url_description):
        self._database.insert_url_structure_into_db(self._current_session, url_description)

    def get_url_to_id(self, id):
        return self._database.get_url_to_id(self._current_session, id)

    def write_clusters(self, url_hash, clusters):
        self._database.write_cluster(self._current_session, url_hash, clusters)

    def get_clusters(self, url_hash):
        return self._database.get_clusters(self._current_session, url_hash)

    def count_visited_url_per_hash(self, url_hash):
        return self._database.count_visited_urls_per_hash(self._current_session, url_hash)

    def get_all_url_structures(self):
        return  self._database.get_all_url_structures(self._current_session)

    def get_all_visited_urls(self):
        return self._database.get_all_visited_urls(self._current_session)

    def get_one_visited_url_per_structure(self):
        return self._database.get_one_visited_url_per_structure(self._current_session)

    def insert_attack_result(self, result, attack_url):
        self._database.insert_attack_result(self._current_session, result, attack_url)

    def get_asyncrequest_structure(self, structure_hash=None):
        return self._database.get_asyncrequest_structure(self._current_session, structure_hash)
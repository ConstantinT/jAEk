from models.url import Url
from utils.utils import calculate_similarity_between_pages

__author__ = 'constantin'

CLUSTER_THRESHOLD = .7

class ClusterManager():
    """
    A cluster is a collection of similar pages, defined through a cluster function
    """

    def __init__(self, persistence_manager):
        self._clusters = {} #A dictionary containing the clusters => List of web_page_ids
        self._persistence_manager = persistence_manager

    @property
    def get_clusters(self):
        return self._clusters

    def get_cluster(self, url_description):
        try:
            return self._clusters[url_description].values()
        except:
            raise KeyError("No cluster with that id found")

    def add_new_cluster(self, web_page_id= None, web_page=None):
        if web_page is not None:
            web_page_url = web_page.url
            web_page_url = Url(web_page_url)
            web_page_id = web_page.id
        elif web_page_id is not None:
            web_page_url = self._persistence_manager.get_web_page_to_id(web_page_id).url
            web_page_url = Url(web_page_url)
        else:
            raise AttributeError("Need to specifie web_page_id or web_page")
        web_page_url.url_description = self._persistence_manager.get_url_description_to_hash(web_page_url.url_hash)
        self._clusters[web_page_url.url_description] = [web_page_id]

    def add_to_cluster(self, url_description, web_page_id):
        try:
            self._clusters[url_description].append(web_page_id)
        except:
            raise KeyError("No cluster found with this id")

    def add_to_nearest_cluster(self, web_page):
        if len(self._clusters) == 0: #We have no cluster, so add as first
            self.add_new_cluster(web_page=web_page)
            return
        nearest_cluster = (0, 0) # id, similarity value
        for url_description in self._clusters:
            similarity = 0.0
            for web_page_id in self._clusters[url_description]:
                page = self._persistence_manager.get_web_page_to_id(web_page_id)
                similarity += calculate_similarity_between_pages(web_page, page)
            similarity /= len(self._clusters[url_description])
            if similarity > nearest_cluster[1]:
                nearest_cluster = (url_description, similarity)
        if nearest_cluster[1] > CLUSTER_THRESHOLD:
            self.add_to_cluster(nearest_cluster[0], web_page_id=web_page.id)
        else:
            self.add_new_cluster(web_page=web_page)








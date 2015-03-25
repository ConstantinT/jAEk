
import matplotlib.pyplot as plt
import networkx
from models.url import Url
from utils.utils import calculate_similarity_between_pages

__author__ = 'constantin'

CLUSTER_THRESHOLD = .8

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

    def add_to_webpage_to_cluster(self, web_page):
        url = Url(web_page.url)
        if not url.url_hash in self._clusters: # it is the first
            self._clusters[url.url_hash] = [[web_page.id]]
            return
        nearest_cluster = (0, 0) # list, similarity value
        for cluster in self._clusters[url.url_hash]:  # A cluster is a simple list of web_page_ids
            average_cluster_similarity = 0
            for webpage_id in cluster:
                page = self._persistence_manager.get_web_page_to_id(webpage_id)
                similarity = calculate_similarity_between_pages(web_page, page)
                average_cluster_similarity += similarity
            average_cluster_similarity = average_cluster_similarity / len(cluster)
            if average_cluster_similarity > nearest_cluster[1]:
                nearest_cluster = (cluster, average_cluster_similarity)
        if nearest_cluster[1] > CLUSTER_THRESHOLD:
            nearest_cluster[0].append(web_page.id)
        else:
            self._clusters[url.url_hash].append([web_page.id]) # If it is here, then we must at a new list to the list of clusters





    def draw_clusters(self):
        G = networkx.Graph()
        all_clusters = self._clusters.values()
        for different_clusters in all_clusters:
            for cluster in different_clusters:
                for page_id in cluster:
                    url = self._persistence_manager.get_url_to_id(page_id)
                    G.add_node(page_id, url=url)
                edges = []
                for i in range(len(cluster)):
                    for j in range(i+1, len(cluster)):
                        edges.append((cluster[i], cluster[j]))
                G.add_edges_from(edges)
        labels=dict((n,d['url']) for n, d in G.nodes(data=True))
        networkx.draw_networkx(G, labels=labels)
        plt.show()












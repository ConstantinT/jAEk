import itertools
import logging
from copy import deepcopy
import matplotlib.pyplot as plt
import networkx
from models.cluster import Cluster
from models.url import Url
from utils.utils import calculate_similarity_between_pages
from sklearn.neighbors import NearestNeighbors
from sklearn.neighbors import DistanceMetric

__author__ = 'constantin'

CLUSTER_THRESHOLD = .8

class ClusterManager():
    """
    A cluster is a collection of similar pages, defined through a cluster function
    """

    def __init__(self, persistence_manager):
        self._clusters = {} #A dictionary containing the clusters => List of web_page_ids
        self._persistence_manager = persistence_manager
        self._similarity_cache = {} #Stores in a tripple: List(ids), result

    @property
    def get_clusters(self):
        return self._clusters

    def get_cluster(self, url_description):
        try:
            return self._clusters[url_description].values()
        except:
            raise KeyError("No cluster with that id found")

    def add_webpage_to_cluster(self, webpage):
        url = Url(webpage.url)
        clusters = self._persistence_manager.get_clusters(url.url_hash)
        if clusters is None:
            #self._clusters[url.url_hash] = [webpage.id]
            self._persistence_manager.write_clusters(url.url_hash, [webpage.id])
        else:
            tmp = []
            for c in clusters:
                if isinstance(c, list):
                    tmp.extend(c)
                else:
                    tmp.append(c)
            tmp.append(webpage.id)
            cluster = self.hierarchical_clustering(tmp, 0.2)
            self._persistence_manager.write_clusters(url.url_hash, cluster)


    def hierarchical_clustering(self, clusters, threshold):
        result = []
        rest_clusters = clusters
        while len(rest_clusters) > 1:
            combinations_of_clusters = list(itertools.combinations(rest_clusters, 2))
            distances = []
            for combi in combinations_of_clusters:
                distance = self.calculate_minimum_distance(combi[0], combi[1])
                distances.append((distance, combi[0], combi[1]))
            #distances = sorted(distances, key=lambda x: x[0])
            min_distance = min(distances, key=lambda x: x[0])
            if min_distance[0] > threshold:
                break
            else:
                rest_clusters.remove(min_distance[1])
                rest_clusters.remove(min_distance[2])
                if isinstance(min_distance[1], int):
                    a = min_distance[1],
                else:
                    a = min_distance[1]
                if isinstance(min_distance[2], int):
                    b = min_distance[2],
                else:
                    b = min_distance[2]
                new_cluster = a + b
                rest_clusters.append(new_cluster)
        return rest_clusters

    def calculate_minimum_distance(self, cluster1, cluster2):
        if isinstance(cluster1, int):
            cluster1 = [cluster1]
        else:
            cluster1 = list(cluster1)
        if isinstance(cluster2, int):
            cluster2 = [cluster2]
        else:
            cluster2 = list(cluster2)
        all_nodes =  cluster1 +  cluster2
        all_combinations = list(itertools.combinations(all_nodes, 2))
        distances = []
        for combi in all_combinations:
            if combi[0] in cluster1 and combi[1] in cluster1 or combi[0] in cluster2 and combi[1] in cluster2:
                continue
            distance = self.calculate_distance(combi[0], combi[1])
            distances.append((combi[0], combi[1], distance))
        min_distance = min(distances, key=lambda x: x[2])
        return min_distance[2]

    def calculate_distance(self, x, y):
        name = self.get_similarity_identifier(x, y)
        if name in self._similarity_cache:
            result = self._similarity_cache[name]
        else:
            page_x = self._persistence_manager.get_web_page_to_id(x)
            page_y = self._persistence_manager.get_web_page_to_id(y)
            result = calculate_similarity_between_pages(page_x, page_y)
            self._similarity_cache[name] = result
        return 1 - result

    def get_similarity_identifier(self, x, y):
        name = (x, y)
        name = sorted(name)
        return str(name[0])+"$"+str(name[1])

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







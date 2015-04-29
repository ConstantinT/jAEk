import itertools
import logging
from copy import deepcopy
from models.url import Url
from utils.utils import calculate_similarity_between_pages


__author__ = 'constantin'

CLUSTER_THRESHOLD = .2

class ClusterManager():
    """
    A cluster is a collection of similar pages, defined through a cluster function
    """

    def __init__(self, persistence_manager):
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
            new_clusters = self.hierarchical_clustering(tmp, CLUSTER_THRESHOLD)
            for c in new_clusters:
                if isinstance(c, int): # Konvert integer to list, so mongo store all seperate single clusters in its own lists.
                    new_clusters.remove(c)
                    new_clusters.insert(0, [c])
            self._persistence_manager.write_clusters(url.url_hash, new_clusters)


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
        all_nodes =  cluster1 + cluster2
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
            result = calculate_similarity_between_pages(page_x, page_y, verbose=True)
            self._similarity_cache[name] = result
        return 1 - result

    def get_similarity_identifier(self, x, y):
        name = (x, y)
        name = sorted(name)
        return str(name[0])+"$"+str(name[1])

    def calculate_cluster_per_visited_urls(self, url_hash):
        try:
            return self.num_of_clusters(url_hash) / self.num_of_visited_urls(url_hash)
        except ZeroDivisionError:
            return 1.0

    def num_of_clusters(self, url_hash):
        clusters = self._persistence_manager.get_clusters(url_hash)
        if clusters is not None:
            return len(clusters)
        return 1.0

    def num_of_visited_urls(self, url_hash):
        return self._persistence_manager.count_visited_url_per_hash(url_hash)

    def need_more_urls_of_this_type(self, url_hash):
        return self.calculate_cluster_per_visited_urls(url_hash) > CLUSTER_THRESHOLD







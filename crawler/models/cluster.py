import itertools
from copy import deepcopy

__author__ = 'constantin'


class Cluster():


    def __init__(self, ids, cluster_manager):
        self.clustroid = None
        self.cluster = ids
        self._cluster_manager = cluster_manager
        if len(ids) > 1:
            self.set_new_centroid()
            self.average_similarity = self._cluster_manager.get_average_distance_between(ids)
            diameters = []
            all_ids = self.get_all_ids()
            all_pairs = list(itertools.combinations(all_ids, 2))
            for pair in all_pairs:
                diameters.append(self._cluster_manager.get_average_distance_between(pair))
            self._diameter = min(diameters) # Smallest similarity
        else:
            self.clustroid = ids[0]
            self.average_similarity = 1.0
            self._diameter = 0
            self.cluster = None

    def set_new_centroid(self):
        average_distance_for_centroid = (1,0) #Average distance, centroid id
        for i in range(len(self.cluster)):
            average_distance = 0
            for j in range(len(self.cluster)):
                if j != i:
                    average_distance += self._cluster_manager.get_average_distance_between([self.cluster[i], self.cluster[j]])
            average_distance /= len((self.cluster)) - 1
            if average_distance < average_distance_for_centroid[0]:
                average_distance_for_centroid = (average_distance, i)
        self.clustroid = self.cluster[average_distance_for_centroid[1]]
        self._average_distance_to_centroid = average_distance_for_centroid[0]
        del(self.cluster[average_distance_for_centroid[1]])

    def get_all_ids(self):
        if self.cluster is not None:
            l = deepcopy(self.cluster)
            l.append(self.clustroid)
        else:
            l = self.clustroid
        return l

    def get_cluster_size(self):
        return len(self.cluster) + 1 #For the centroid








    def check_distance_and_diameter(self, page_id):
        all_ids = self.get_all_ids()
        all_ids.append(page_id)
        average_distance = self._cluster_manager.get_average_distance_between(all_ids)
        diameters = []
        all_pairs = list(itertools.combinations(all_ids, 2))
        for pair in all_pairs:
            diameters.append(self._cluster_manager.get_average_distance_between(pair))
        diameter = min(diameters)
        average_centroid_distance = 0
        all_elements = deepcopy(self.cluster)
        all_elements.append(page_id)
        for page_id in all_elements:
            average_centroid_distance += self._cluster_manager.get_average_distance_between([page_id, self.clustroid])
        average_centroid_distance /= len(all_elements)
        return average_distance, average_centroid_distance, diameter

    def add_new_id(self, page_id):
        self.cluster = self.get_all_ids()
        self.cluster.append(page_id)
        self.set_new_centroid()
        self.average_similarity = self._cluster_manager.get_average_distance_between(self.get_all_ids())
        diameters = []
        all_ids = self.get_all_ids()
        all_pairs = list(itertools.combinations(all_ids, 2))
        for pair in all_pairs:
            diameters.append(self._cluster_manager.get_average_distance_between(pair))
        self._diameter = min(diameters)










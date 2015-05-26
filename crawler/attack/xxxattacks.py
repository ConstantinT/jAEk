import logging
import os
import random
import string


__author__ = 'constantin'


FILENAME = "/xssvectors.txt"
class XSSVectors():

    def __init__(self):
        self.attack_vectors = []
        for line in open(os.path.dirname(os.path.realpath(__file__)) + FILENAME, "r"):
            self.attack_vectors.append(line[:-1])

    def random_string_generator(self, size=6, chars=string.ascii_uppercase + string.digits+string.ascii_lowercase):
        result = ""
        for i in range(size):
            result += random.choice(chars)
        return result

    def random_number_generator(self, size=6):
        i = 1
        max_num = ""
        min_num = "1"
        for i in range(size + 1):
            max_num += "9"
            min_num += "0"
        min_num = min_num[:-1]
        max_num = int(max_num)
        min_num = int(min_num)
        return str(random.randint(min_num, max_num))

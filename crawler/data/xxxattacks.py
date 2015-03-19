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
            self.attack_vectors.append(line)

    def random_generator(self, size=6, chars=string.ascii_uppercase + string.digits+string.ascii_lowercase):
        result = ""
        for i in range(size):
            result += random.choice(chars)
        return result


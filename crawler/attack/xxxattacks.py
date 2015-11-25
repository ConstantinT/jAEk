'''
Copyright (C) 2015 Constantin Tschuertz

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

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

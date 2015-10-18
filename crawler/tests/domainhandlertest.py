Copyright (C) 2015 Constantin Tschürtz

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


from database.databasemanager import DatabaseManager
from models.urlstructure import ParameterType
from utils.domainhandler import DomainHandler
from utils.user import User

__author__ = 'constantin'

import unittest


class DomainHandlerTest(unittest.TestCase):

    def setUp(self):
        self.persistence_manager = DatabaseManager(User("DummyUser", 0))
        self.domain_handler = DomainHandler("example.com", self.persistence_manager)

    def test_a_parameter_calculation(self):
        self.assertEqual(self.domain_handler.calculate_new_url_type(None, "a"), ParameterType.Char)
        self.assertEqual(self.domain_handler.calculate_new_url_type(None, "4"), ParameterType.Digit)
        self.assertEqual(self.domain_handler.calculate_new_url_type(None, "afd"), ParameterType.String)
        self.assertEqual(self.domain_handler.calculate_new_url_type(None, "1.5"), ParameterType.Float)
        self.assertEqual(self.domain_handler.calculate_new_url_type(None, "42342"), ParameterType.Integer)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Digit, "a"), ParameterType.Char)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Digit, "1"), ParameterType.Digit)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Digit, "12"), ParameterType.Integer)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Digit, "42.5"), ParameterType.Float)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Digit, "abc"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Digit, "abc123"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Float, "a"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Float, "1"), ParameterType.Float)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Float, "1.5"), ParameterType.Float)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Float, "abc"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Float, "abc123"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Float, "17"), ParameterType.Float)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Float, "17.5"), ParameterType.Float)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Integer, "a"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Integer, "14"), ParameterType.Integer)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Integer, "14.5"), ParameterType.Float)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Integer, "abc123"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Char, "a"), ParameterType.Char)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Char, "4"), ParameterType.Char)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Char, "14"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Char, "14.5"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Char, "abc"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.Char, "abc123"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.String, "a"), ParameterType.String)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.String, "abc"), ParameterType.String)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.String, "1"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.String, "2.3"), ParameterType.AlphaNumerical)
        self.assertEqual(self.domain_handler.calculate_new_url_type(ParameterType.String, "abc123"), ParameterType.AlphaNumerical)


    def test_b_create_url_function(self):
        url = self.domain_handler.handle_url("http://example.com/test.php?a=5&b=abc")
        url_desc = self.persistence_manager.get_url_structure(url.url_hash)
        self.assertEqual(url_desc.get_parameter_type("b"), ParameterType.String)
        self.assertEqual(url_desc.get_parameter_type("a"), ParameterType.Digit)
        self.assertEqual(url.get_values_to_parameter("a")[0], "5")
        self.assertEqual(url.get_values_to_parameter("b")[0], "abc")


        url = self.domain_handler.handle_url("test.php?a=7&b=abc123", "http://example.com")
        url_desc = self.persistence_manager.get_url_structure(url.url_hash)
        self.assertEqual(url_desc.get_parameter_type("b"), ParameterType.AlphaNumerical)
        self.assertEqual(url_desc.get_parameter_type("a"), ParameterType.Digit)
        self.assertEqual(url.domain, "example.com")
        self.assertEqual(url.path, "/test.php")
        self.assertEqual(url.scheme, "http")
        self.assertEqual(len(url.parameters), 2)
        self.assertEqual(url.get_values_to_parameter("a")[0], "7")
        self.assertEqual(url.get_values_to_parameter("b")[0], "abc123")

        with self.assertRaises(KeyError):
            url.get_values_to_parameter("zzz")



if __name__ == '__main__':
    unittest.main()

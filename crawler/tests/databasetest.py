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
from copy import deepcopy
from database.database import Database
from models.ajaxrequest import AjaxRequest
from models.clickable import Clickable
from models.clickabletype import ClickableType
from models.form import HtmlForm, FormInput
from models.url import Url
from models.webpage import WebPage

__author__ = 'constantin'

import unittest

SESSION = 12345
WEBPAGE_ID = 99
TEST_URL1 = "http://example.com"
TEST_URL2 = "http://example.com/exmaple.php"
TEST_HTML = "<html><head></head><body></body></html>"
CLICKABLE = Clickable("click", "a", "body/div/div/a", id = "Test1", html_class = "Test2", clickable_depth = 243, function_id = "Test3")
WEBPAGE = WebPage(1, url= TEST_URL1, html= TEST_HTML, cookiesjar= None, depth= 24, base_url= TEST_URL2)
AJAXREQUEST = AjaxRequest("GET", TEST_URL1, CLICKABLE, parameters=["test=Test"])


class DataBaseTests(unittest.TestCase):

    def setUp(self):
        self.database = Database("DataBaseUnit")


    def test_url_set_and_get(self):
        url = Url(TEST_URL1, depth_of_finding=3)
        self.database.insert_url_into_db(SESSION, url)
        url2 = self.database.get_next_url_for_crawling(SESSION)
        self.assertEqual(url, url2)
        self.assertEqual(url2.depth_of_finding, 3)

    def test_url_visit(self):
        url1 = Url(TEST_URL1, depth_of_finding=3)
        url2 = Url(TEST_URL2, depth_of_finding=25)

        self.database.insert_url_into_db(SESSION, url1)
        self.database.insert_url_into_db(SESSION, url2)

        url3 = self.database.get_next_url_for_crawling(SESSION)
        self.database.visit_url(SESSION, url3, 25, 200)
        url4 = self.database.get_next_url_for_crawling(SESSION)

        self.assertEqual(url1, url3)
        self.assertEqual(url2, url4)

    def test_url_set(self):
        url1 = Url(TEST_URL1, depth_of_finding=3)
        url2 = Url(TEST_URL2, depth_of_finding=25)

        self.database.insert_url_into_db(SESSION, url1)
        self.assertEqual(self.database.urls.count(), 1)
        self.database.insert_url_into_db(SESSION, url1)
        self.assertEqual(self.database.urls.count(), 1)
        self.database.insert_url_into_db(SESSION, url2)
        self.assertEqual(self.database.urls.count(), 2)


    def test_clickables(self):
        clickable1 = Clickable("click", "a", "body/div/div/a", id = "Test1", html_class = "Test2", clickable_depth = 243, function_id = "Test3")
        self.database._insert_clickable_into_db(SESSION, WEBPAGE_ID, clickable1)

        clickables = self.database.get_all_clickables_to_page_id_from_db(SESSION,WEBPAGE_ID)
        self.assertEqual(len(clickables), 1)
        self.assertEqual(clickable1, clickables[0])
        
        self.database.set_clickable_clicked(SESSION, WEBPAGE_ID, clickable1.dom_address, clickable1.event, clickable_depth=243, clickable_type=ClickableType.CreatesNewNavigatables)

        clickables = self.database.get_all_clickables_to_page_id_from_db(SESSION,WEBPAGE_ID)
        self.assertEqual(len(clickables), 1)
        clickable1.clicked = True
        clickable1.clickable_type = ClickableType.CreatesNewNavigatables
        self.assertEqual(clickable1, clickables[0])

    def test_webpage(self):
        clickable1 = Clickable("click", "a", "body/div/div/a", id = "Test1", html_class = "Test2", clickable_depth = 243, function_id = "Test3")
        web_page = WebPage(1, url= TEST_URL1, html= TEST_HTML, cookiesjar= None, depth= 24, base_url= TEST_URL2)
        web_page.clickables.extend([clickable1])
        self.database.insert_page_into_db(SESSION, web_page)
        web_page1 = self.database.get_webpage_to_id_from_db(SESSION, 1)
        self.assertEqual(web_page.toString(), web_page1.toString())
        web_page2 = self.database.get_webpage_to_url_from_db(SESSION, TEST_URL1)
        self.assertEqual(web_page.toString(), web_page2.toString())

    def test_form1(self):
        form_input1 = FormInput("INPUT", "Username", input_type="text", values=None)
        form_input2 = FormInput("INPUT", "Password", input_type="password", values=None)
        form = HtmlForm([form_input1,form_input2], TEST_URL1, "POST", dom_address= None)

        self.database.insert_form(SESSION,form, WEBPAGE_ID)
        self.assertEqual(self.database.forms.count(), 1)
        form1 = self.database.get_all_forms_to_page_id_from_db(SESSION,WEBPAGE_ID)
        self.assertEqual(form, form1[0])
        self.assertEqual(form.toString(), form1[0].toString())

    def test_similar_forms(self):
        form_input1 = FormInput("INPUT", "Test1", input_type="text", values=["Thomas"])
        form_input2 = FormInput("INPUT", "Test2", input_type="text", values=["Mueller"])
        form = HtmlForm([form_input1,form_input2], TEST_URL1, "POST", dom_address= None)
        self.database.insert_form(SESSION,form, WEBPAGE_ID)
        self.assertEqual(self.database.forms.count(), 1)

        form_input1 = FormInput("INPUT", "Test1", input_type="text", values=["Edgar"])
        form_input2 = FormInput("INPUT", "Test2", input_type="text", values=["Mueller"])
        form = HtmlForm([form_input1,form_input2], TEST_URL1, "POST", dom_address= None)
        self.database.insert_form(SESSION,form, WEBPAGE_ID)
        self.assertEqual(self.database.forms.count(), 1)

        form_input1 = FormInput("INPUT", "Test1", input_type="text", values=["Thomas, Edgar"])
        form_input2 = FormInput("INPUT", "Test2", input_type="text", values=["Mueller"])
        form = HtmlForm([form_input1,form_input2], TEST_URL1, "POST", dom_address= None)
        self.database.insert_form(SESSION,form, WEBPAGE_ID)
        self.assertEqual(self.database.forms.count(), 1)


        expected_form = HtmlForm([form_input1,form_input2], TEST_URL1, "POST", dom_address= None)
        form1 = self.database.get_all_forms_to_page_id_from_db(SESSION,WEBPAGE_ID)[0]
        self.assertEqual(form1.toString(), expected_form.toString())

    def test_not_similar_forms(self):
        form_input1 = FormInput("INPUT", "Test1", input_type="text", values=["Thomas"])
        form_input2 = FormInput("INPUT", "Test3", input_type="text", values=["Mueller"])
        form = HtmlForm([form_input1,form_input2], TEST_URL1, "POST", dom_address= None)
        self.database.insert_form(SESSION,form, WEBPAGE_ID)
        self.assertEqual(self.database.forms.count(), 1)

        form_input1 = FormInput("INPUT", "Test1", input_type="text", values=["Edgar"])
        form_input2 = FormInput("INPUT", "Test2", input_type="text", values=["Mueller"])
        form = HtmlForm([form_input1,form_input2], TEST_URL1, "POST", dom_address= None)
        self.database.insert_form(SESSION,form, WEBPAGE_ID)
        self.assertEqual(self.database.forms.count(), 2)

    def test_web_page_extend_ajax(self):
        web_page = deepcopy(WEBPAGE)
        clickable = deepcopy(CLICKABLE)
        web_page.clickables.extend([clickable])
        self.database.insert_page_into_db(SESSION, web_page)
        ajax = deepcopy(AJAXREQUEST)
        self.database.extend_ajax_requests_to_webpage(SESSION, web_page, [ajax])

        web_page.ajax_requests = [ajax]
        test_page = self.database.get_webpage_to_url_from_db(SESSION, web_page.url)
        self.assertEqual(web_page.toString(),test_page.toString())
        self.assertEqual(web_page.ajax_requests[0], ajax)



if __name__ == '__main__':
    unittest.main()

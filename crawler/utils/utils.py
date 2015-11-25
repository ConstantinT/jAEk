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
import string
from Cython.Compiler.Options import normalise_encoding_name
from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QNetworkCookie

from models.deltapage import DeltaPage
from models.parametertype import ParameterType


def form_to_dict(form, key_values = None):
    result = {}
    QStr
    for elem in form.parameter:
        if elem.name == "redirect_to": 
            continue
        if elem.name not in key_values:
            result[elem.name] = elem.values
        else: 
            result[elem.name] = key_values[elem.name]    
    return result
             

#substract the page-parameters in the parent-class from the delta-class
def subtract_parent_from_delta_page(parent_page, delta_page):
    result = DeltaPage(delta_page.id, delta_page.url, delta_page.html, cookiesjar=delta_page.cookiejar, depth=delta_page.current_depth, generator=delta_page.generator, parent_id=delta_page.parent_id)
    result.delta_depth = delta_page.delta_depth
    for link in delta_page.links:
        if link not in parent_page.links:
            result.links.append(link)
        
    for d_clickable in delta_page.clickables:
        clickable_is_already_in_main = False
        for m_clickable in parent_page.clickables:
            if d_clickable == m_clickable:
                clickable_is_already_in_main = True
                break
        if clickable_is_already_in_main == False:
                result.clickables.append(d_clickable)
    
    for d_form in delta_page.forms:
        form_is_already_in_main = False
        for m_form in parent_page.forms:
            if two_forms_are_equal(d_form, m_form):
                form_is_already_in_main = True
                break
        if form_is_already_in_main == False:
            result.forms.append(d_form)

    result.ajax_requests = delta_page.ajax_requests # They are just capturing the new one
    return result
    
def transfer_clicked_from_parent_to_delta(parent_page, delta_page):
    for d_clickabe in delta_page.clickables:
        if not d_clickabe.clicked:
            for p_clickable in parent_page.clickables:
                if d_clickabe == p_clickable:
                    d_clickabe.clicked = p_clickable.clicked # If both are equel, transfer the clickstate from parent to child

    return delta_page

def calculate_similarity_between_pages(page1, page2, clickable_weight = 1.0, form_weight = 1.0, link_weight = 1.0, verbose= True):

    if page1.toString() == page2.toString():
        return 1.0

    form_similarity = 0.0
    identical_forms = 0.0
    form_counter = len(page1.forms) + len(page2.forms)
    if form_counter > 0:
        for p1_form in page1.forms:
            is_in_other = False
            for p2_form in page2.forms:
                if two_forms_are_equal(p1_form, p2_form):
                    is_in_other = True
                    break
            if is_in_other:
                identical_forms += 1.0
                form_counter -= 1.0
        form_similarity = identical_forms / form_counter
    else:
        form_weight = 0.0

    link_similarity = 0.0
    identical_links = 0.0
    link_counter = len(page1.links) + len(page2.links)
    if link_counter > 0:
        for p1_link in page1.links:
            is_in_other = False
            for p2_link in page2.links:
                if p1_link.url.abstract_url == p2_link.url.abstract_url:
                    is_in_other = True
                    break
            if is_in_other:
                identical_links += 1.0
                link_counter -= 1.0
        link_similarity = identical_links / link_counter
    else:
        #logging.debug("Linkweight is 0.0")
        link_weight = 0.0

    clickable_similarity = 0.0
    identical_clickables = 0.0
    clickable_counter = len(page1.clickables) + len(page2.clickables)
    if clickable_counter > 0:
        for p1_clickable in page1.clickables:
            is_in_other = False
            for p2_clickable in page2.clickables:
                if two_clickables_are_equal(p1_clickable, p2_clickable):
                    is_in_other = True
                    break
            if is_in_other:
                identical_clickables += 1.0
                clickable_counter -= 1.0
        clickable_similarity = identical_clickables / clickable_counter
    else:
        clickable_weight = 0

    sum_weight = clickable_weight + form_weight + link_weight
    similarity= clickable_weight * clickable_similarity + form_weight * form_similarity + link_weight * link_similarity
    if sum_weight > 0:
        result = similarity / sum_weight
    else:
        result = 1
    if verbose:
        f = open("similarities/" + str(page1.id) + " - " + str(page2.id) + ".txt", "w")
        f.write(page1.toString())
        f.write(" \n \n ======================================================= \n \n")
        f.write(page2.toString())
        f.write("\n \n ====================Result=========================== \n \n")
        f.write("Similarity = " + str(result) + " - Formsimilarity: " + str(form_similarity) + " - Linksimilarity: " + str(link_similarity) + " - Clickablesimilarity: " + str(clickable_similarity))
        f.write("\n Formweight: "+ str(form_weight) + " Formnum: " +str(form_counter) + " - Linkweight: " + str(link_weight) + " Linknum: " + str(link_counter) + " - Clickableweight: " + str(clickable_weight) + " Clickablenum: " + str(clickable_counter) )
        f.close()
        #logging.debug("PageID: " + str(page1.id) + " and PageID: " + str(page2.id) + " has a similarity from: " + str(result))

    return result

def two_clickables_are_equal(c1, c2):
    tmp = c1.event == c2.event and c1.dom_address == c2.dom_address and c1.tag == c2.tag
    if c1.clickable_type is not None and c2.clickable_type is not None:
        tmp = tmp and c1.clickable_type == c2.clickable_type
    return tmp

def two_forms_are_equal(form1, form2):
    return form1.form_hash == form2.form_hash and form1.action.abstract_url == form2.action.abstract_url

def count_cookies(networkaccess_manager, url):
    try:
        url = url.toString()
    except AttributeError:
        url = url
    cookiejar = networkaccess_manager.cookieJar()
    all_cookies = cookiejar.cookiesForUrl(QUrl(url))
    return len(all_cookies)



def calculate_new_parameter_type(current_type, value):
        if current_type is None: # When we see it the first time, then we just set this param to None
            if len(value) == 1:
                if value in string.ascii_lowercase + string.ascii_uppercase + "/":
                    return ParameterType.Char
                elif _is_int(value):
                    return ParameterType.Digit
                elif _is_float(value):
                    return ParameterType.Float
                else:
                    raise ValueError("Len is one but I have not specified a case for: {}".format(value))
            else:
                if _is_int(value):
                    return ParameterType.Integer
                elif _is_float(value):
                    return ParameterType.Float
                elif isinstance(value, str):
                    if _has_number(value):
                        return ParameterType.AlphaNumerical
                    else:
                        return ParameterType.String
                else:
                    raise ValueError("Is ling but not specified...")

        else:
            if current_type == ParameterType.Digit:
                return _handle_digit(value)
            elif current_type == ParameterType.Float:
                return _handle_float(value)
            elif current_type == ParameterType.Char:
                return _handle_char(value)
            elif current_type == ParameterType.Integer:
                return _handle_integer(value)
            elif current_type == ParameterType.String:
                return _handle_string(value)
            else:
                return ParameterType.AlphaNumerical # One time alphanumerical everytime alphanumerical


def _is_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False

def _is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def _has_number(input):
    return any(_is_int(char) or _is_float(char) for char in input)

def _handle_digit(value):
    if len(value) == 1:
        if _is_int(value):
            return ParameterType.Digit
        if _is_float(value):
            return ParameterType.Float
        if value in string.ascii_uppercase + string.ascii_lowercase:
            return ParameterType.Char
    else:
        if _is_int(value):
            return ParameterType.Integer
        if _is_float(value):
            return ParameterType.Float
        else:
            return ParameterType.AlphaNumerical

def _handle_float(value):
    if _is_float(value) or _is_int(value):
            return ParameterType.Float
    if isinstance(value, str):
        return ParameterType.AlphaNumerical
    else:
        raise  ValueError("{}".format(value))


def _handle_char(value):
    if len(value) == 1:
        return ParameterType.Char
    else:
        return ParameterType.AlphaNumerical

def _handle_integer(value):
    if _is_int(value):
        return ParameterType.Integer
    elif _is_float(value):
        return ParameterType.Float
    else:
        return ParameterType.AlphaNumerical

def _handle_string(value):
    if _has_number(value):
        return ParameterType.AlphaNumerical
    else:
        return ParameterType.String

def print_to_file(self, item, filename):
    f = open("result/"+filename, "w")
    f.write(item)
    f.close()
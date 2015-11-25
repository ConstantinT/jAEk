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
from models.clickable import Clickable
from models.link import Link
from models.url import Url
from urllib.parse import urlparse, urljoin

def extract_links(frame, requested_url):
    try:
        requested_url = requested_url.toString()
    except AttributeError:
        requested_url = requested_url
    anchor_tags = frame.findAllElements("a")
    new_links, new_clickables = _extract_new_links_from_links(anchor_tags, requested_url)
    iframes = frame.findAllElements("iframe") + frame.findAllElements("frame")
    new_links = new_links + extract_links_from_iframe(iframes)
    return new_links, new_clickables

def _extract_new_links_from_links(elements, requested_url):
    found_links = []
    new_clickables = []
    if(len(elements) == 0):
        #logging.debug("No links found...")
        return [], []
    else:
        for elem in elements:
            href = elem.attribute("href")
            #logging.debug(str(type(elem)) + " href: " + str(href) + " Tagname: " + str(elem.tagName()))
            if href == "/" or href == requested_url or href == "": #or href[0] == '#':
                continue
            elif "javascript:" in href: #We assume it as clickable
                html_id = elem.attribute("id")
                html_class = elem.attribute("class")
                dom_address = elem.evaluateJavaScript("getXPath(this)")
                event = href
                tag = "a"
                new_clickables.append(Clickable(event, tag, dom_address, html_id, html_class, None, None))
            elif "#" in href:
                html_id = elem.attribute("id")
                html_class = elem.attribute("class")
                dom_address = elem.evaluateJavaScript("getXPath(this)")
                event = "click"
                tag = "a"
                new_clickables.append(Clickable(event, tag, dom_address, html_id, html_class, None, None))
            elif len(href) > 0:
                html_id = elem.attribute("id")
                html_class = elem.attribute("class")
                dom_address = elem.evaluateJavaScript("getXPath(this)")
                url = href
                link = Link(url, dom_address, html_id, html_class)
                found_links.append(link)
            else:
                logging.debug("Elem has attribute href: " + str(elem.attribute("href") + " and matches no criteria"))
    return found_links, new_clickables

def extract_links_from_iframe(elements):
    found_links = []
    if len(elements) == 0:
        return []
    for element in elements:
        src = element.attribute("src")
        html_id = element.attribute("id")
        html_class = element.attribute("class")
        dom_address = element.evaluateJavaScript("getXPath(this)")
        link = Link(src, dom_address, html_id, html_class)
        found_links.append(link)
    return found_links
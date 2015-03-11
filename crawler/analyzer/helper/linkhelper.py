import logging
from models.clickable import Clickable
from models.link import Link
from models.url import Url
from urllib.parse import urlparse, urljoin


class LinkHelper():

    def extract_links(self, frame, requested_url, current_depth):
        elems = frame.findAllElements("a")
        new_links, new_clickables = self._extract_links(elems, requested_url, current_depth)
        return new_links, new_clickables

    def _extract_links(self, elems, requested_url, current_depth):
        found_links = []
        new_clickables = []
        if(len(elems) == 0):
            #logging.debug("No links found...")
            pass
        else:
            for elem in elems:
                href = elem.attribute("href")
                #logging.debug(str(type(elem)) + " href: " + str(href) + " Tagname: " + str(elem.tagName()))
                if href == "/" or href == "#" or href == requested_url or href == "": #or href[0] == '#':
                    continue
                elif "javascript:" in href: #We assume it as clickable
                    html_id = elem.attribute("id")
                    html_class = elem.attribute("class")
                    dom_adress = elem.evaluateJavaScript("getXPath(this)")
                    event = href
                    tag = "a"
                    new_clickables.append(Clickable(event, tag, dom_adress, html_id, html_class, None, None))
                elif len(href) > 1:
                    html_id = elem.attribute("id")
                    html_class = elem.attribute("class")
                    dom_adress = elem.evaluateJavaScript("getXPath(this)")
                    url = href
                    url = Url(url, current_depth)
                    link = Link(url, dom_adress, html_id, html_class)
                    found_links.append(link)
                elif "http://" in href or "https://" in href:
                    continue
                else:
                    logging.debug("Elem has attribute href: " + str(elem.attribute("href") + " and matches no criteria"))
        return found_links, new_clickables
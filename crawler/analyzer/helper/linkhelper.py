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

    f = open("test.txt", "w")
    f.write(frame.toHtml())
    f.close()
    anchor_tags = frame.findAllElements("a")
    new_links, new_clickables = _extract_links(anchor_tags, requested_url)
    return new_links, new_clickables

def _extract_links( elements, requested_url):
    found_links = []
    new_clickables = []
    if(len(elements) == 0):
        #logging.debug("No links found...")
        pass
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
            elif len(href) > 1:
                html_id = elem.attribute("id")
                html_class = elem.attribute("class")
                dom_address = elem.evaluateJavaScript("getXPath(this)")
                url = href
                link = Link(url, dom_address, html_id, html_class)
                found_links.append(link)
            elif "http://" in href or "https://" in href:
                continue
            else:
                logging.debug("Elem has attribute href: " + str(elem.attribute("href") + " and matches no criteria"))
    return found_links, new_clickables
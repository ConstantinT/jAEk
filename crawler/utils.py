'''
Created on 12.11.2014

@author: constantin
'''
import logging
from time import time, sleep
import models
import abstractanalyzer





class Factory():
    
    def form_to_json(self, form, key_values = None):
        result = {}
        for elem in form.parameter:
            if elem.name == "redirect_to": 
                continue
            if elem.name not in key_values:
                result[elem.name] = elem.values
            else: 
                result[elem.name] = key_values[elem.name]    
        return result
             
 
class PageHandler():
    
    """substract the page-parameters in the parent-class from the delta-class"""
    def subtract_parent_from_delta_page(self, parent_page, delta_page):
        result = models.DeltaPage(delta_page.id, delta_page.url, delta_page.html, cookiesjar=delta_page.cookiejar, depth=delta_page.current_depth, generator=delta_page.generator, parent_id=delta_page.parent_id)
        result.delta_depth = delta_page.delta_depth
        for link in delta_page.links:
            if link not in parent_page.links:
                result.links.append(link)
        
        for d_clickable in delta_page.clickables:
            clickable_is_already_in_main = False
            for m_clickable in parent_page.clickables:
                if d_clickable == m_clickable:
                    clickable_is_already_in_main = True
            if clickable_is_already_in_main == False:        
                result.clickables.append(d_clickable)
    
        for d_form in delta_page.forms:
            forms_is_already_in_main = False
            for m_form in parent_page.forms:
                if d_form == m_form:
                    forms_is_already_in_main = True
            if forms_is_already_in_main == False:
                result.forms.append(d_form)
        
        result.ajax_requests = delta_page.ajax_requests # They are just capturing the new one
        return result
    
    def transfer_clicked_from_parent_to_delta(self, parent_page, delta_page):
        for d_clickabe in delta_page.clickables:
            if not d_clickabe.clicked:
                for p_clickable in parent_page.clickables:
                    if d_clickabe == p_clickable:
                        d_clickabe.clicked = p_clickable.clicked # If both are equel, transfer the clickstate from parent to child
                        
        return delta_page
    
    def calculate_similarity_between_pages(self, page1, page2, clickable_weight = 1.0, form_weight = 1.0, link_weight = 1.0):

        if page1.toString() == page2.toString():
            return 1.0
        
        form_similarity = 0.0
        identical_forms = 0.0
        form_counter = len(page1.forms) + len(page2.forms)
        if form_counter > 0:
            for p1_form in page1.forms:
                is_in_other = False
                for p2_form in page2.forms:
                    if p1_form.toString() == p2_form.toString():
                        is_in_other = True
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
                    if p1_link == p2_link:
                        is_in_other = True
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
                    if self.two_clickables_are_equal(p1_clickable, p2_clickable):
                        is_in_other = True
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
        f = open("similarities/" + str(page1.id) + " - " + str(page2.id) + ".txt", "w")
        f.write(page1.toString())
        f.write(" \n \n ======================================================= \n \n")
        f.write(page2.toString())
        f.write("\n \n ====================Ergebniss=========================== \n \n")
        f.write("Similatiry = " + str(result) + " - Formsimilarity: " + str(form_similarity) + " - Linksimilarity: " + str(link_similarity) + " - Clickablesimilarity: " + str(clickable_similarity))
        f.write("\n Formweight: "+ str(form_weight) + " Formnum: " +str(form_counter) + " - Linkweight: " + str(link_weight) + " Linknum: " + str(link_counter) + " - Clickableweight: " + str(clickable_weight) + " Clickablenum: " + str(clickable_counter) )
        f.close()
        logging.debug("PageID: " + str(page1.id) + " and PageID: " + str(page2.id) + " has a similarity from: " + str(result))
        return result
    
    def two_clickables_are_equal(self, c1, c2):
        return c1.event == c2.event and c1.dom_adress == c2.dom_adress and c1.tag == c2.tag #Function_id is no applicable anymore, because of some generic in the method

"""
This Class prepares a page for analyzing... it renders the initial page and removes all <video> because of memory corruption during processing.
"""  
        
class PageRenderer(abstractanalyzer.AbstractAnalyzer):
    def __init__(self, parent, proxy, port, crawl_speed = models.CrawlSpeed.Medium):
        super(PageRenderer, self).__init__(parent,proxy, port, crawl_speed)
        self._loading_complete = False
        f = open("js/lib.js", "r")
        self._lib_js = f.read()
        f.close()
        self._current_event = None
        self._html = None
        self._analyzing_finished = False
        self.element_to_click = None
        self.element_to_click_model = None
        
    def loadFinishedHandler(self, result):
        if not self._analyzing_finished: # Just to ignoring setting of non page....
            self._wait(0.5)
            self._load_finished = True
            
    def render(self, requested_url, html, timeout=10):
        logging.debug("Render page...")
        self._load_finished = False
        self._analyzing_finished = False
        t = 0
        self.mainFrame().setHtml(html)
        while not self._load_finished and t < timeout:
            self._wait(0.1)
            t += 0.1        
        
        if not self._load_finished:
            logging.debug("Renderer timeout...")
        
        
        videos = self.mainFrame().findAllElements("video")
        if len(videos) > 0:
            logging.debug(str(len(videos)) + " Videos found...now removing them")
            for v in videos:
                v.removeFromDocument() 
         
        html = self.mainFrame().toHtml()
       
        self._analyzing_finished = True
        self.mainFrame().setHtml(None)
        return html
    
    def _wait(self, timeout=1):
        """Wait for delay time
        """
        deadline = time() + timeout
        while time() < deadline:
            sleep(0)
            self.app.processEvents()
            
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        #logging.debug("Console(PageBuilder): " + message + " at: " + str(lineNumber))
        pass
    
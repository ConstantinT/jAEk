from time import time, sleep
import logging

from PyQt5.Qt import QEventLoop, QTimer, QUrl

from core.abstractinteractioncore import AbstractInteractionCore
from models.utils import CrawlSpeed


class Requestor(AbstractInteractionCore):
    def __init__(self, parent, proxy, port, crawl_speed = CrawlSpeed.Medium):
        super(Requestor, self).__init__(parent, proxy, port, crawl_speed)
        self.app = parent.app

    def _loadFinished(self, resutl):
        #logging.debug("{} Subframes found".format(self.mainFrame().childFrames()))
        #logging.debug(self.mainFrame().toHtml())
        pass
        
    def get(self, qurl, html=None, num_retries=1, delay = 10, timeout = 10):
        t1 = time()
        
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        self.loadFinished.connect(loop.quit)
        if qurl:
            if html:
                self.setHtml(html, qurl)
            else: 
                self.mainFrame().load(QUrl(qurl))
        timer.start(timeout * 1000)
        loop.exec_() # delay here until download finished or timeout
    
        if timer.isActive():
            # downloaded successfully
            timer.stop()
            self._wait(delay - (time() - t1))
            parsed_html = self.mainFrame().toHtml()
        else:
            # did not download in time
            if num_retries > 0:
                logging.debug('Timeout - retrying')
                parsed_html = self.get(qurl, num_retries=num_retries-1, timerout=timeout, delay=delay)
            else:
                logging.debug('Timed out')
                parsed_html = ''
        self.mainFrame().setHtml(None)
        return parsed_html
    
    def _wait(self, timeout=1, pattern=None):
        """Wait for delay time
        """
        deadline = time() + timeout
        while time() < deadline:
            sleep(0)
            self.app.processEvents()
      
    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        logging.debug("Console: " + message + " at: " + str(lineNumber))
        
    def __del__(self):
        pass
import json
from PyQt5.QtCore import QObject, pyqtSlot

__author__ = 'constantin'

class JsBridge(QObject):

    def __init__(self, analyzer):
        QObject.__init__(self)
        self.analyzer = analyzer
        self._ajax_request = []

    @pyqtSlot(str)
    def add_eventListener_to_element(self, msg):
        msg = json.loads(msg)
        self.analyzer.add_eventlistener_to_element(msg)

    @pyqtSlot(str)
    def xmlHTTPRequestOpen(self, msg):
        msg = json.loads(msg)
        self._ajax_request.append(msg)

    @pyqtSlot(str)
    def xmlHTTPRequestSend(self, msg):
        msg = json.loads(msg)
        according_open = self._ajax_request.pop(0)
        try:
            according_open['parameters'] = msg['parameters'][0]
        except IndexError:
            according_open['parameters'] = ""
        self.analyzer.capturing_requests(according_open)

    @pyqtSlot(str)
    def timeout(self, msg):
        msg = json.loads(msg)
        msg['type'] = "timeout"
        self.analyzer.capture_timeout_call(msg)

    @pyqtSlot(str)
    def intervall(self, msg):
        msg = json.loads(msg)
        msg['type'] = "intervall"
        #logging.debug(msg)
        self.analyzer.capture_timeout_call(msg)

    @pyqtSlot(str)
    def add_eventlistener_to_element(self, msg):
        msg = json.loads(msg)
        #logging.debug(msg)
        self.analyzer.add_eventlistener_to_element(msg)
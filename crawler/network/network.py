from PyQt5.Qt import QNetworkAccessManager, QDesktopServices, QNetworkDiskCache
import logging
from PyQt5.QtNetwork import QHttpMultiPart, QHttpPart


class NetWorkAccessManager(QNetworkAccessManager):
    
    def __init__(self, parent, cache_size = 100, cache_dir='.webkit_cache'):
        super(NetWorkAccessManager, self).__init__(parent)
        self.finished.connect(self._finished) 
        cache = QNetworkDiskCache()
        cache.setCacheDirectory(cache_dir)
        cache.setMaximumCacheSize(cache_size * 1024 * 1024) # need to convert cache value to bytes
        self.setCache(cache)
        self.reply = None
        
    def _finished(self, reply):
        logging.debug("NetworkAccessManager: Reply from {} {}".format(reply.url().toString(), reply.isFinished()))
        #self.reply.deleteLater()

        
    def createRequest(self, op, req, device=None):
        self.reply = None

        if op == 1:
            logging.debug("NetworkAccessManager: Request created - Operation: {}, Url: {}".format("Head",req.url().toString()))
        elif op == 2:
            logging.debug("NetworkAccessManager: Request created - Operation: {}, Url: {}".format("GET",req.url().toString()))
        elif op == 3:
            logging.debug("NetworkAccessManager: Request created - Operation: {}, Url: {}".format("PUT",req.url().toString()))
        elif op == 4:
            logging.debug("NetworkAccessManager: Request created - Operation: {}, Url: {}".format("POST",req.url().toString()))
        elif op == 5:
            logging.debug("NetworkAccessManager: Request created - Operation: {}, Url: {}".format("Delete",req.url().toString()))
        else:
            logging.debug("NetworkAccessManager: Request created - Operation: {}, Url: {}".format("CUSTOM",req.url().toString()))

        self.reply = QNetworkAccessManager.createRequest(self, op, req, device)
        #reply = NetworkReply(self, reply)       
        return self.reply

    def doPost(self, target, parameters):
        multipart = QHttpMultiPart(QHttpMultiPart.FormDataType)
        text = QHttpPart()


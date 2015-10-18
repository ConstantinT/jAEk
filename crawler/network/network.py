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
        
    def _finished(self, reply):
        reply.deleteLater()
        
    def createRequest(self, op, req, device=None):
        self.reply = None
        """
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
        """
        reply = QNetworkAccessManager.createRequest(self, op, req, device)
        #reply = NetworkReply(self, reply)
        return reply

    def __del__(self):
        self = None

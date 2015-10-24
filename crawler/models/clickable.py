'''
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
'''

import hashlib
from models.clickabletype import ClickableType


class Clickable():
    '''
    Models interesting element with events as attributes
    '''
    
    def __init__(self, event, tag, dom_address, id = None, html_class = None, clickable_depth = None, function_id = None):
        self.event = event
        self.tag = tag
        self.dom_address = dom_address
        self.id = id
        self.html_class = html_class
        self.links_to = None
        self.clicked = False
        self.clickable_type = None
        self.clickable_depth = clickable_depth
        self.function_id = function_id    
        
    def toString(self):
        msg = ""
        msg += "[TAG: " + self.tag
        if self.id is not None and not self.id == "":
            msg += " - ID: " + self.id
        if self.event is not None and not self.event == "":
            msg += " - Event: " + self.event
        if self.html_class is not None and not self.html_class == "":
            msg += " - Class: " + self.html_class
        msg += " - Domaddress: " + self.dom_address
        if self.links_to is not None:
            msg += " - Links to: " + self.links_to
        if self.clickable_depth is not None:
            msg += " - Clickable Depth: " + str(self.clickable_depth)
        if self.function_id is not None:
            msg += " - FunctionID: " + self.function_id
        if self.clickable_type is not None:
            if self.clickable_type == ClickableType.CreatesNewNavigatables:
                msg += " - ClickableType: CreateNewNavigatable"
            elif self.clickable_type == ClickableType.Link:
                msg += " - ClickableType: Link"
            elif self.clickable_type == ClickableType.SendingAjax:
                msg += " - ClickableType: SendingAjax"
            elif self.clickable_type == ClickableType.UIChange:
                msg += " - ClickableType: UiChange"
            elif self.clickable_type == ClickableType.Error:
                msg += " - ClickableType: Error"
            elif self.clickable_type == ClickableType.IgnoredByCrawler:
                msg += " - ClickableType: IgnoredByCrawler"
            elif self.clickable_type == ClickableType.UnsupportedEvent:
                msg += " - ClickableType: UnsupportedEvent"
            else:
                msg += " - ClickableType: Unknown"
        msg += "]"  
        return msg
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.clickable_type is not None and other.clickable_type is not None:
            return self.dom_address == other.dom_address and self.event == other.event and self.clickable_type == other.clickable_type and self.links_to == other.links_to
        else:
            return self.dom_address == other.dom_address and self.event == other.event and self.links_to == other.links_to

    def __hash__(self):
        s_to_hash = self.toString()
        return hash(s_to_hash)


    def __ne__(self, other):
        return not self.__eq__(other)        
    
    def similar(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self == other:
            return True
        elif self.html_class == other and self.id == other.id and self.event == other.event and levenshtein < 4:
            return True
        else: 
            return False
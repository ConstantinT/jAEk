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

from models.clickable import Clickable
from models.clickabletype import ClickableType

class KeyClickable(Clickable):
    
    def __init__(self, clickable, key_event):
        Clickable.__init__(self, clickable.event, clickable.tag, clickable.dom_address, clickable.id, clickable.html_class, clickable.clickable_depth, clickable.function_id)
        self.random_char = key_event #Is the key typed in for triggering the clickabel
    
    def toString(self):   
        msg = ""
        msg += "[TAG: " + self.tag
        if self.id is not None and not self.id == "":
            msg += " - ID: " + self.id
        if self.event is not None and not self.event == "":
            msg += " - Event: " + self.event
        if self.html_class is not None and not self.html_class == "":
            msg += " - Class: " + self.html_class
        msg += " - Domadress: " + self.dom_address
        if self.links_to is not None:
            msg += " - Links to: " + self.links_to
        if self.clickable_depth is not None:
            msg += " - Clickable Depth: " + str(self.clickable_depth)
        if self.function_id is not None:
            msg += " - FunctionID: " + self.function_id
        if self.clickable_type is not None:
            if self.clickable_type == ClickableType.CreatesNewNavigatables:
                msg += " - ClickableType: Create_new_navigatable"
            elif self.clickable_type == ClickableType.Link:
                msg += " - ClickableType: Link"
            elif self.clickable_type == ClickableType.SendingAjax:
                msg += " - ClickableType: SendingAjax"
            elif self.clickable_type == ClickableType.UIChange:
                msg += " - ClickableType: UiChange"
            elif self.clickable_type == ClickableType.Error:
                msg += " - ClickableType: Error"
        if self.random_char is not None:
            msg += self.random_char
        msg += "]"  
        return msg
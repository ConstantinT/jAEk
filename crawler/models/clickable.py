from models.clickabletype import ClickableType


class Clickable():
    '''
    Models interesting element with events as attributes
    '''
    
    def __init__(self, event, tag, dom_adress, id = None, html_class = None, clickable_depth = None, function_id = None):
        self.event = event
        self.tag = tag
        self.dom_adress = dom_adress
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
        msg += " - Domadress: " + self.dom_adress
        if self.links_to is not None:
            msg += " - Links to: " + self.links_to
        if self.clickable_depth is not None:
            msg += " - Clickable Depth: " + str(self.clickable_depth)
        if self.function_id is not None:
            msg += " - FunctionID: " + self.function_id
        if self.clickable_type is not None:
            if self.clickable_type == ClickableType.Creates_new_navigatables:
                msg += " - ClickableType: Create_new_navigatable"
            elif self.clickable_type == ClickableType.Link:
                msg += " - ClickableType: Link"
            elif self.clickable_type == ClickableType.SendingAjax:
                msg += " - ClickableType: SendingAjax"
            elif self.clickable_type == ClickableType.UI_Change:
                msg += " - ClickableType: UiChange"
            elif self.clickable_type == ClickableType.Error:
                msg += " - ClickableType: Error"
            elif self.clickable_type == ClickableType.Ignored_by_Crawler:
                msg += " - ClickableType: IgnoredByCrawler"
            elif self.clickable_type == ClickableType.Unsuported_Event:
                msg += " - ClickableType: UnsupportedEvent"
            else:
                msg += " - ClickableType: Unknown"
        msg += "]"  
        return msg
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.dom_adress == other.dom_adress and self.event == other.event

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
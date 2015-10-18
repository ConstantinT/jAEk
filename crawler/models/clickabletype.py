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
Created on 23.02.2015

@author: constantin
'''
from enum import Enum

class ClickableType(Enum):
    UIChange = 0
    Link = 1
    CreatesNewNavigatables = 2
    Error = 3
    SendingAjax = 4
    IgnoredByCrawler = 5
    UnsupportedEvent = 6
    CreateNewWindow = 7
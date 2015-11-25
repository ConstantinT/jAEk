# -*- coding: latin-1 -*-"
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


from models.asyncrequests import AsyncRequests


class TimingRequest(AsyncRequests):
    '''
    Models an Ajax-Request issued after timeout or intervall
    '''
    def __init__(self, method, url, time, event, parameters=None):
        super(TimingRequest, self).__init__(method, url, parameters)
        self.event = event #Timout or Intervall
        self.time = time

    def toString(self):
        return "[Timing - Method: " + str(self.method) + " - Url: "+ str(self.url.toString()) + " - Trigger: " + str(self.event) + "]"

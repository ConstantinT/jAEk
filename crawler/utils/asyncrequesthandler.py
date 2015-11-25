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
import logging
from models.asyncrequeststructure import AsyncRequestStructure
from models.parametertype import ParameterType
from utils.utils import calculate_new_parameter_type



class AsyncRequestHandler():

    def __init__(self, database_manager):
        self.database_manager = database_manager

    def handle_requests(self, web_page):
        for async_request in web_page.ajax_requests + web_page.timing_requests:
            request_hash = async_request.request_hash
            ajax_structure = self.database_manager.get_asyncrequest_structure(request_hash)
            if ajax_structure is None:
                new_parameters = {}
                parameters = async_request.parameters
                try:
                    for key, value in parameters.items():
                        param_type = calculate_new_parameter_type(None, value)
                        new_parameters[key] = {"parameter_type": param_type.value}
                    async_request.request_structure = AsyncRequestStructure(request_hash, new_parameters)
                except AttributeError:
                    async_request.request_structure = AsyncRequestStructure(request_hash, None)
            else:
                new_parameters = {}
                if async_request.parameters is not None:
                   try:
                        for key, value in async_request.parameters.items():
                            param_type = calculate_new_parameter_type(ParameterType(ajax_structure.parameters[key]['parameter_type']), value)
                            new_parameters[key] = {"parameter_type": param_type.value}
                        async_request.request_structure = AsyncRequestStructure(request_hash, new_parameters)
                   except AttributeError:
                       logging.error("AttributeError with request: {}, Key: {}, Value: {}".format(request_hash, key, value))
                       async_request.request_structure = ajax_structure
                   except KeyError:
                       logging.debug("KeyError with request: {}, Key: {}, Value: {}".format(request_hash, key, value))
                       async_request.request_structure = ajax_structure
                else:
                    async_request.request_structure = ajax_structure
        return web_page





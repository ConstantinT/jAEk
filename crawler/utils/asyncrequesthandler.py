from models.asyncrequeststructure import AsyncRequestStructure
from models.parametertype import ParameterType
from utils.utils import calculate_new_parameter_type

__author__ = 'constantin'


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
                    for key, value in async_request.parameters.items():
                        param_type = calculate_new_parameter_type(ParameterType(ajax_structure.parameters[key]['parameter_type']), value)
                        new_parameters[key] = {"parameter_type": param_type.value}
                async_request.request_structure = AsyncRequestStructure(request_hash, new_parameters)
        return web_page





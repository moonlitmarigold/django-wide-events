from ...config import wide_event_settings
from ..Base import Collector
from .registry import factory_collector


class RequestID(Collector):

    def __init__(self, func):
        self.func = func

    def on_create(self, request):
        request_id = self.func(request)
        request.request_id = request_id
        self.set(request_id=request_id)


class ResponseID(Collector):

    def __init__(self, header):
        self.header = header

    def on_finish(self, request, response):
        response.headers[self.header] = request.request_id


@factory_collector
class RequestIDFactory:

    def __init__(self):
        request_id_settings = wide_event_settings.REQUEST_ID

        generator_func = request_id_settings.get("ID_GENERATOR")
        if request_id_settings.get("TRUST_ID_HEADER"):
            self.generation_func = lambda request: RequestIDFactory.apply_incoming(
                request, generator_func
            )
        else:
            self.generation_func = lambda request: generator_func()

    def __call__(self):
        return RequestID(self.generation_func)

    @staticmethod
    def apply_incoming(request, fallback_id):
        _id = request.headers.get("X-Request-Id", "")
        if _id:
            return _id
        return fallback_id()


@factory_collector
class ResponseIDFactory:

    def __init__(self):
        request_id_settings = wide_event_settings.REQUEST_ID
        response_header = request_id_settings.get('RESPONSE_HEADER', None)
        if response_header:
            self.col = lambda: ResponseID(response_header)
        else:
            self.col = Collector

    def __call__(self):
        return self.col()
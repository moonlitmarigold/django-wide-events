from ..config import wide_event_settings
from ..collectors import Collector
from ..context import ContextEvent
import time
from typing import Callable


def _overrides(cls, name):
    return getattr(cls, name) is not getattr(Collector, name)

def get_request_id(request):
    request.headers.get("X-Request-Id", "")

def generate_request_id(generation_func:Callable):
    return generation_func()

class WideEventMiddleware:

    Collectors:list[Collector]
    StaticFields:dict
    _response_header:str|None

    def __init__(self, get_response):
        self.get_response = get_response

        self.pre_hooks = [] # request, event, collectors
        self.finished_hooks = []
        self.exception_hooks = []


        self.Collectors = wide_event_settings.COLLECTORS
        self.StaticFields = wide_event_settings.STATIC_FIELDS

        request_id_settings = wide_event_settings.REQUEST_ID
        if request_id_settings.get('TRUST_ID_HEADER'):
            self.pre_hooks.append(lambda r:get_request_id(r))
        else:
            self.pre_hooks.append(lambda r: generate_request_id(request_id_settings.get('ID_GENERATOR')))



    def __call__(self, request):

        if self.no_logging(request):
            return self.get_response(request)

        start = time.perf_counter()

        event:dict = {}
        ctx = ContextEvent.init()
        _collectors = self.return_collectors()
        self.apply_request_id(request, event, self._request_id_generation)

        try:
            event.update(self.StaticFields)

            self.collector_on_create(_collectors, request, event)

            response = self.get_response(request)

            return response
        except Exception:
            self.collector_on_exception(_collectors, request, event)
        finally:
            event['duration_ms'] = round((time.perf_counter() - start) * 1000, 2)
            self.collector_on_finish(_collectors, request, response, event)

            event.update(ctx.drop())


    def no_logging(self, request):
        return False

    def return_collectors(self):
        return [c() for c in self.Collectors]

    @staticmethod
    def _call_collectors(collectors, func_name, *args):
        for c in collectors:
            c(func_name, *args)

    def collector_on_create(self, collectors, request, event):
        self._call_collectors(collectors, 'on_create', request, event)

    def collector_on_finish(self, collectors, request, response, event):
        self._call_collectors(collectors, 'on_finish', request, response, event)

    def collector_on_exception(self, collectors, request, event):
        self._call_collectors(collectors, 'on_exception', request, event)

    @staticmethod
    def apply_request_id(request, event, generation_func:Callable):
        incoming = generation_func(request)
        request.request_id = incoming
        event['request_id'] = incoming

    @staticmethod
    def apply_response_id(response, request_id, header: str | None):
        if header:
            response.headers[header] = request_id



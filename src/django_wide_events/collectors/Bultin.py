from .Base import Collector
from ..config import wide_event_settings
from .. event_blocks.TimerEventBlock import _Timer
import dataclasses
from typing import Type

BUILTIN_COLLECTORS = []

def builtin_collector(_class):
    BUILTIN_COLLECTORS.append(_class)
    return _class


FACTORY_COLLECTORS = []

def factory_collector(_class):
    FACTORY_COLLECTORS.append(_class)
    return _class

@builtin_collector
class Duration(Collector):

    def __init__(self):
        self.timer = None

    def on_create(self, request):
        self.timer = _Timer(lambda ms: self.set(duration_ms=ms)).start_timer()

    def on_finish(self, request, response):
        self.timer.stop_timer()

    def on_finish_no_response(self, request, response=None):
        self.timer.stop_timer()

@builtin_collector
class StatusCode(Collector):

    def on_finish(self, request, response):
        self.set(status_code=int(getattr(response, 'status_code')))

    def on_finish_no_response(self, request, response=None):
        self.set(status_code=500)

@builtin_collector
class RequestRoute(Collector):

    def on_finish(self, request, response):
        match = getattr(request, "resolver_match", None)
        if match:
            self.set(route=match.view_name)

    def on_finish_no_response(self, request, response=None):
        self.on_finish(request, response)

@builtin_collector
class StaticFields(Collector):

    def on_create(self, request):
        self.set(**wide_event_settings.STATIC_FIELDS)

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


class RequestID(Collector):

    def __init__(self, func):
        self.func = func

    def on_create(self, request):
        request_id = self.func(request)
        request.request_id = request_id
        self.set(request_id=request_id)

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


class ResponseID(Collector):

    def __init__(self, header):
        self.header = header

    def on_finish(self, request, response):
        response.headers[self.header] = request.request_id

@dataclasses.dataclass
class Change:
    phase:str
    target_index:int

    def absolute(self, _len):
        return self.target_index % _len

@dataclasses.dataclass
class ChangeHookPosition:

    cls:Type
    collectors:list[Collector]
    hooks:dict[str, list[int]]
    changes:list[Change]

    @staticmethod
    def get_index_class_in_collectors(_cls, collectors):
        for i, hook in enumerate(collectors):
            # entries are classes or factory instances; only classes can match
            if isinstance(hook, type) and issubclass(hook, _cls):
                return i
        return None

    def change_position_of_hook(self, _change:Change, collector_index):
        hook_phase = self.hooks[_change.phase]
        if collector_index not in hook_phase:
            # the class doesn't implement this phase, so there is nothing to move
            return hook_phase

        # resolve against the phase length *before* removal: -1 then lands on
        # len(rest), which makes insert() an append
        target_index = _change.absolute(len(hook_phase))
        rest = [i for i in hook_phase if i != collector_index]
        rest.insert(target_index, collector_index)
        return rest

    def convert(self):
        index: int | None = self.get_index_class_in_collectors(
            self.cls, self.collectors
        )
        if index is None:
            return

        for change in self.changes:
            self.hooks[change.phase] = self.change_position_of_hook(
                change, index
            )
        return
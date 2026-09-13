from ..config import wide_event_settings
from ..collectors import Collector, CollectorHooks
from ..context import ContextEvent
import time
from typing import Callable
import logging
import traceback


def get_request_id(request, generation_func:Callable):
    _id = request.headers.get("X-Request-Id", "")
    if _id:
        return _id
    return generation_func()

def generate_request_id(generation_func:Callable):
    return generation_func()


def apply_request_id(request, event, generation_func:Callable):
    incoming = generation_func(request)
    request.request_id = incoming
    event['request_id'] = incoming

def apply_response_id(request, response, header: str):
    response.headers[header] = request.request_id

def apply_status_code(response, event):
    event['status_code'] = int(getattr(response, 'status_code'))

def apply_route(request, event):
    match = getattr(request, "resolver_match", None)
    if match:
        event["route"] = match.view_name

class WideEventMiddleware:

    Collectors:list[Collector]
    StaticFields:dict
    _response_header:str|None

    def __init__(self, get_response):
        self.get_response = get_response

        self.pre_hooks = [] # request, event, collectors
        self.finished_hooks = [] # request, response, event, collectors
        self.exception_hooks = [] # request, exception, event, collectors


        self.Collectors = wide_event_settings.COLLECTORS
        self.StaticFields = wide_event_settings.STATIC_FIELDS
        self.NoLogging = wide_event_settings.NO_LOGGING_PATHS

        # Use lambda r(request), e(event), c(collectors) to build the hooks at every point at the init of middleware
        request_id_settings = wide_event_settings.REQUEST_ID
        if request_id_settings.get('TRUST_ID_HEADER'):
            self.pre_hooks.append(lambda r, e, c:
                                  apply_request_id(
                                      r, e, lambda r2:
                                      get_request_id(r2, request_id_settings.get('ID_GENERATOR'))
                                  )
                            )
        else:
            self.pre_hooks.append(lambda r, e, c:
                                  apply_request_id(
                                      r, e, lambda r2:
                                            request_id_settings.get('ID_GENERATOR')()
                                  )
                            )

        response_header = request_id_settings.get('RESPONSE_HEADER', None)
        if response_header:
            self.finished_hooks.append(lambda rq, rp, e, c: apply_response_id(rq, rp, response_header))

        self.pre_hooks.append(lambda r, e, c: e.update(self.StaticFields))

        # At last, add the collectors to the hooks
        self.pre_hooks.extend(self.plan_hooks('on_create'))
        self.exception_hooks.extend(self.plan_hooks('on_exception'))

        # Plan hooks
        self.finished_hooks.extend([lambda rq, rp, e, c: apply_status_code(rp, e)])
        self.finished_hooks.extend(self.plan_hooks('on_finish'))

        self.logger = logging.getLogger(wide_event_settings.LOGGER_NAME)


    def __call__(self, request):

        if self.no_logging(request):
            return self.get_response(request)

        start = time.perf_counter()

        event:dict = {}
        ctx = ContextEvent.init()
        _collectors = self.return_collectors()
        request.collectors = _collectors

        response = None
        try:
            for hook in self.pre_hooks:
                self.run_hook(hook, event, *(request, event, _collectors))

            request.event = event
            response = self.get_response(request)

            return response
        finally:

            event = getattr(request, 'event', event)
            if response is not None:
                for hook in self.finished_hooks:

                    self.run_hook(hook, event, *(request, response, event, _collectors))
            else:
                event['status_code'] = 500


            apply_route(request,event) # use it unconditionally
            event.update(ctx.drop())

            event['duration_ms'] = round((time.perf_counter() - start) * 1000, 2)

            # Also: set the error/type of logging
            self._log(request, event)


    def _log(self, request, event):
        if 'status_code' not in event.keys() or event['status_code'] >= 500:
            self.logger.error("request", extra={"event": event})
        else:
            self.logger.info("request", extra={"event": event})


    def no_logging(self, request):
        for route in self.NoLogging:
            if request.path.startswith(route):
                return True
        return False

    def return_collectors(self):
        return [c() for c in self.Collectors]


    def plan_hooks(self, name):

        def pre_hook_factory(i, fn):
            return lambda r, e, c: fn(c[i], r, e)

        def exception_hook_factory(i, fn):
            return lambda r, ex, e, c: fn(c[i], r, ex, e)

        def finish_hook_factory(i, fn):
            return lambda rq, rp, e, c: fn(c[i], rq, rp, e)

        if name == CollectorHooks.on_create.value:
            factory = pre_hook_factory
        elif name == CollectorHooks.on_exception.value:
            factory = exception_hook_factory
        else:
            factory = finish_hook_factory

        base = getattr(Collector, name)

        hooks = []
        for i, cls in enumerate(self.Collectors):
            if getattr(cls, name) is not base:
                hook = factory(i, getattr(cls, name))
                hook.label = f"{cls.__name__}.{name}"
                hooks.append(hook)

        return hooks

    def process_exception(self, request, exception):
        request.event["error"] = ({
            "type": type(exception).__name__,
            "message": str(exception),
            "stack":
                "".join(traceback.format_exception(type(exception), exception,
                exception.__traceback__))
            }
        )

        for hook in self.exception_hooks:
            self.run_hook(hook, request.event, *(request, exception, request.event, request.collectors))

        return None

    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):
        view = getattr(view_func, "view_class", view_func)  # CBVs
        if getattr(view, "capture", True) is False:
            request.event["_capture"] = False
        return None

    def run_hook(self, hook:Callable, event, *args):
        try:
            hook(*args)
        except Exception as e:
            self._record_hook_failure(getattr(hook, "label", repr(hook)), event, e)

    @staticmethod
    def _record_hook_failure(label, event, exception):
        errors = event.setdefault('hook_errors', [])
        errors.append(
            {
                "hook" : label,
                "stack": "".join(traceback.format_exception(type(exception), exception,
                exception.__traceback__))
            }
        )



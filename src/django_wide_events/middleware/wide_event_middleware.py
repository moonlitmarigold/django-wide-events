from ..config import wide_event_settings
from ..collectors import Collector, CollectorHooks
from ..collectors.builtin import (
    BUILTIN_COLLECTORS,
    FACTORY_COLLECTORS,
    Change,
    ChangeHookPosition,
    HookPosition,
    Duration,
)
from ..context import ContextEvent, ContextBlock, ContextCollectors, ContextCapture
import logging
import traceback
from ..event_blocks import HookErrorEvent, ExceptionEvent
from dataclasses import dataclass


@dataclass
class CtxDict:

    event:ContextEvent
    block:ContextBlock
    collectors:ContextCollectors
    capture:ContextCapture

    @property
    def get_event(self):
        return self.event.get()

    def drop_all(self):
        self.block.drop()
        self.collectors.drop()
        self.capture.drop()

    @classmethod
    def init(cls):
        return cls(
            ContextEvent.init(),
            ContextBlock.init(),
            ContextCollectors.init(),
            ContextCapture.init()
        )


class WideEventMiddleware:

    Collectors:list[Collector]
    HookPositionChanges:tuple[HookPosition, ...] = (
        HookPosition(Duration, (
            Change(CollectorHooks.on_create, 0),
            Change(CollectorHooks.on_finish, -1),
            Change(CollectorHooks.on_finish_no_response, -1)
        )),
    )



    def __init__(self, get_response):
        self.get_response = get_response

        self.Collectors = wide_event_settings.COLLECTORS
        self.NoLogging = wide_event_settings.NO_LOGGING_PATHS

        # Build the collectors Step by Step

        # Step 1: Builtin Collectors
        self.collectors_classes = list(BUILTIN_COLLECTORS)

        # Step 2: Factory Collectors
        self.collectors_classes += [factory() for factory in FACTORY_COLLECTORS]

        # Step 3: Other Collectors
        self.collectors_classes += self.Collectors

        # For each phase there is a list of index, that corresponds to the index of the collector class in 'collectors_classes'
        self.hooks = {
            hook_phase.value : [
                index for index, cls in enumerate(self.collectors_classes)
                if self.get_hook_phase_function(cls, hook_phase.value) is not getattr(Collector, hook_phase.value)
            ] for hook_phase in CollectorHooks
        }

        for change in self.HookPositionChanges:
            change.apply(self.collectors_classes, self.hooks)

        self.logger = logging.getLogger(wide_event_settings.LOGGER_NAME)


    @staticmethod
    def get_hook_phase_function(cls, phase:str):
        # Read the hook off the class, not an instance: an instance gives a fresh bound
        # method that is never 'is' Collector's plain function, so nothing would be skipped.
        # Factory entries are resolved to the class of the collector they build.
        collector_cls = cls if isinstance(cls, type) else type(cls())
        return getattr(collector_cls, phase)


    def __call__(self, request):

        if self.no_logging(request):
            return self.get_response(request)

        ctx = CtxDict.init()
        ctx.collectors.set_collectors(self.return_collectors())

        response = None
        try:
            self.run_hook_phase(CollectorHooks.on_create.value, request)
            response = self.get_response(request)

            return response
        finally:

            ## New
            self.run_hook_phase(CollectorHooks.on_finish.value, request, response, is_response_none=response is None)

            # Also: set the error/type of logging
            self._log(request, ctx.event.drop(), ctx.capture.get())

            # Reset Blocks and Collectors
            ctx.drop_all()


    def _log(self, request, event, capture):
        extra = {"event": event, "capture":capture}
        if self.is_log_error(event):
            self.logger.error("request", extra=extra)
        else:
            self.logger.info("request", extra=extra)

    @staticmethod
    def is_log_error(event:dict):
        return 'status_code' not in event.keys() or event['status_code'] >= 500

    def no_logging(self, request):
        for route in self.NoLogging:
            if request.path.startswith(route):
                return True
        return False

    def return_collectors(self):
        return [c() for c in self.collectors_classes]

    def process_exception(self, request, exception):
        ExceptionEvent.save_error(
            type(exception).__name__,
            str(exception),
            "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        )

        self.run_hook_phase(CollectorHooks.on_exception.value, request, exception)

        return None

    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):
        view = getattr(view_func, "view_class", view_func)  # CBVs
        is_capture:bool|None = getattr(view, "capture", None)
        if is_capture is not None:
            ContextCapture.set(is_capture)
        return None

    def run_hook_phase(self, phase:str, *args, is_response_none:bool=False):
        phase = phase if not is_response_none else CollectorHooks.on_finish_no_response.value
        phase_hooks = self.hooks.get(phase)
        collectors = ContextCollectors.get()
        for i in phase_hooks: # Go loud if the phase does not exist
            collector = collectors[i]
            try:
                _func = getattr(collector, phase)
                _func(*args)
            except Exception as e:
                HookErrorEvent.save_hook_error(
                    f"{type(collector).__name__}.{phase}",
                    "".join(traceback.format_exception(type(e), e, e.__traceback__),
                ))





from datetime import datetime, timezone

from ...config import wide_event_settings
from ...event_blocks.TimerEventBlock import _Timer
from ..Base import Collector
from .registry import builtin_collector


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
class Timestamp(Collector):

    def on_create(self, request):
        self.set(started_at=datetime.now(timezone.utc).isoformat(timespec='milliseconds'))


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
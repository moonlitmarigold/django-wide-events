from ...config import wide_event_settings
from ...context import ContextTrace
from .Base import SessionTrace
from ...event_blocks.SessionEvents import SessionIDAddEvent

class CheckPaths(SessionTrace):

    def __init__(self):

        _settings = wide_event_settings.SESSION_TRACE
        self.NO_TRACE_PATH = _settings.get("NO_TRACE_PATHS")

    def should_trace(self, request, response) -> bool | None:
        route = getattr(request, "path")
        for path in self.NO_TRACE_PATH:
            if route.startswith(path):
                return False
        return None

class CheckViewName(SessionTrace):

    def __init__(self):
        _settings = wide_event_settings.SESSION_TRACE
        self.NO_TRACE_VIEW_NAMES = _settings.get("NO_TRACE_VIEW_NAMES")

    def should_trace(self, request, response) -> bool | None:
        match = request.resolver_match
        if match is None:  # resolver 404 or a middleware that answered before resolving
            return None
        view_name = match.view_name

        for _view_name in self.NO_TRACE_VIEW_NAMES:
            if view_name == _view_name:
                return False
        return None

class CheckMustTrace(SessionTrace):

    def should_trace(self, request, response) -> bool | None:
        _trace = ContextTrace.get()
        if _trace is not None:
            return _trace
        return None


class CheckResponseError(SessionTrace):

    def should_trace(self, request, response) -> bool | None:
        if response is None:
            return False
        if response.status_code >= 500:
            return False
        return None
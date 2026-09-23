from ...config import WideEventSettings
from .Base import SessionTrace

class CheckPaths(SessionTrace):

    def __init__(self):

        _settings = WideEventSettings.SESSION_TRACE
        self.NO_TRACE_PATH = _settings.get("NO_TRACE_PATHS")

    def should_trace(self, request, view_func, view_args, view_kwargs) -> bool:
        route = getattr(request, "path")
        for path in self.NO_TRACE_PATH:
            if route.startswith(path):
                return False
        return True

class CheckViewName(SessionTrace):

    def __init__(self):
        _settings = WideEventSettings.SESSION_TRACE
        self.NO_TRACE_VIEW_NAMES = _settings.get("NO_TRACE_VIEW_NAMES")

    def should_trace(self, request, view_func, view_args, view_kwargs) -> bool:
        match = request.resolver_match
        view_name = match.view_nam

        for _view_name in self.NO_TRACE_VIEW_NAMES:
            if view_name == _view_name:
                return False
        return True

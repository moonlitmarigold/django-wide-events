# Module import, not the name: config imports collectors, which imports this module.
from ... import config
from ...context import ContextTrace
from .Base import SessionTrace

class CheckPaths(SessionTrace):

    def __init__(self):

        _settings = config.wide_event_settings.SESSION_TRACE
        self.NO_TRACE_PATH = _settings.get("NO_TRACE_PATHS")

    def should_trace(self, request, response) -> bool | None:
        route = getattr(request, "path")
        for path in self.NO_TRACE_PATH:
            if route.startswith(path):
                return False
        return None

class CheckViewName(SessionTrace):

    def __init__(self):
        _settings = config.wide_event_settings.SESSION_TRACE
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

class CheckUserAgent(SessionTrace):

    def __init__(self):
        _settings = config.wide_event_settings.SESSION_TRACE
        self.NO_TRACE_USER_AGENTS = [ua.lower() for ua in _settings.get("NO_TRACE_USER_AGENTS")]

    def should_trace(self, request, response) -> bool | None:
        user_agent = request.headers.get("User-Agent", "").lower()
        for _user_agent in self.NO_TRACE_USER_AGENTS:
            if _user_agent in user_agent:
                return False
        return None

class CheckNamespaces(SessionTrace):

    def __init__(self):
        _settings = config.wide_event_settings.SESSION_TRACE
        self.NO_TRACE_NAMESPACES = _settings.get("NO_TRACE_NAMESPACES")

    def should_trace(self, request, response) -> bool | None:
        match = request.resolver_match
        if match is None:  # resolver 404 or a middleware that answered before resolving
            return None

        for namespace in match.namespaces:
            if namespace in self.NO_TRACE_NAMESPACES:
                return False
        return None

class CheckPrivacySignal(SessionTrace):

    def __init__(self):
        _settings = config.wide_event_settings.SESSION_TRACE
        self.RESPECT_PRIVACY_SIGNALS = _settings.get("RESPECT_PRIVACY_SIGNALS")

    def should_trace(self, request, response) -> bool | None:
        if not self.RESPECT_PRIVACY_SIGNALS:
            return None
        # Global Privacy Control and the older Do Not Track header
        if request.headers.get("Sec-GPC") == "1" or request.headers.get("DNT") == "1":
            return False
        return None

class CheckAuthenticatedOnly(SessionTrace):

    def __init__(self):
        _settings = config.wide_event_settings.SESSION_TRACE
        self.AUTHENTICATED_ONLY = _settings.get("AUTHENTICATED_ONLY")

    def should_trace(self, request, response) -> bool | None:
        if not self.AUTHENTICATED_ONLY:
            return None
        user = getattr(request, "user", None)
        if user is None:  # AuthenticationMiddleware isn't installed
            return None
        if not user.is_authenticated:
            return False
        return None
from ..config import wide_event_settings
from ..collectors.SessionTrace import BUILTIN_SESSION_TRACE
from ..event_blocks import EventBlock
from ..event_blocks.SessionEvents import SessionIDAddEvent
from ..context import ContextTrace

class SessionIDErrorEvent(EventBlock):
    namespace = "NotImplemented"
    pass

class SessionID:

    def __init__(self, get_response):

        self.get_response = get_response

        self._settings = wide_event_settings.SESSION_TRACE


        self.handle_trace_logic_func = self.return_handle_function(self._settings.get("ONLY_EXISTING_SESSIONS"))
        self.id_generation_func = self._settings.get("SESSION_ID_GENERATOR")

        self.session_traces_classes = list(BUILTIN_SESSION_TRACE)
        self.session_traces_classes = [s() for s in self.session_traces_classes]

    @staticmethod
    def return_handle_function(is_override):
        if is_override:
            return SessionID.on_session_trace_only_existing_sessions
        else:
            return SessionID.on_session_trace_not_only_existing_sessions


    def __call__(self, request):

        ctx = ContextTrace.init()
        SessionIDAddEvent.init()
        response =  self.get_response(request)

        if self.check_session_trace(request, response):

            # TODO: Cleanup lambdas
            _func = self.handle_trace_logic_func(request, response)

            _func(self)
        #SessionIDAddEvent.unknow_session_status()
        ctx.drop()
        return response

    def add_session_id(self, trace, request):
        #SessionIDAddEvent.debug_session_trace(trace is None)
        if trace is None:
            SessionIDAddEvent.add_id(self.id_generation_func)

        if trace is None:
            trace = self.id_generation_func()
            request.session["wide_events_trace"] = trace

        SessionIDAddEvent.add_id(
            trace
        )

    @staticmethod
    def get_trace_from_session(request):
        return request.session.get("wide_events_trace", None)

    @staticmethod
    def on_session_trace_only_existing_sessions(request, response):
        if request.session.session_key is None:
            return lambda _: SessionIDAddEvent.no_existing_session()

        trace = SessionID.get_trace_from_session(request)

        if request.session.session_key is None:
            return lambda _: SessionIDAddEvent.invalid_session()

        return lambda _cls: SessionID.add_session_id(_cls, trace, request)

    @staticmethod
    def on_session_trace_not_only_existing_sessions(request, response):
        trace = SessionID.get_trace_from_session(request)
        return lambda _cls: SessionID.add_session_id(_cls, trace, request)

    def check_session_trace(self, *args):

        for session_tracer in self.session_traces_classes:
            res = session_tracer.should_trace(*args)
            if res is not None:
                return res
        return True

    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):
        view = getattr(view_func, "view_class", view_func)
        _trace:bool | None = getattr(view, "trace", None)
        if _trace is not None:
            ContextTrace.set(_trace)
        return
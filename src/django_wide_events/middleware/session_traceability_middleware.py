from ..config import wide_event_settings
from ..collectors.SessionTrace import BUILTIN_SESSION_TRACE, DEFAULT_SESSION_TRACE
from ..event_blocks import EventBlock, SessionErrorEvent
from ..event_blocks.SessionEvents import SessionIDAddEvent
from ..context import ContextTrace
import traceback


class SessionID:

    def __init__(self, get_response):

        self.get_response = get_response

        self._settings = wide_event_settings.SESSION_TRACE

        self.handle_trace_logic_func = self.return_handle_function(self._settings.get("ONLY_EXISTING_SESSIONS"))
        self.id_generation_func = self._settings.get("SESSION_ID_GENERATOR")

        self.session_traces_classes = list(BUILTIN_SESSION_TRACE)
        self.session_traces_classes.extend(DEFAULT_SESSION_TRACE)
        self.session_traces_classes.extend(self._settings.get("SESSION_CHECKS", []))
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

        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            should_trace, tracer = self.check_session_trace(request, response)
            SessionIDAddEvent.decision(should_trace, tracer)

            if should_trace:
                _func = self.handle_trace_logic_func(request, response)

                _func(self)
            else:
                SessionIDAddEvent.not_traced()
            ctx.drop()

    def add_session_id(self, trace, request):
        if trace is not None:
            SessionIDAddEvent.existing_id(trace)
            return

        trace = self.id_generation_func()
        request.session["wide_events_trace"] = trace
        SessionIDAddEvent.new_id(trace)

    @staticmethod
    def get_trace_from_session(request):
        return request.session.get("wide_events_trace", None)

    @staticmethod
    def on_session_trace_only_existing_sessions(request, response):
        if request.session.session_key is None:
            return lambda _: SessionIDAddEvent.no_existing_session()

        trace = SessionID.get_trace_from_session(request)
        return lambda _cls: SessionID.add_session_id(_cls, trace, request)

    @staticmethod
    def on_session_trace_not_only_existing_sessions(request, response):
        trace = SessionID.get_trace_from_session(request)
        return lambda _cls: SessionID.add_session_id(_cls, trace, request)

    def check_session_trace(self, *args) -> tuple[bool, str | None]:
        # First tracer with an opinion decides; the name says which one did.
        for session_tracer in self.session_traces_classes:
            try:
                res = session_tracer.should_trace(*args)
                if res is not None:
                    return res, session_tracer.get_name()
            except Exception as e:
                SessionErrorEvent.save_session_error(
                    session_tracer.get_name(),
                    "".join(traceback.format_exception(type(e), e, e.__traceback__)),
                )
        return True, None

    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):
        view = getattr(view_func, "view_class", view_func)
        _trace: bool | None = getattr(view, "trace", None)
        if _trace is not None:
            ContextTrace.set(_trace)
        return
    
    


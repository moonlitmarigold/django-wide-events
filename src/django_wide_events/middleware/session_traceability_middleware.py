from ..config import wide_event_settings
from ..collectors.SessionTrace import BUILTIN_SESSION_TRACE
from ..event_blocks import EventBlock
from ..event_blocks.SessionEvents import SessionIDAddEvent
from ..context import ContextTrace

class SessionIDErrorEvent(EventBlock):

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
        response =  self.get_response(request)

        if self.check_session_trace(request, response):

            trace, is_break = self.handle_trace_logic_func(
                request, response
            )

            if not is_break:
                SessionIDAddEvent.add_id(
                    trace if trace is not None else self.id_generation_func()
                )

        SessionIDAddEvent.no_session_id()
        return response

    @staticmethod
    def on_session_trace_only_existing_sessions(request, response):
        if request.session.session_key is None:
            return None, True

        # Get the actual session and if the key is valid
        trace = request.session.get("wide_events_trace", None)
        if request.session.session_key is None:
            return None, True

        return trace, False

    @staticmethod
    def on_session_trace_not_only_existing_sessions(request, response):
        trace = request.session.get("wide_events_trace", None)
        return trace, False

    def check_session_trace(self, *args):

        for session_tracer in self.session_traces_classes:
            # ADD: Session Trace error
            res = session_tracer.should_trace(*args)
            if res is not None:
                return res
        return True

    def process_view(self, request, view_func, view_args, view_kwargs):
        # TODO: Make error event an list

        return
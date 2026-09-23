from django.conf import settings
from ..config import WideEventSettings
from ..collectors.SessionTrace import BUILTIN_SESSION_TRACE
from ..event_blocks import EventBlock

class NoSessionInstalled(Exception):

    def __init__(self):
        super().__init__("The Request has no session attached to it")

class SessionIDErrorEvent(EventBlock):

    pass

class SessionIDAddEvent(EventBlock):

    pass

class SessionID:

    def __init__(self, get_response):

        self.get_response = get_response

        self._settings = WideEventSettings.SESSION_TRACE
        self.ONLY_EXISTING_SESSIONS = self._settings.get("ONLY_EXISTING_SESSIONS")

        self.session_traces_classes = list(BUILTIN_SESSION_TRACE)



    def __call__(self, request):
        return self.get_response(request)

    def check_session_trace(self, *args):
        session_tracers = [s() for s in self.session_traces_classes]

        for session_tracer in session_tracers:
            res = session_tracer.should_trace(*args)
            if res is False:
                return False
        return True


    def process_view(self, request, view_func, view_args, view_kwargs):

        if not hasattr(request, "session"):  # keep per call check to ensure existing sessions
            if self.check_session_trace(request, view_func, view_args, view_kwargs):
                raise NoSessionInstalled()  # NO raise: there will be no traceback so attach error to event block
            return

        if request.session.session_key is None:
            # Add bot to the event blocks
            return
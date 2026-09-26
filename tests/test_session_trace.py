from django.core.mail.message import sanitize_address
from django.test import TestCase, override_settings
from django_wide_events.event_blocks import SessionStatus
from tests.settings import WIDE_EVENTS
from tests.test_middleware import EventCaptureMixin

class BaseSessionTestCase(EventCaptureMixin, TestCase):

    @property
    def last_session_id(self):
        return self.handler.records[-1].event.get("session").get("session_id")

    @property
    def session(self):
        return self.handler.records[-1].event.get("session")

    def create_session(self):
        self.client.session.get("wide_events_trace", None)

class TestSessionTrace(BaseSessionTestCase):

    def test_session_id(self):
        self.client.session.get("wide_events_trace", None)
        self.client.get("/")

        last_event: dict = self.handler.records[-1].event
        assert "session" in last_event

        session = last_event.get("session")
        assert "session_id" in session

    def test_session_id_keep(self):

        self.client.session.get("wide_events_trace", None)
        self.client.get("/")

        id_1 = self.last_session_id

        self.client.get("/")

        id_2 = self.last_session_id

        assert id_1 == id_2

    def test_session_boom(self):
        self.client.get("/boom/")

        assert self.last_session_id is None

@override_settings(
    WIDE_EVENTS={
        "SESSION_TRACE":{
                "NO_TRACE_PATHS": ["/slow/"],
                "NO_TRACE_VIEW_NAMES": ["ok"],
                "ONLY_EXISTING_SESSIONS": True,
                "SESSION_ID_GENERATOR": "django_wide_events.ids.uuid4_hex",
    }
    }
)
class TestSessionTraceCapture(BaseSessionTestCase):

    def test_trace_on_path(self):
        self.client.get("/slow/")
        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.no_trace_path

    def test_trace_on_view(self):
        self.client.get("")
        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.no_trace_view

    def test_trace_decorators(self):
        self.create_session()
        self.client.get("/never_trace/")

        assert self.last_session_id is None
        assert self.session.get("should_trace") is False

        self.client.get("/always_trace/")

        assert self.last_session_id is not None
        assert self.session.get("should_trace") is True



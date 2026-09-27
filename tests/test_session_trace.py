from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django_wide_events.event_blocks import SessionStatus
from tests.settings import WIDE_EVENTS
from tests.test_middleware import EventCaptureMixin
from django_wide_events.collectors.SessionTrace import BaseSessionTrace

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
        assert session.get("session_id") is not None
        assert session.get("session_status") == SessionStatus.new_id

    def test_session_id_keep(self):

        self.client.session.get("wide_events_trace", None)
        self.client.get("/")

        id_1 = self.last_session_id

        self.client.get("/")

        id_2 = self.last_session_id

        assert id_1 == id_2

    def test_session_id_keep_status(self):
        self.create_session()
        self.client.get("/")
        assert self.session.get("session_status") == SessionStatus.new_id

        self.client.get("/")
        assert self.session.get("session_status") == SessionStatus.existing_id

    def test_session_boom(self):
        self.client.get("/boom/")

        assert self.last_session_id is None

    def test_no_existing_session(self):
        self.client.get("/")

        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.no_existing_session
        assert self.session.get("should_trace") is True
        assert self.session.get("session_tracer") is None

    def test_server_error_not_traced(self):
        self.create_session()
        self.client.get("/")
        id_1 = self.last_session_id

        self.client.get("/boom/")
        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.not_traced
        assert self.session.get("session_tracer") == "CheckResponseError"

        self.client.get("/523/")
        assert self.last_session_id is None
        assert self.session.get("session_tracer") == "CheckResponseError"

        self.client.get("/")
        assert self.last_session_id == id_1
        assert self.session.get("session_status") == SessionStatus.existing_id

    def test_login_keeps_id(self):
        get_user_model().objects.create_user(username="tracer", password="tracer")
        self.create_session()
        self.client.get("/")
        id_1 = self.last_session_id

        self.client.get("/login/")
        assert self.last_session_id == id_1

        self.client.get("/")
        assert self.last_session_id == id_1
        assert self.session.get("session_status") == SessionStatus.existing_id

    def test_logout_new_id(self):
        self.create_session()
        self.client.get("/")
        id_1 = self.last_session_id

        self.client.get("/logout/")
        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.no_existing_session

        # logout empties the session cookie; a browser drops it, the test client keeps it
        self.client.cookies.pop(settings.SESSION_COOKIE_NAME)
        self.create_session()
        self.client.get("/")
        assert self.last_session_id is not None
        assert self.last_session_id != id_1
        assert self.session.get("session_status") == SessionStatus.new_id

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
        assert self.session.get("session_status") == SessionStatus.not_traced
        assert self.session.get("session_tracer") == "CheckPaths"

    def test_trace_on_view(self):
        self.client.get("")
        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.not_traced
        assert self.session.get("session_tracer") == "CheckViewName"

    def test_trace_decorators(self):
        self.create_session()
        self.client.get("/never_trace/")

        assert self.last_session_id is None
        assert self.session.get("should_trace") is False
        assert self.session.get("session_tracer") == "CheckMustTrace"

        self.client.get("/always_trace/")

        assert self.last_session_id is not None
        assert self.session.get("should_trace") is True
        assert self.session.get("session_tracer") == "CheckMustTrace"

@override_settings(
    WIDE_EVENTS={
        "SESSION_TRACE":{
                "NO_TRACE_PATHS": ["/always_trace/"],
    }
    }
)
class TestSessionTraceForce(BaseSessionTestCase):

    def test_always_trace_on_excluded_path(self):
        self.create_session()
        self.client.get("/always_trace/")

        assert self.last_session_id is not None
        assert self.session.get("session_status") == SessionStatus.new_id
        assert self.session.get("session_tracer") == "CheckMustTrace"

@override_settings(
    WIDE_EVENTS={
        "SESSION_TRACE":{
                "ONLY_EXISTING_SESSIONS": False,
    }
    }
)
class TestSessionTraceNewSessions(BaseSessionTestCase):

    def test_creates_session(self):
        self.client.get("/")
        id_1 = self.last_session_id

        assert id_1 is not None
        assert self.session.get("session_status") == SessionStatus.new_id

        self.client.get("/")
        assert self.last_session_id == id_1
        assert self.session.get("session_status") == SessionStatus.existing_id

class RaisingTracer(BaseSessionTrace):

    def should_trace(self, request, response) -> bool | None:
        raise ValueError("tracer boom")

@override_settings(
    WIDE_EVENTS={
        "SESSION_TRACE":{
                "SESSION_CHECKS": [RaisingTracer],
    }
    }
)
class TestSessionTraceErrors(BaseSessionTestCase):

    def test_tracer_error(self):
        self.create_session()
        self.client.get("/")

        errors = self.handler.records[-1].event.get("session_errors")
        assert len(errors) == 1
        assert errors[0].get("tracer_name") == "RaisingTracer"
        assert "tracer boom" in errors[0].get("stack")

        # a failing tracer has no opinion, the request is still traced
        assert self.last_session_id is not None
        assert self.session.get("session_tracer") is None

class TestSessionTraceUserAgent(BaseSessionTestCase):

    def test_bot_user_agent(self):
        self.create_session()
        self.client.get("/", headers={"user-agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"})

        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.not_traced
        assert self.session.get("session_tracer") == "CheckUserAgent"

    def test_browser_user_agent(self):
        self.create_session()
        self.client.get("/", headers={"user-agent": "Mozilla/5.0 (X11; Linux x86_64) Firefox/130.0"})

        assert self.last_session_id is not None
        assert self.session.get("session_tracer") is None

    @override_settings(
        WIDE_EVENTS={
            "SESSION_TRACE":{
                    "NO_TRACE_USER_AGENTS": ["My-Monitor"],
        }
        }
    )
    def test_custom_user_agent(self):
        self.create_session()
        self.client.get("/", headers={"user-agent": "my-monitor/1.0"})

        assert self.last_session_id is None
        assert self.session.get("session_tracer") == "CheckUserAgent"

@override_settings(
    WIDE_EVENTS={
        "SESSION_TRACE":{
                "NO_TRACE_NAMESPACES": ["private"],
    }
    }
)
class TestSessionTraceNamespaces(BaseSessionTestCase):

    def test_namespace(self):
        self.create_session()
        self.client.get("/private/")

        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.not_traced
        assert self.session.get("session_tracer") == "CheckNamespaces"

    def test_no_namespace(self):
        self.create_session()
        self.client.get("/")

        assert self.last_session_id is not None

class TestSessionTracePrivacySignal(BaseSessionTestCase):

    def test_global_privacy_control(self):
        self.create_session()
        self.client.get("/", headers={"sec-gpc": "1"})

        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.not_traced
        assert self.session.get("session_tracer") == "CheckPrivacySignal"

    def test_do_not_track(self):
        self.create_session()
        self.client.get("/", headers={"dnt": "1"})

        assert self.last_session_id is None
        assert self.session.get("session_tracer") == "CheckPrivacySignal"

    @override_settings(
        WIDE_EVENTS={
            "SESSION_TRACE":{
                    "RESPECT_PRIVACY_SIGNALS": False,
        }
        }
    )
    def test_privacy_signal_ignored(self):
        self.create_session()
        self.client.get("/", headers={"sec-gpc": "1"})

        assert self.last_session_id is not None

@override_settings(
    MIDDLEWARE=[
        "django_wide_events.middleware.wide_event_middleware.WideEventMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django_wide_events.middleware.session_traceability_middleware.SessionID",
    ],
    WIDE_EVENTS={
        "SESSION_TRACE":{
                "AUTHENTICATED_ONLY": True,
    }
    }
)
class TestSessionTraceAuthenticatedOnly(BaseSessionTestCase):

    def test_anonymous(self):
        self.create_session()
        self.client.get("/")

        assert self.last_session_id is None
        assert self.session.get("session_status") == SessionStatus.not_traced
        assert self.session.get("session_tracer") == "CheckAuthenticatedOnly"

    def test_authenticated(self):
        user = get_user_model().objects.create_user(username="tracer", password="tracer")
        self.client.force_login(user)
        self.client.get("/")

        assert self.last_session_id is not None
        assert self.session.get("session_status") == SessionStatus.new_id
        assert self.session.get("session_tracer") is None



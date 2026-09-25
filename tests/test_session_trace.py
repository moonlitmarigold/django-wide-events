from django.test import TestCase, override_settings
from tests.test_middleware import EventCaptureMixin



class TestSessionTrace(EventCaptureMixin, TestCase):

    def test_session_id(self):
        self.client.session.get("wide_events_trace", None)
        self.client.get("/")

        last_event: dict = self.handler.records[-1].event
        assert "session" in last_event
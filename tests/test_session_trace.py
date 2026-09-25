from django.core.mail.message import sanitize_address
from django.test import TestCase, override_settings
from tests.test_middleware import EventCaptureMixin



class TestSessionTrace(EventCaptureMixin, TestCase):

    @property
    def last_session_id(self):
        return self.handler.records[-1].event.get("session").get("session_id")

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
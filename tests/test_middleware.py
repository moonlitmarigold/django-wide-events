import logging
from uuid import uuid4

from django.test import Client, TestCase, override_settings

from wide_events.config import wide_event_settings


def _make_request_id() -> str:
    return uuid4().hex


class RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


class EventCaptureMixin:
    """Captures the events the middleware emits for the duration of one test."""

    def setUp(self):
        # raise_request_exception=False so an unhandled view exception is reported
        # as a 500 instead of being re-raised into the test.
        self.client = Client(raise_request_exception=False)
        self.handler = RecordingHandler()
        self.logger = logging.getLogger(wide_event_settings.LOGGER_NAME)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    @property
    def event(self):
        return self.handler.records[-1].event


@override_settings(
    WIDE_EVENTS={
        "STATIC_FIELDS": {"service": "tests"},
        "REQUEST_ID": {
            "TRUST_ID_HEADER": True,
            "RESPONSE_HEADER": "X-Request-Id",
            "ID_GENERATOR": _make_request_id,
        },
    }
)
class TestWideEventMiddleware(EventCaptureMixin, TestCase):
    def test_emits_single_event_with_trusted_request_id(self):
        self.client.get("/", headers={"x-request-id": "test-rid-123"})

        assert len(self.handler.records) == 1
        assert self.event["request_id"] == "test-rid-123"
        assert self.event["service"] == "tests"

    def test_generates_request_id_when_header_absent(self):
        self.client.get("/")
        assert self.event["request_id"]

    def test_sets_request_id_response_header(self):
        response = self.client.get("/", headers={"x-request-id": "test-rid-123"})
        assert response["X-Request-Id"] == "test-rid-123"

    def test_records_route_and_status(self):
        self.client.get("/")
        assert self.event["route"] == "ok"
        assert self.event["status_code"] == 200
        assert self.handler.records[-1].levelno == logging.INFO

    def test_http404_is_not_an_error_level_event(self):
        self.client.get("/404/")
        assert self.event["status_code"] == 404
        assert self.handler.records[-1].levelno == logging.INFO
        assert self.event["error"]["type"] == "Http404"

    def test_5xx_response_without_exception_logs_at_error(self):
        self.client.get("/523/")
        assert self.event["status_code"] == 523
        assert self.handler.records[-1].levelno == logging.ERROR
        assert "error" not in self.event

    def test_view_exception_records_error_and_status_500(self):
        self.client.get("/boom/")
        assert self.event["status_code"] == 500
        assert self.event["route"] == "boom"
        assert self.handler.records[-1].levelno == logging.ERROR
        error = self.event["error"]
        assert error["type"] == "ValueError"
        assert error["message"] == "boom"
        assert "raise ValueError" in error["stack"]


@override_settings(
    WIDE_EVENTS={
        "STATIC_FIELDS": {"service": "tests"},
        "REQUEST_ID": {
            "TRUST_ID_HEADER": False,
            "RESPONSE_HEADER": "X-Request-Id",
            "ID_GENERATOR": _make_request_id,
        },
    }
)
class TestUntrustedRequestIdHeader(EventCaptureMixin, TestCase):
    """``TRUST_ID_HEADER: False`` - the id always comes from ID_GENERATOR."""

    def test_generates_id_from_the_configured_generator(self):
        self.client.get("/")

        request_id = self.event["request_id"]
        assert isinstance(request_id, str), f"expected a str, got {request_id!r}"
        assert len(request_id) == 32  # uuid4().hex, as _make_request_id returns

    def test_ignores_incoming_request_id_header(self):
        self.client.get("/", headers={"x-request-id": "spoofed-rid-123"})
        assert self.event["request_id"] != "spoofed-rid-123"

    def test_response_header_carries_the_generated_id(self):
        response = self.client.get("/", headers={"x-request-id": "spoofed-rid-123"})
        assert response["X-Request-Id"] == self.event["request_id"]
        assert response["X-Request-Id"] != "spoofed-rid-123"

    def test_each_request_gets_a_distinct_id(self):
        self.client.get("/")
        self.client.get("/")

        first, second = (record.event["request_id"] for record in self.handler.records)
        assert first != second

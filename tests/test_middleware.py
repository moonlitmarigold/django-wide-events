import logging
from uuid import uuid4

from django.test import Client, RequestFactory, TestCase, override_settings

from django_wide_events.config import wide_event_settings
from django_wide_events.collectors import Collector
from django_wide_events.middleware import WideEventMiddleware


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

class TestCollector(Collector):

    def on_create(self, request):
        self.set(test=True)

    def on_exception(self, request, exception):
        self.set(test_e=True)

    def on_finish(self, request, response):
        self.set(test_f=True)

    def on_finish_no_response(self, request, response=None):
        self.set(test_rn=True)

class RaisingCollector(Collector):

    def on_create(self, request):
        raise RuntimeError("collector broke")


class StatefulCollector(Collector):

    def __init__(self):
        self.seen = []

    def on_create(self, request):
        self.seen.append("create")

    def on_finish(self, request, response):
        self.seen.append("finish")
        self.set(seen=list(self.seen))


def _collector_settings(*collectors):
    return {
        "COLLECTORS": [f"tests.test_middleware.{c.__name__}" for c in collectors],
        "REQUEST_ID": {"ID_GENERATOR": _make_request_id},
    }


@override_settings(WIDE_EVENTS=_collector_settings(TestCollector))
class TestCollectors(EventCaptureMixin, TestCase):

    def test_create_and_finish_run_on_a_normal_request(self):
        self.client.get("/")
        assert self.event["test"] is True
        assert self.event["test_f"] is True
        assert "test_e" not in self.event
        assert "test_rn" not in self.event

    def test_exception_hook_runs_when_the_view_raises(self):
        # Django turns the exception into a 500 response, so on_finish still runs
        self.client.get("/boom/")
        assert self.event["test"] is True
        assert self.event["test_e"] is True
        assert self.event["test_f"] is True
        assert "test_rn" not in self.event

    def test_finish_no_response_runs_when_no_response_comes_back(self):
        # Only reachable when an exception escapes the inner stack, which the test
        # client never allows - so drive the middleware directly.
        def get_response(request):
            raise RuntimeError("no response")

        middleware = WideEventMiddleware(get_response)
        with self.assertRaises(RuntimeError):
            middleware(RequestFactory().get("/"))

        assert self.event["test"] is True
        assert self.event["test_rn"] is True
        assert "test_f" not in self.event
        assert self.event["status_code"] == 500


@override_settings(WIDE_EVENTS=_collector_settings(RaisingCollector, TestCollector))
class TestCollectorHookErrors(EventCaptureMixin, TestCase):

    def test_failing_hook_is_recorded_and_the_request_still_succeeds(self):
        response = self.client.get("/")

        assert response.status_code == 200
        assert self.event["test"] is True  # later collectors still ran
        hook_errors = self.event["hook_error"]["hook_errors"]
        assert [e["hook"] for e in hook_errors] == ["RaisingCollector.on_create"]
        assert "collector broke" in hook_errors[0]["stack"]


@override_settings(WIDE_EVENTS=_collector_settings(StatefulCollector))
class TestCollectorState(EventCaptureMixin, TestCase):

    def test_state_survives_between_hooks_but_not_between_requests(self):
        self.client.get("/")
        self.client.get("/")

        first, second = (record.event["seen"] for record in self.handler.records)
        assert first == ["create", "finish"]
        assert second == ["create", "finish"]



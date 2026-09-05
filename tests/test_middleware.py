import logging
from urllib import response
from uuid import uuid4

from django.http import HttpResponse, Http404
from django.test import RequestFactory, TestCase, override_settings

from wide_events.config import wide_event_settings
from wide_events.middleware.wide_event_middleware import WideEventMiddleware


def _make_request_id() -> str:
    return uuid4().hex


def dummy_view(request):
    return HttpResponse("ok")

def dummy_error_view(request):
    return HttpResponse(status=523)

def dummy_404_view(request):
    raise Http404

class RecordingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


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
class TestWideEventMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.handler = RecordingHandler()
        self.logger = logging.getLogger(wide_event_settings.LOGGER_NAME)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def request_through(self, x_request_id=None, view=None):
        kwargs = {}
        _view = view if view else dummy_view
        if x_request_id is not None:
            kwargs["HTTP_X_REQUEST_ID"] = x_request_id
        request = self.factory.get("/", **kwargs)
        response = WideEventMiddleware(_view)(request)
        return request, response

    def test_emits_single_event_with_trusted_request_id(self):
        _, _ = self.request_through(x_request_id="test-rid-123")

        assert len(self.handler.records) == 1
        event = self.handler.records[0].event
        assert event["request_id"] == "test-rid-123"
        assert event["static_fields"]["service"] if "static_fields" in event else True

    def test_generates_request_id_when_header_absent(self):
        request, _ = self.request_through()
        event = self.handler.records[-1].event
        assert event["request_id"] == request.request_id

    def test_sets_request_id_response_header(self):
        _, response = self.request_through(x_request_id="test-rid-123")
        assert response["X-Request-Id"] == "test-rid-123"

    def test_request_error(self):
        _, response = self.request_through(view=dummy_404_view)

        _, response = self.request_through(view=dummy_error_view)

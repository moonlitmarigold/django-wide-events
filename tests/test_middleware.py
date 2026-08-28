"""Behavioural tests for the core middleware.

Skipped wholesale until ``wide_events.middleware`` exists — they activate on
their own the moment it does, which makes them the spec to build against.
"""

import pytest
from django.urls import reverse

pytest.importorskip(
    "wide_events.middleware",
    reason="core middleware not implemented yet (see EXAMPLE_USAGE.md)",
)

MIDDLEWARE_PATH = "wide_events.middleware.WideEventMiddleware"


@pytest.fixture(autouse=True)
def install_middleware(settings):
    settings.MIDDLEWARE = [MIDDLEWARE_PATH, *settings.MIDDLEWARE]


def test_emits_exactly_one_event_per_request(client, events):
    client.get(reverse("tests:ok"))
    events.one()


def test_event_carries_request_basics(client, events, assert_json_safe):
    client.get(reverse("tests:picture-download", args=[42]))

    event = events.one()
    assert event["method"] == "GET"
    assert event["path"] == "/pictures/42/download/"
    assert event["route"] == "tests:picture-download"
    assert event["status_code"] == 200
    assert event["duration_ms"] >= 0
    assert event["request_id"]
    assert_json_safe(event)


def test_static_fields_are_merged_in(client, events):
    client.get(reverse("tests:ok"))
    assert events.one()["service"] == "test-project"


def test_excluded_paths_emit_nothing(client, events):
    client.get(reverse("tests:health"))
    assert len(events) == 0


def test_exception_is_recorded_and_logged_as_error(client_quiet, events):
    client_quiet.get(reverse("tests:boom"))

    event = events.one()
    assert event["error"]["type"] == "ValueError"
    assert "kaboom" in event["error"]["message"]
    assert events.one_record().levelno >= 40  # ERROR


def test_server_error_status_is_logged_as_error(client, events):
    client.get(reverse("tests:server-error"))
    assert events.one()["status_code"] == 500
    assert events.one_record().levelno >= 40


def test_request_id_is_on_the_response(client, events):
    response = client.get(reverse("tests:ok"))
    assert response.headers["X-Request-Id"] == events.one()["request_id"]

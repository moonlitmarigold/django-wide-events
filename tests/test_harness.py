"""Tests for the test environment itself.

These do not test the package — they prove the harness can boot Django, route a
request, and capture a wide event, so that a failure in a real test means a real bug.
"""

import logging

import pytest
from django.conf import settings
from django.urls import reverse

LOGGER = logging.getLogger("wide_events")


def test_django_boots():
    assert "wide_events" in settings.INSTALLED_APPS
    assert settings.WIDE_EVENTS["STATIC_FIELDS"]["service"] == "test-project"


@pytest.mark.parametrize(
    ("name", "status"),
    [
        ("tests:ok", 200),
        ("tests:health", 200),
        ("tests:server-error", 500),
        ("tests:forbidden", 403),
        ("tests:redirect", 302),
    ],
)
def test_views_respond(client, name, status):
    assert client.get(reverse(name)).status_code == status


def test_url_kwargs_reach_the_view(client):
    response = client.get(reverse("tests:picture-download", args=[42]))
    assert response.content == b"picture 42"


def test_exception_view_raises_by_default(client):
    with pytest.raises(ValueError, match="kaboom"):
        client.get(reverse("tests:boom"))


def test_exception_view_returns_500_with_quiet_client(client_quiet):
    assert client_quiet.get(reverse("tests:boom")).status_code == 500


def test_events_fixture_captures(events, assert_json_safe):
    LOGGER.info("request", extra={"event": {"path": "/ok/", "status_code": 200}})

    event = events.one()
    assert event["path"] == "/ok/"
    assert events.one_record().levelno == logging.INFO
    assert_json_safe(event)


def test_events_fixture_is_isolated(events):
    """No leakage from the previous test's emission."""
    assert len(events) == 0

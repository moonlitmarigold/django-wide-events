import pytest
from django.test import override_settings

from wide_events.config import wide_event_settings


def test_strict_collectors_defaults_to_false():
    assert wide_event_settings.STRICT_COLLECTORS is False


def test_unknown_setting_raises_attribute_error():
    with pytest.raises(AttributeError):
        wide_event_settings.NOT_A_SETTING


@override_settings(WIDE_EVENTS={"STATIC_FIELDS": {"region": "eu"}})
def test_static_fields_from_override_are_visible():
    assert wide_event_settings.STATIC_FIELDS["region"] == "eu"
    
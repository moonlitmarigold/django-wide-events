import pytest
from django.test import override_settings
import uuid

from django_wide_events.config import wide_event_settings

def custom_id():
    return uuid.uuid4().hex

def test_unknown_setting_raises_attribute_error():
    with pytest.raises(AttributeError):
        wide_event_settings.NOT_A_SETTING


@override_settings(WIDE_EVENTS={"STATIC_FIELDS": {"region": "eu"}})
def test_static_fields_from_override_are_visible():
    assert wide_event_settings.STATIC_FIELDS["region"] == "eu"

@override_settings(WIDE_EVENTS={"REQUEST_ID":{"ID_GENERATOR":"tests.test_config.custom_id"}})
def test_custom_id():
    _r = wide_event_settings.REQUEST_ID
    _r.get("ID_GENERATOR")()
    
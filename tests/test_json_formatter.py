import json
import logging

from wide_events.formatters.json_formatter import JSONFORMATTER


def _make_record(message="hello", name="wide_events.test"):
    return logging.LogRecord(name, logging.INFO, __file__, 1, message, None, None)


def test_scalar_output_has_base_fields():
    data = json.loads(JSONFORMATTER().format(_make_record()))
    assert data["message"] == "hello"
    assert data["loglevel"] == "INFO"
    assert data["logger"] == "wide_events.test"


def test_merges_event_and_error_into_output():
    record = _make_record()
    record.event = {"request_id": "abc"}
    record.exc_info = (ValueError, ValueError("boom"), None)

    data = json.loads(JSONFORMATTER().format(record))
    assert data["request_id"] == "abc"
    assert data["error"]["type"] == "ValueError"


def test_indent_dump_is_valid_pretty_json():
    record = _make_record()
    out = JSONFORMATTER(indent=True).format(record)
    assert "\n" in out
    assert json.loads(out)["message"] == "hello"
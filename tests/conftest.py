"""Shared test fixtures.

The one piece of machinery worth having here is ``events``: wide events are emitted
through stdlib logging, so the way to assert on them is to attach a capturing handler
to the package's logger and look at ``record.event``.
"""

import json
import logging

import pytest
from django.test import Client

LOGGER_NAME = "wide_events"


class CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


class EventLog:
    """Assertion-friendly view over the captured log records.

    ``event`` is the dict the middleware attaches via ``extra={"event": ...}``; the
    record itself is kept around for level/exc_info assertions and for feeding real
    filters (``TailSampling``) in tests that exercise sampling.
    """

    def __init__(self, handler: CapturingHandler):
        self._handler = handler

    @property
    def records(self) -> list[logging.LogRecord]:
        return list(self._handler.records)

    @property
    def events(self) -> list[dict]:
        return [getattr(r, "event", {}) for r in self._handler.records]

    def one(self) -> dict:
        """The single emitted event, asserting that exactly one was emitted."""
        events = self.events
        assert len(events) == 1, f"expected exactly 1 event, got {len(events)}: {events}"
        return events[0]

    def one_record(self) -> logging.LogRecord:
        records = self.records
        assert len(records) == 1, f"expected exactly 1 record, got {len(records)}"
        return records[0]

    @property
    def last(self) -> dict:
        return self.events[-1]

    def clear(self) -> None:
        self._handler.records.clear()

    def __len__(self) -> int:
        return len(self._handler.records)

    def __bool__(self) -> bool:
        return bool(self._handler.records)


@pytest.fixture
def events():
    """Capture everything emitted on the ``wide_events`` logger during a test."""
    handler = CapturingHandler()
    logger = logging.getLogger(LOGGER_NAME)
    previous_level, previous_propagate = logger.level, logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    try:
        yield EventLog(handler)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate


@pytest.fixture
def client_quiet():
    """Client that returns the 500 instead of re-raising, for exception paths."""
    return Client(raise_request_exception=False)


@pytest.fixture
def assert_json_safe():
    """Every event must survive the trip through a JSON formatter."""

    def _assert(event: dict) -> str:
        return json.dumps(event, default=str)

    return _assert

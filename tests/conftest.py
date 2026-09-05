import json
import logging

import pytest

from wide_events.config import wide_event_settings


class _RenderEvent(logging.Filter):
    """Append the wide event payload to the log message so it shows up in
    pytest's live log / captured-log output, which only renders %(message)s."""

    def filter(self, record):
        event = getattr(record, "event", None)
        if event and not getattr(record, "_event_rendered", False):
            record.msg = f"{record.getMessage()} {json.dumps(event, indent=2, default=str)}"
            record.args = ()
            record._event_rendered = True
        return True


@pytest.fixture(autouse=True)
def render_wide_events():
    # Filters only run on the logger a record is emitted on, so attach to the
    # configured logger itself rather than the "wide_events" ancestor.
    logger = logging.getLogger(wide_event_settings.LOGGER_NAME)
    _filter = _RenderEvent()
    logger.addFilter(_filter)
    yield
    logger.removeFilter(_filter)

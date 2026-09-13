import json
import logging
import logging.config

import pytest
from django.conf import settings

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
    # dictConfig clears a logger's handlers when it reconfigures but only ever
    # *appends* its filters, so every override_settings(LOGGING=...) stacks
    # another one onto this logger. Reset and reapply, or a sampling filter from
    # an earlier test class stays in the chain and drops records this one
    # expects to keep.
    logger = logging.getLogger(wide_event_settings.LOGGER_NAME)
    logger.filters = []
    if getattr(settings, "LOGGING", None):
        logging.config.dictConfig(settings.LOGGING)

    # Filters only run on the logger a record is emitted on, so attach to the
    # configured logger itself rather than the "wide_events" ancestor.
    _filter = _RenderEvent()
    logger.addFilter(_filter)
    yield
    logger.removeFilter(_filter)

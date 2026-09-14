from tests.test_middleware import EventCaptureMixin
from django.test import TestCase, override_settings
from tests.test_sampling import sample_logging

@override_settings(LOGGING=sample_logging(1))
class TestBlockEvent(EventCaptureMixin, TestCase):

    def test_block_event(self):
        self.client.get("/event_block/")

        assert True
from tests.test_middleware import EventCaptureMixin
from django.test import TestCase, override_settings
from tests.test_sampling import sample_logging

@override_settings(LOGGING=sample_logging(1))
class TestBlockEvent(EventCaptureMixin, TestCase):

    def test_block_event(self):
        self.client.get("/event_block/")

        last_event:dict = self.handler.records[-1].event
        assert "TestBlock" in last_event
        assert "other" in last_event
        assert "non_value" not in last_event

        block:dict = last_event.get("TestBlock")
        assert block.get("is_flase")
        assert block.get("test")
        assert "timers" in block

        timers:dict = block.get("timers")
        assert "sleep_ms" in timers
        assert "sleep2_ms" in timers

        test_block:dict = block.get("test_block")
        assert "other" in test_block
        assert "path" in test_block
        assert test_block.get("path") == ("TestBlock", "test_block")
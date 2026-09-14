from tests.test_middleware import EventCaptureMixin
from django.test import TestCase, override_settings
from tests.test_sampling import sample_logging

@override_settings(LOGGING=sample_logging(1))
class TestCaptureDecoratorsNever(EventCaptureMixin, TestCase):

    def test_never_capture(self):
        self.client.get("/never/")

        assert self.handler.records == []

@override_settings(LOGGING=sample_logging(10000))
class TestCaptureDecoratorsAlways(EventCaptureMixin, TestCase):
    def test_always_capture(self):
        self.client.get("/always/")

        assert self.handler.records != []
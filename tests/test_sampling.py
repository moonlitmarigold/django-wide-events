import logging

from django.test import TestCase, override_settings
from tests.test_middleware import EventCaptureMixin
from unittest.mock import patch

from django_wide_events.filter import RandomSampling
from django_wide_events.filter.rules import (
    DEFAULT_RULES,
    BaseRule,
    ErrorRequest,
    SecurityStatus,
    ServerError,
    SlowRequest,
    WriteRequest,
)

def sample_logging(base_rate=100):
    return {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "random_sampler": {
            "()": "django_wide_events.filter.RandomSampling",
            "base_rate": base_rate,
        }
    },
    "loggers": {
        "wide_events.request": {
            "level": "INFO", "filters":["random_sampler"]
        }
    }
}


@override_settings(LOGGING=sample_logging(1))
class TestRandomSamplingKeep(EventCaptureMixin, TestCase):

    def test_sample_rate(self):
        self.client.get("/")
        assert self.handler.records != []


@override_settings(LOGGING=sample_logging())
class TestRandomSamplingLoose(EventCaptureMixin, TestCase):

    def test_leave_out_sample_rate(self):
        for x in range(10):
            self.client.get("/")
        assert len(self.handler.records) == 0


def tail_logging(base_rate=100, slow_ms=10):
    return {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "tail_sampler": {
            "()": "django_wide_events.filter.TailSampling",
            "base_rate": base_rate,
            "keep_rules": [SlowRequest(slow_ms=slow_ms)],
        }
    },
    "loggers": {
        "wide_events.request": {
            "level": "INFO", "filters":["tail_sampler"]
        }
    }
}


@override_settings(LOGGING=tail_logging())
class TestTailSampling(EventCaptureMixin, TestCase):
    """base_rate=100 with randint forced to 2, so nothing survives on the base
    rate alone - anything kept here was kept by a rule."""

    @patch.object(RandomSampling, "sample_on_base_rate", return_value=False)
    def test_slow_request_is_kept(self, base_rate):
        self.client.get("/slow/")
        assert len(self.handler.records) == 1
        assert self.event["duration_ms"] > 10

    @patch.object(RandomSampling, "sample_on_base_rate", return_value=False)
    def test_fast_request_is_dropped(self, base_rate):
        self.client.get("/")
        assert self.handler.records == []


class TestSlowRequestRule(TestCase):
    """The event is a plain dict - reading duration_ms with getattr silently
    yields None and the rule never fires."""

    def test_keeps_slow_event(self):
        assert SlowRequest(slow_ms=1000).keep(None, {"duration_ms": 1500.0}) is True

    def test_drops_fast_event(self):
        assert SlowRequest(slow_ms=1000).keep(None, {"duration_ms": 12.5}) is False

    def test_drops_event_without_duration(self):
        assert SlowRequest(slow_ms=1000).keep(None, {}) is False


class TestErrorRequestRule(TestCase):

    def _record(self, level=logging.INFO):
        return logging.LogRecord("r", level, "", 0, "request", None, None)

    def test_keeps_error_level(self):
        assert ErrorRequest().keep(self._record(logging.ERROR), {}) is True

    def test_keeps_event_with_error_payload(self):
        assert ErrorRequest().keep(self._record(), {"error": {"type": "ValueError"}}) is True

    def test_drops_plain_info_event(self):
        assert ErrorRequest().keep(self._record(), {"status_code": 200}) is False


class TestServerErrorRule(TestCase):

    def test_keeps_5xx(self):
        assert ServerError().keep(None, {"status_code": 523}) is True

    def test_keeps_missing_status(self):
        assert ServerError().keep(None, {}) is True

    def test_drops_2xx(self):
        assert ServerError().keep(None, {"status_code": 200}) is False


class TestWriteRequestRule(TestCase):
    """method is nested under the MetaData collector, not top level."""

    def test_keeps_post(self):
        assert WriteRequest().keep(None, {"meta": {"method": "POST"}}) is True

    def test_drops_get(self):
        assert WriteRequest().keep(None, {"meta": {"method": "GET"}}) is False

    def test_drops_when_method_absent(self):
        assert WriteRequest().keep(None, {"status_code": 200}) is False


class TestSecurityStatusRule(TestCase):

    def test_keeps_403(self):
        assert SecurityStatus().keep(None, {"status_code": 403}) is True

    def test_drops_200(self):
        assert SecurityStatus().keep(None, {"status_code": 200}) is False

    def test_drops_when_status_absent(self):
        assert SecurityStatus().keep(None, {}) is False


class TestLookup(TestCase):

    def test_reads_nested_path(self):
        assert BaseRule.lookup({"meta": {"method": "GET"}}, "meta.method") == "GET"

    def test_missing_path_returns_default(self):
        assert BaseRule.lookup({"meta": {}}, "meta.method") is None

    def test_non_dict_midway_returns_default(self):
        assert BaseRule.lookup({"meta": "nope"}, "meta.method") is None


def default_rules_logging(base_rate=100):
    return {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "tail_sampler": {
            "()": "django_wide_events.filter.TailSampling",
            "base_rate": base_rate,
        }
    },
    "loggers": {
        "wide_events.request": {
            "level": "INFO", "filters":["tail_sampler"]
        }
    }
}


@override_settings(
    LOGGING=default_rules_logging(),
    # WriteRequest reads meta.method, which only exists if MetaData is
    # installed - the base test settings run with COLLECTORS = [].
    WIDE_EVENTS={"COLLECTORS": ["django_wide_events.collectors.MetaData"]},
)
@patch.object(RandomSampling, "sample_on_base_rate", return_value=False)
class TestDefaultRules(EventCaptureMixin, TestCase):
    """TailSampling with no keep_rules falls back to DEFAULT_RULES. The base
    rate is forced to drop, so anything kept here was kept by a rule."""

    def test_default_rules_are_installed(self, base_rate):
        assert len(DEFAULT_RULES) == 5

    def test_keeps_server_error(self, base_rate):
        self.client.get("/523/")
        assert len(self.handler.records) == 1

    def test_keeps_unhandled_exception(self, base_rate):
        self.client.get("/boom/")
        assert len(self.handler.records) == 1
        assert self.event["error"]["type"] == "ValueError"

    def test_keeps_write(self, base_rate):
        self.client.post("/")
        assert len(self.handler.records) == 1
        assert self.event["meta"]["method"] == "POST"

    def test_keeps_security_status(self, base_rate):
        self.client.get("/403/")
        assert len(self.handler.records) == 1

    def test_drops_fast_successful_read(self, base_rate):
        self.client.get("/")
        assert self.handler.records == []

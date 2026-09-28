import logging

from django.conf import settings
from django.test import TestCase, override_settings

from tests.tasks import send_invoice, failing_task
from tests.test_middleware import EventCaptureMixin, RecordingHandler

TASK_LOGGER_NAME = "wide_events.tasks"

def return_logging():
    return {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "random_sampler": {
            "()": "django_wide_events.filter.RandomSampling",
            "base_rate": 1,
        }
    },
    "loggers": {
        "wide_events.request": {
            "level": "INFO", "filters":["random_sampler"]
        },
        "wide_events.tasks": {
            "level": "INFO", "filters": ["random_sampler"]
        },
    }
}



class TaskCaptureMixin(EventCaptureMixin):
    """Captures request events (self.handler) and task events (self.task_handler)."""

    def setUp(self):
        super().setUp()
        self.task_handler = RecordingHandler()
        self.task_logger = logging.getLogger(TASK_LOGGER_NAME)
        self.task_logger.addHandler(self.task_handler)
        self.task_logger.setLevel(logging.INFO)

    def tearDown(self):
        self.task_logger.removeHandler(self.task_handler)
        super().tearDown()

    @property
    def task_event(self):
        return self.task_handler.records[-1].event


@override_settings(
    INSTALLED_APPS=[*settings.INSTALLED_APPS, "django_wide_events.tasks.contrib.WideEventsTasksConfig"],
)
class TestDjangoTasks(TaskCaptureMixin, TestCase):

    def test_task_event(self):
        result = send_invoice.enqueue(invoice_id=7)

        assert len(self.task_handler.records) == 1
        assert self.task_handler.records[-1].levelno == logging.INFO

        event = self.task_event
        assert event.get("source") == "task"
        assert "duration_ms" in event
        assert "started_at" in event

        task = event.get("task")
        assert task.get("id") == result.id
        assert task.get("name") == "tests.tasks.send_invoice"
        assert task.get("framework") == "django_tasks"
        assert task.get("status") == "succeeded"
        assert task.get("attempt") == 1

    def test_task_event_block(self):
        send_invoice.enqueue(invoice_id=7)

        assert self.task_event.get("invoice") == {"invoice_id": 7, "sent": True}

    def test_failing_task(self):
        failing_task.enqueue()

        assert self.task_handler.records[-1].levelno == logging.ERROR
        assert self.task_event.get("task").get("status") == "failed"

        error = self.task_event.get("error")
        assert error.get("type") == "ValueError"
        assert error.get("message") == "task boom"

    def test_enqueued_from_request(self):
        self.client.get("/enqueue/")

        task_event = self.task_event
        request_event = self.event

        # the task ran inside the request, but each got its own event
        assert request_event.get("route") == "/enqueue/"
        assert "invoice" not in request_event
        assert task_event.get("invoice") == {"invoice_id": 7, "sent": True}

        # the request event links to the task it enqueued
        tasks = request_event.get("tasks")
        assert len(tasks) == 1
        assert tasks[0].get("id") == task_event.get("task").get("id")
        assert tasks[0].get("name") == "tests.tasks.send_invoice"

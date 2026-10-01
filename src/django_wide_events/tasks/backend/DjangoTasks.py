import sys

from ..Base import TaskEventBackend, TaskPhase
from ..collectors.classes import TaskInfo, TaskResult

# django.tasks.TaskResultStatus value -> status on the event
_STATUSES = {"SUCCESSFUL": "succeeded", "FAILED": "failed"}


class DjangoTaskBackend(TaskEventBackend):

    backend_name = "django_tasks"

    # adapters: django.tasks signal arguments -> the dataclass the collector hooks receive

    @staticmethod
    def task_info(sender, task_result, **kwargs):
        task = task_result.task
        return TaskInfo(
            task_id=task_result.id,
            name=task.module_path,
            framework=DjangoTaskBackend.backend_name,
            backend=task_result.backend,
            queue=task.queue_name,
            priority=task.priority,
            enqueued_at=task_result.enqueued_at,
            # a worker id is appended on every attempt, so nothing is there yet on enqueue
            attempt=len(task_result.worker_ids),
            worker=task_result.worker_ids[-1] if task_result.worker_ids else None,
        )

    @staticmethod
    def task_result(sender, task_result, **kwargs):
        status = task_result.status.value
        return TaskResult(
            status=_STATUSES.get(status, status.lower()),
            # django.tasks only keeps the formatted traceback, but task_finished is
            # sent from inside the except block, so the live exception is still set
            exception=sys.exception(),
        )

    signals = {
        "on_enqueued" : (TaskPhase.on_enqueued, task_info),
        "on_start": (TaskPhase.on_start, task_info),
        "on_finish": (TaskPhase.on_finish, task_result),
        "on_failure" : (TaskPhase.on_failure, task_result),
    }

    def connect(self):
        from django.tasks.signals import task_enqueued, task_started, task_finished

        task_enqueued.connect(self.receivers.get(TaskPhase.on_enqueued), dispatch_uid="wide_events.task_enqueued")
        task_started.connect(self.receivers.get(TaskPhase.on_start), dispatch_uid="wide_events.task_started")
        task_finished.connect(self.on_finish, dispatch_uid="wide_events.task_finished")

    def on_finish(self, sender, task_result, **kwargs):

        if task_result.errors:
            self.receivers.get(TaskPhase.on_failure)(sender, task_result)

        self.receivers.get(TaskPhase.on_finish)(sender, task_result)

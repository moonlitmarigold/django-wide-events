from datetime import datetime, timezone

from ...context import ContextEvent
from ..context import TaskContext
from .Base import TaskCollector
from ..events import TaskEventBlock


class SimpleBlock(TaskEventBlock):
    namespace = "task"
    append_list = True

class QueueWait(TaskCollector):

    def on_start(self, info):
        if info.enqueued_at is None:
            return
        wait = datetime.now(timezone.utc) - info.enqueued_at
        self.set(**{
            "enqueued_at": info.enqueued_at.isoformat(timespec='milliseconds'),
            "queue_wait_ms": round(wait.total_seconds() * 1000, 2),
        })


class Attempt(TaskCollector):

    def on_start(self, info):
        self.set(**{"attempt": info.attempt, "worker": info.worker})


class EnqueuedInCaller(TaskCollector):
    # Runs in the caller's context: a task enqueued from inside another task goes onto
    # that task's event, otherwise onto the request event.

    def on_enqueued(self, info):
        SimpleBlock.from_kwargs(**{
            "id": info.task_id,
            "name": info.name,
            "framework": info.framework,
            "queue": info.queue,
        })

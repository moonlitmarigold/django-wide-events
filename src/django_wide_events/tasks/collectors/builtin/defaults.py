import traceback
from datetime import datetime, timezone

from ....config import wide_event_settings
from ....event_blocks.TimerEventBlock import _Timer
from ...context import TaskState
from ...events import TaskExceptionEvent
from ..Base import TaskCollector
from .registry import builtin_task_collector


@builtin_task_collector
class TaskIdentity(TaskCollector):

    def on_start(self, info):
        self.set(
            source="task",
            task={
                "id": info.task_id,
                "name": info.name,
                "framework": info.framework,
                "backend": info.backend,
                "queue": info.queue,
                "priority": info.priority,
            },
        )


@builtin_task_collector
class Timing(TaskCollector):
    # Collectors are singletons per backend, so the timer lives in the per-task state
    # instead of on the instance like the request Duration collector.

    def on_start(self, info):
        self.set(started_at=datetime.now(timezone.utc).isoformat(timespec='milliseconds'))
        TaskState.set(timer=_Timer(lambda ms: self.set(duration_ms=ms)).start_timer())

    def on_finish(self, info):
        timer = TaskState.get().get("timer")
        if timer:
            timer.stop_timer()




@builtin_task_collector
class Status(TaskCollector):

    def on_finish(self, info):
        self.set(task={"status": info.status})


@builtin_task_collector
class Error(TaskCollector):

    def on_failure(self, info):
        exception = info.exception
        if exception is None:
            return
        TaskExceptionEvent.save_error(
            type(exception).__name__,
            str(exception),
            "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        )


@builtin_task_collector
class StaticFields(TaskCollector):

    def on_start(self, info):
        self.set(**wide_event_settings.STATIC_FIELDS)

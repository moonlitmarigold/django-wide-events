"""Celery adapter: one wide event per task, correlated back to the request
that queued it.

Wire it once, anywhere the worker imports (``celery.py`` next to your app):

    from django_wide_events.contrib.celery import install
    install()

Every task then emits one event. No decorator per task, and nothing to remember
when someone adds a new one — this is the middleware equivalent for the worker.
"""

from celery import current_task
from celery.signals import (
    before_task_publish,
    task_failure,
    task_postrun,
    task_prerun,
)

from ..context import ContextEvent, event

TRACE_HEADER = "wide_event_trace_id"
PARENT_HEADER = "wide_event_parent_id"

_handles: dict[str, ContextEvent] = {}


def install(logger: str = "wide_events.request") -> None:
    _publish.logger = _prerun.logger = _postrun.logger = logger
    before_task_publish.connect(_publish, weak=False)
    task_prerun.connect(_prerun, weak=False)
    task_failure.connect(_failure, weak=False)
    task_postrun.connect(_postrun, weak=False)


def _publish(sender=None, headers=None, **kwargs):
    """Caller side: stamp the current event's trace onto the outgoing message."""
    current = event.get()
    if current is None or headers is None:
        return
    headers[TRACE_HEADER] = current.get("trace_id") or current.get("request_id")
    headers[PARENT_HEADER] = current.get("request_id")


def _prerun(task_id=None, task=None, **kwargs):
    request = getattr(task, "request", None)
    _handles[task_id] = ContextEvent.init(
        source="task",
        request_id=task_id,
        task=getattr(task, "name", None),
        trace_id=getattr(request, TRACE_HEADER, None),
        parent_request_id=getattr(request, PARENT_HEADER, None),
        retries=getattr(request, "retries", 0),
    )


def _failure(task_id=None, exception=None, **kwargs):
    event.set(
        outcome="error",
        error={"type": type(exception).__name__, "message": str(exception)},
    )


def _postrun(task_id=None, state=None, **kwargs):
    import logging

    handle = _handles.pop(task_id, None)
    if handle is None:
        return
    finished = handle.drop()
    finished.setdefault("outcome", "ok")
    finished["state"] = state
    log = logging.getLogger(_postrun.logger)
    log.log(
        logging.ERROR if finished["outcome"] == "error" else logging.INFO,
        "task",
        extra={"event": finished},
    )

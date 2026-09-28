from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from ..Base import TaskEventBackend

# framework name -> dotted path of its backend class. Paths are only imported when
# a framework is selected in WIDE_EVENTS["TASK_BACKENDS"], so an unused framework
# (django.tasks on Django < 6.0, celery when not installed) is never imported.
TASK_BACKENDS: dict[str, str] = {
    "django_tasks": "django_wide_events.tasks.backend.DjangoTasks.DjangoTaskBackend",
}
# one instance per backend: signal receivers are bound methods, which the
# dispatcher only holds weakly, so something has to keep the instance alive
_INSTANCES: dict[str, TaskEventBackend] = {}


def get_task_backend(name: str) -> TaskEventBackend:
    """Return the backend for a framework name, or for a dotted path to a custom backend class."""
    backend = _INSTANCES.get(name)
    if backend is None:
        backend = _INSTANCES[name] = _load(name)()
    return backend


def get_task_backends() -> list[TaskEventBackend]:
    from ...config import wide_event_settings

    return [get_task_backend(name) for name in wide_event_settings.TASK_BACKENDS]


def _load(name: str) -> type[TaskEventBackend]:
    path = TASK_BACKENDS.get(name, name)
    if "." not in path:
        raise ImproperlyConfigured(
            f"Unknown task backend {name!r}, use one of {sorted(TASK_BACKENDS)} or a dotted path"
        )
    try:
        cls = import_string(path)
    except ImportError as e:
        raise ImproperlyConfigured(f"Could not import task backend {name!r} ({path}): {e}") from e
    if not (isinstance(cls, type) and issubclass(cls, TaskEventBackend)):
        raise ImproperlyConfigured(f"Task backend {path!r} is not a TaskEventBackend subclass")
    return cls

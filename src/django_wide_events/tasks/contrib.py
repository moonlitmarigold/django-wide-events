from django.apps import AppConfig

class WideEventsTasksConfig(AppConfig):
    name = "django_wide_events.tasks"
    label = "wide_events_tasks"

    def ready(self):
        from .backend import get_task_backend
        from ..config import wide_event_settings

        _settings = wide_event_settings.TASK

        for backend in _settings.get("BACKENDS"):
            get_task_backend(backend).connect()

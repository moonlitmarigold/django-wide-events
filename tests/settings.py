from uuid import uuid4

SECRET_KEY = "tests"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "tests.urls"

MIDDLEWARE = [
    "django_wide_events.middleware.wide_event_middleware.WideEventMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_wide_events.middleware.session_traceability_middleware.SessionID",
]

SESSION_ENGINE="django.contrib.sessions.backends.cache"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

# Runs every task inline on enqueue(), firing enqueued -> started -> finished
TASKS = {
    "default": {
        "BACKEND": "django.tasks.backends.immediate.ImmediateBackend",
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


def _make_request_id() -> str:
    return uuid4().hex


WIDE_EVENTS = {
    "COLLECTORS": [],
    "STATIC_FIELDS": {"service": "tests", "env": "test"},
    "LOGGER_NAME": "wide_events.request",
    # only connects when a test installs the tasks app; set here rather than next to that
    # override because override_settings runs ready() before other overrides apply
    "TASK": {"BACKENDS": ["django_tasks"]},
    "REQUEST_ID": {
        "TRUST_ID_HEADER": True,
        "RESPONSE_HEADER": "X-Request-Id",
        "ID_GENERATOR": _make_request_id,
    },
}
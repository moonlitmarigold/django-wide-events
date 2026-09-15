from uuid import uuid4

SECRET_KEY = "tests"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "tests.urls"

MIDDLEWARE = [
    "django_wide_events.middleware.wide_event_middleware.WideEventMiddleware",
]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

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
    "REQUEST_ID": {
        "TRUST_ID_HEADER": True,
        "RESPONSE_HEADER": "X-Request-Id",
        "ID_GENERATOR": _make_request_id,
    },
}
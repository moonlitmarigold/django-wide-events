"""Minimal Django settings for the test project.

Small on purpose: enough of a real Django to route a request through middleware,
resolve a view, hit the session/auth machinery and emit a log record. No app of our
own is installed beyond ``django_wide_events`` itself.
"""

SECRET_KEY = "not-a-secret-this-is-a-test-project"
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django_wide_events",
]

MIDDLEWARE = [
    # NOTE: "django_wide_events.middleware.WideEventMiddleware" goes here, first,
    # once it exists. Until then the harness proves everything around it works.
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "tests.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The settings the package itself reads. Mirrors EXAMPLE_USAGE.md; tests that need
# something different use the pytest-django ``settings`` fixture to override.
WIDE_EVENTS = {
    "STATIC_FIELDS": {
        "service": "test-project",
        "env": "test",
        "commit": "0000000",
    },
    "EXCLUDE_PATHS": ["/health"],
    "SAMPLING": {
        "BASE_RATE": 1,        # keep everything by default so assertions are simple
        "SLOW_MS": 1000,
    },
}

# Deliberately NOT configuring handlers here. The ``events`` fixture attaches a
# capturing handler to the "wide_events" logger per-test, which is both faster and
# keeps test output clean. Tests that care about real formatter/filter wiring build
# their own LOGGING dict with the ``settings`` fixture.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "WARNING"},
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests

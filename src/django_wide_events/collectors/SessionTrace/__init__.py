from .Base import SessionTrace

DEFAULT_SESSION_TRACE = [
    "django_wide_events.collectors.SessionTrace.[[[["
]

from .builtin import CheckPaths, CheckViewName

BUILTIN_SESSION_TRACE = [
    CheckPaths, CheckViewName
]
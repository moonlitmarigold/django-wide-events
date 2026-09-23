from .Base import SessionTrace

DEFAULT_SESSION_TRACE = [
    # dotted paths of user-provided session tracers go here
]

from .builtin import CheckPaths, CheckViewName

BUILTIN_SESSION_TRACE = [
    CheckPaths, CheckViewName
]
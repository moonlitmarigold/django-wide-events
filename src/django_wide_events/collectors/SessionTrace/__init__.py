from .Base import SessionTrace as BaseSessionTrace

from .builtin import CheckPaths, CheckViewName, CheckResponseError, CheckMustTrace
from .builtin import CheckUserAgent, CheckNamespaces, CheckPrivacySignal, CheckAuthenticatedOnly

DEFAULT_SESSION_TRACE = [
    CheckUserAgent, CheckNamespaces,
    CheckPrivacySignal, CheckAuthenticatedOnly
]

BUILTIN_SESSION_TRACE = [
    CheckResponseError, CheckMustTrace,
    CheckPaths, CheckViewName
]
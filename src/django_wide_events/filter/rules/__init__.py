from .Base import BaseRule

from .ErrorRequest import ErrorRequest
from .SecurityStatus import SecurityStatus
from .ServerError import ServerError
from .SlowRequest import SlowRequest
from .WriteRequest import WriteRequest

DEFAULT_RULES = [
    ErrorRequest(),
    ServerError(),
    SlowRequest(),
    WriteRequest(),
    SecurityStatus(),
]

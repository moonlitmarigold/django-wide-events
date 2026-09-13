from .Base import *

def register_collectors(cls):
    DEFAULT_COLLECTORS.append(f'wide_events.collectors.{cls.__name__}')
    return cls

from .User import User
from .ExtenededMetaData import MetaData

DEFAULT_COLLECTORS = [
    "wide_events.collectors.User",
    "wide_events.collectors.MetaData",
]
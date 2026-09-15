from .Base import *

def register_collectors(cls):
    DEFAULT_COLLECTORS.append(f'django_wide_events.collectors.{cls.__name__}')
    return cls

from .User import User
from .ExtenededMetaData import MetaData

DEFAULT_COLLECTORS = [
    "django_wide_events.collectors.User",
    "django_wide_events.collectors.MetaData",
]
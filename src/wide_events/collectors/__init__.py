from .Base import *

def register_collectors(cls):
    DEFAULT_COLLECTORS.append(f'wide_events.collectors.{cls.__name__}')
    return cls

DEFAULT_COLLECTORS = []
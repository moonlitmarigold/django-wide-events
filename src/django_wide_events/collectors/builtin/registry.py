from typing import TypeVar

from ..Base import Collector

_CollectorT = TypeVar("_CollectorT", bound=Collector)
_FactoryT = TypeVar("_FactoryT")

BUILTIN_COLLECTORS: list[type[Collector]] = []
# Factories are classes whose instances build a Collector (e.g. RequestIDFactory).
FACTORY_COLLECTORS: list[type] = []


def builtin_collector(cls: type[_CollectorT]) -> type[_CollectorT]:
    BUILTIN_COLLECTORS.append(cls)
    return cls


def factory_collector(factory: type[_FactoryT]) -> type[_FactoryT]:
    FACTORY_COLLECTORS.append(factory)
    return factory
from typing import TypeVar

from ..Base import TaskCollector

_TaskCollectorT = TypeVar("_TaskCollectorT", bound=TaskCollector)

BUILTIN_TASK_COLLECTORS: list[type[TaskCollector]] = []


def builtin_task_collector(cls: type[_TaskCollectorT]) -> type[_TaskCollectorT]:
    BUILTIN_TASK_COLLECTORS.append(cls)
    return cls

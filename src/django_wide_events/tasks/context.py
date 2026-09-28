from ..context import BaseContext, ContextEvent
from contextvars import ContextVar, Token

_task: ContextVar[dict | None] = ContextVar("django_wide_events.task", default=None)
_task_token:ContextVar[list | None] = ContextVar("django_wide_events.task_token", default=None)



class TaskTokenContext(BaseContext):

    _contex_var = _task_token

    @staticmethod
    def add(_token:Token):
        _l = TaskTokenContext._contex_var.get()
        if _l:
            _l.append(_token)
        else:
            _l = [_token]
        TaskTokenContext._contex_var.set(_l)

    @classmethod
    def init(cls):
        _cls = super().init()
        _cls.add(_cls.token)

    @staticmethod
    def get():
        return TaskTokenContext._contex_var.get()

class TaskContext(ContextEvent):

    _contex_var = _task
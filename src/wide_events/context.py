from contextvars import ContextVar, Token
import dataclasses

_current: ContextVar[dict | None] = ContextVar("wide_events.event", default=None)

@dataclasses.dataclass
class ContextEvent:

    token: Token|None = None

    @staticmethod
    def set(**kwargs):
        ctx = ContextEvent.get()
        ctx.update(kwargs)

    @staticmethod
    def get():
        ctx = _current.get()
        if ctx is None:
            return {}
        return ctx

    def drop(self):
        if not self.token:
            return
        ctx = _current.get()
        _current.reset(self.token)
        return ctx

    @classmethod
    def init(cls):
        token = _current.set({})
        return cls(token)
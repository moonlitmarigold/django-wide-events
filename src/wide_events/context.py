from contextvars import ContextVar, Token
import dataclasses

_current: ContextVar[dict | None] = ContextVar("wide_events.event", default=None)
_blocks: ContextVar[dict | None] = ContextVar("wide_events.event", default=None)

@dataclasses.dataclass
class BaseContext:

    token: Token|None = None

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

@dataclasses.dataclass
class ContextEvent(BaseContext):

    @staticmethod
    def set(**kwargs):
        ctx = ContextEvent.get()
        ctx.update(kwargs)

    @staticmethod
    def update(**kwargs):
        ctx = ContextEvent.get()
        ContextEvent.merge(ctx, **kwargs)


    @staticmethod
    def merge(ctx:dict, **kwargs):
        for key, value in kwargs.items():
            if not isinstance(value, dict):
                ctx[key] = value
            else:
                new = ctx.setdefault(key, {})
                ctx[key] = ContextEvent.merge(new, **value)
        return ctx

    @staticmethod
    def get():
        ctx = _current.get()
        if ctx is None:
            return {}
        return ctx

@dataclasses.dataclass
class ContextBlock(BaseContext):

    @staticmethod
    def get():
        blocks = _blocks.get()
        if blocks is None:
            return {}
        return blocks

    @staticmethod
    def set(**kwargs):
        ctx = ContextBlock.get()
        for key, value in kwargs.items():
            if isinstance(value, list):
                _list_block = ctx.setdefault(key, [])
                _list_block.extend(value)
            else:
                ctx[key] = value




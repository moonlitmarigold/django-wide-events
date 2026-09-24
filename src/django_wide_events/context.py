from contextvars import ContextVar, Token
import dataclasses
from typing import ClassVar

_current: ContextVar[dict | None] = ContextVar("django_wide_events.event", default=None)
_blocks: ContextVar[dict | None] = ContextVar("django_wide_events.block", default=None)
_collectors: ContextVar[list | None] = ContextVar("django_wide_events.collectors", default=None)
_capture:ContextVar[bool | None] = ContextVar("django_wide_events.capture", default=None)
_trace:ContextVar[bool | None] = ContextVar("django_wide_events.trace", default=None)


class BlockAlreadyAttached(Exception):

    def __init__(self, key, attached, incoming):
        self.key = key
        self.attached = attached
        self.incoming = incoming
        super().__init__(
            f"{type(incoming).__name__} cannot attach at {key!r}: already claimed by "
            f"{type(attached).__name__} on this event. Use {type(incoming).__name__}"
            f".current() to reach the attached block, or set 'multiple = True' if this "
            f"block is meant to attach more than once."
        )


@dataclasses.dataclass
class BaseContext:

    token: Token|None = None
    _contex_var: ClassVar[ContextVar[dict | None]] = None

    def check_or_raise_contex_var(self):
        if self._contex_var is None:
            raise ValueError("Internal: ContextVar for Event is not set")
        return self._contex_var

    def drop(self):
        if not self.token:
            return
        ctx_var = self.check_or_raise_contex_var()
        ctx = ctx_var.get()
        ctx_var.reset(self.token)
        return ctx

    @classmethod
    def init(cls):
        _cls = cls()
        ctx_var = _cls.check_or_raise_contex_var()
        _cls.token = ctx_var.set({})
        return _cls

@dataclasses.dataclass
class ContextEvent(BaseContext):

    _contex_var = _current

    @staticmethod
    def set(**kwargs):
        ctx = ContextEvent.get()
        ctx.update(kwargs)

    @staticmethod
    def update(payload:dict, drop_none:bool=True, append_lists:bool=False):
        ctx = ContextEvent.get()
        return ContextEvent.merge(ctx, payload, drop_none, append_lists)

    @staticmethod
    def merge(ctx:dict, payload:dict, drop_none:bool=True, append_lists:bool=False):
        # payload is positional on purpose: taking it as **kwargs let a field named
        # 'ctx' raise TypeError and a field named 'drop_none' silently vanish.
        for key, value in payload.items():
            if isinstance(value, dict):
                ContextEvent.merge(ctx.setdefault(key, {}), value, drop_none, append_lists)
            else:
                if drop_none and value is None:
                    continue
                if append_lists and isinstance(value, list):
                    attached = ctx.get(key)
                    # Only list-on-list accumulates. A list landing on a scalar writes as
                    # usual -- merging there would lose the scalar silently. On nothing it
                    # writes a copy, so the caller keeps their list free of later appends.
                    if isinstance(attached, list):
                        attached.extend(value)
                        continue
                    value = list(value)
                ctx[key] = value
        return ctx

    @staticmethod
    def get():
        ctx = _current.get()
        if ctx is None:
            return {}
        return ctx

@dataclasses.dataclass
class ContextBlock(BaseContext):

    _contex_var = _blocks

    @staticmethod
    def get():
        blocks = _blocks.get()
        if blocks is None:
            return {}
        return blocks

    @staticmethod
    def attach(key:str, block, multiple:bool=False):
        ctx = ContextBlock.get()
        if multiple:
            ctx.setdefault(key, []).append(block)
            return block
        attached = ctx.get(key)
        if attached is not None:
            raise BlockAlreadyAttached(key, attached, block)
        ctx[key] = block
        return block

@dataclasses.dataclass
class ContextCollectors:

    token: Token | None = None

    @classmethod
    def init(cls):
        _cls = cls()
        _cls.token = _collectors.set([])
        return _cls

    @staticmethod
    def get():
        ctx = _collectors.get()
        if ctx is None:
            return []
        return ctx

    @staticmethod
    def set_collectors(collectors:list):
        ContextCollectors.get().extend(collectors)


    def drop(self):
        if not self.token:
            return
        _ctx = self.get()
        _collectors.reset(self.token)
        return _ctx

@dataclasses.dataclass
class ContextCapture(BaseContext):

    _contex_var = _capture

    @staticmethod
    def set(var:bool):
        ContextCapture._contex_var.set(var)

    @staticmethod
    def get():
        return ContextCapture._contex_var.get()

    @classmethod
    def init(cls):
        _cls = cls()
        ctx_var = _cls.check_or_raise_contex_var()
        _cls.token = ctx_var.set(None)
        return _cls

@dataclasses.dataclass
class ContextTrace(ContextCapture):

    _contex_var = _trace
from ..context import ContextEvent, ContextBlock
from dataclasses import dataclass
from typing import ClassVar

@dataclass
class EventBlock:

    kwargs:dict | None = None

    namespace: ClassVar[str | None] = None
    multiple: ClassVar[bool] = False
    abstract: ClassVar[bool] = True

    def __post_init__(self):
        self._attach()
        if self.kwargs:
            self.set(**self.kwargs)

    def __init_subclass__(cls, abstract=False ,**kwargs):
        super().__init_subclass__()
        cls.abstract = abstract
        if abstract:
            return

        namespace = getattr(cls, "namespace", None)
        if namespace is None:
            raise TypeError(f"{cls.namespace} must define a 'namespace' or 'abstract = True'")
        if not namespace or "." in namespace:
            raise ValueError(
                f"{cls.__name__}.namespace must be non-empty and contain no '.' (got {namespace!r})."
            )


    def set(self, **kwargs):
        ContextEvent.merge(self.get(), **kwargs)
        return self

    def _attach(self):
        if self.multiple:
            ContextBlock.set(**{self.get_namespace():[self]})
        else:
            ContextBlock.set(**{self.get_namespace():self})


    @classmethod
    def from_kwargs(cls, **kwargs):
        ctx = ContextBlock.get()
        if not cls.multiple and cls.namespace in ctx.keys():
            _cls = ctx.get(cls.namespace)
            _cls.set(**kwargs)
            return _cls
        return cls(kwargs=kwargs)

    @classmethod
    def current(cls):
        ctx = ContextBlock.get()
        _block = ctx.get(cls.namespace, None)
        if _block is None:
            return cls()

        return _block

    @staticmethod
    def get_namespace_dict(namespace:str):
        return ContextEvent.get().setdefault(namespace, {})

    def get_namespace(self):
        if not self.namespace:
            raise TypeError(f"{self.namespace} must define a 'namespace'")
        return self.namespace

    def get(self):
        return self.get_namespace_dict(self.get_namespace())

    def from_form(self, form):
        _form = dict()
        _form["form_valid"] = form.is_valid()
        if not form.is_valid():
            _form["form_error"] = form.errors.as_json()
        self.set(form=_form)
        return self
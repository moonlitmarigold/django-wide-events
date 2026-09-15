from ..context import ContextEvent, ContextBlock
from dataclasses import dataclass
from typing import ClassVar

@dataclass
class EventBlock:

    kwargs:dict | None = None

    namespace: ClassVar[str | None] = None
    parent: ClassVar[type["EventBlock"] | None] = None
    path: ClassVar[tuple[str, ...]] = ()
    multiple: ClassVar[bool] = False
    drop_none:ClassVar[bool] = True
    use_namespace_on_write:ClassVar[bool] = True

    abstract: ClassVar[bool] = True

    def __post_init__(self):
        self._attach()
        if self.kwargs:
            self.set(**self.kwargs)

    def __init_subclass__(cls, abstract=False ,**kwargs):
        super().__init_subclass__(**kwargs)
        cls.abstract = abstract
        if abstract:
            return

        namespace = getattr(cls, "namespace", None)
        if namespace is None:
            raise TypeError(f"{cls.__name__} must define a 'namespace' or 'abstract = True'")
        if not isinstance(namespace, str):
            raise TypeError(
                f"{cls.__name__}.namespace must be a str (got {type(namespace).__name__})."
            )
        if not namespace or "." in namespace:
            raise ValueError(
                f"{cls.__name__}.namespace must be non-empty and contain no '.' (got {namespace!r})."
            )

        cls.path = cls._build_path(namespace)

    @classmethod
    def _build_path(cls, namespace:str):
        parent = getattr(cls, "parent", None)
        if parent is None:
            return (namespace,)
        if not (isinstance(parent, type) and issubclass(parent, EventBlock)):
            raise TypeError(
                f"{cls.__name__}.parent must be an EventBlock subclass (got {parent!r})."
            )
        if parent.abstract:
            raise TypeError(
                f"{cls.__name__}.parent is {parent.__name__}, which is abstract and has "
                f"no namespace of its own to nest under."
            )
        if parent.multiple:
            raise TypeError(
                f"{cls.__name__} cannot nest under {parent.__name__}: it has "
                f"'multiple = True', so it renders as a list and has no single dict to "
                f"nest into."
            )
        return parent.path + (namespace,)

    @classmethod
    def get_key(cls):
        # '.' is banned inside a namespace, so joining on it keeps every path unique --
        # 'picture.timing' and 's3.timing' stay distinct despite the shared leaf name.
        return ".".join(cls.get_path())

    @classmethod
    def get_path(cls):
        if not cls.path:
            raise TypeError(f"{cls.__name__} must define a 'namespace'")
        return cls.path

    def set(self, **kwargs):
        if self.use_namespace_on_write:
            ContextEvent.merge(self.get(), kwargs, self.drop_none)
        else:
            ContextEvent.update(kwargs, self.drop_none)
        return self

    def _attach(self):
        ContextBlock.attach(self.get_key(), self, self.multiple)

    @classmethod
    def from_kwargs(cls, **kwargs):
        if not cls.multiple:
            attached = cls.current()
            if attached is not None:
                return attached.set(**kwargs)
        return cls(kwargs=kwargs)

    @classmethod
    def current(cls):
        _block = ContextBlock.get().get(cls.get_key())
        if _block is None:
            return None
        if cls.multiple:
            return _block[-1]
        else:
            return _block

    def get(self):
        ctx = ContextEvent.get()
        for part in self.get_path():
            ctx = ctx.setdefault(part, {})
        return ctx

    def from_form(self, form):
        _form = dict()
        _form["form_valid"] = form.is_valid()
        if not form.is_valid():
            _form["form_error"] = form.errors.as_json()
        self.set(form=_form)
        return self

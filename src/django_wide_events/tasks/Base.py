from .context import TaskContext, TaskTokenContext, TaskState, ContextEvent
import logging
from ..config import wide_event_settings
from typing import ClassVar
from enum import StrEnum, auto
from dataclasses import dataclass
from typing import Callable
import functools
from .events import TaskHookErrorEvent
import traceback
from ..collectors.builtin import HookPosition, Change
from .collectors.builtin import BUILTIN_TASK_COLLECTORS
from ..event_blocks import EventBlock

class TaskPhase(StrEnum):

    on_enqueued = auto()
    on_start = auto()
    on_finish = auto()
    on_failure = auto()

class ContextDict:

    @staticmethod
    def init():
        TaskTokenContext.init()

        task = TaskContext.init()
        TaskTokenContext.add(task.token)

        state = TaskState.init()
        TaskTokenContext.add(state.token)

    @staticmethod
    def drop():
        tokens = TaskTokenContext.get()

        token_context = TaskTokenContext(tokens[0])
        token_context.drop()

        task_context = TaskContext(tokens[1])
        task_state = TaskState(tokens[2])
        task_state.drop()

        return task_context.drop()

@dataclass(eq=False)
class SignalCallable:

    _func:Callable
    _adapter:Callable|None

    __func = None

    def init__func(self):
        if self._adapter:
            self.__func = lambda *args, **kwargs: self._func(self._adapter(*args, **kwargs))
        else:
            self.__func = lambda *args, **kwargs: self._func(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        if not self.__func:
            self.init__func()
        return self.__func(*args, **kwargs)

@dataclass
class SimpleMaskCollector:

    _func:Callable
    key:str | list[str]
    name:str

    def __post_init__(self):
        if isinstance(self.key, str):
            self.key = [self.key]

    def __getattr__(self, item):
        if item in self.key:
            return self._func
        raise AttributeError()

    @staticmethod
    def override_check_function(_cls, hook):
        if not hasattr(hook, "name"):
            return False
        return _cls == hook.name and isinstance(hook, SimpleMaskCollector)

class TaskEventBackend:

    hooks:ClassVar[StrEnum]
    backend_name:ClassVar[str] = "no_backend"

    signals:ClassVar[dict] = {}
    # key: native signal
    # value: tuple:
    #       str[Hook], lambda: adapter
    HookPositionChanges:ClassVar[tuple[HookPosition, ...] ] = ()
    builtin_HookPositionChanges = (
        HookPosition(
            "init", (
                Change(TaskPhase.on_enqueued, 0),
                Change(TaskPhase.on_start, 0)
            ),
            default_class_check_function=SimpleMaskCollector.override_check_function
        ),
        HookPosition(
            "finish", (
                Change(TaskPhase.on_finish, -1),
            ),
            default_class_check_function=SimpleMaskCollector.override_check_function
        ),
        HookPosition(
            "enqueued", (
                Change(TaskPhase.on_enqueued, -1),
            ),
            default_class_check_function=SimpleMaskCollector.override_check_function
        )
    )


    def __init__(self):
        _settings = wide_event_settings
        self.logger = logging.getLogger(_settings.TASK_LOGGER_NAME)

        _task_settings = _settings.TASK

        # builtin collectors always run, the configured ones replace the defaults
        self._collector_classes = [*BUILTIN_TASK_COLLECTORS, *_task_settings.get("TASK_COLLECTORS")]

        self._collector_classes = [c() for c in self._collector_classes]

        # Add builtin Context Managing
        self._collector_classes.extend([
            SimpleMaskCollector(self.init_ctx, [TaskPhase.on_start, TaskPhase.on_enqueued], name="init"),
            SimpleMaskCollector(self.finish, TaskPhase.on_finish, name="finish"),
            SimpleMaskCollector(self.enqueue_end, TaskPhase.on_enqueued, name="enqueued")
        ])

        self.collectors, self.receivers = self.return_collectors()
        # Shape:
        #   key -> signal/hook
        #   value -> list of collectors

    def return_collectors(self):
        output_collectors = {}
        receivers = {}

        for native_signal, (hook_str, _adapter) in self.signals.items():
            output_collectors[hook_str] = [
                i for i, x in
                [(index, getattr(col, hook_str, None)) for index, col in enumerate(self._collector_classes)]
                if x is not None
            ]

            receivers[native_signal] = SignalCallable(
                functools.partial(self.run_collector_hooks, hook_str),
                _adapter
            )

        for change in [*self.HookPositionChanges, *self.builtin_HookPositionChanges]:
            change.apply(self._collector_classes, output_collectors)

        return output_collectors, receivers

    def connect(self):
        raise NotImplemented

    @staticmethod
    def init_ctx(*args, **kwargs):
        ContextDict.init()

    @staticmethod
    def _log(event:dict):
        if "task" not in event:
            return True
        _task = event.get("task", {})
        return "status" not in _task or _task.get("status") == "failed"

    def finish(self, *args, **kwargs):
        event = ContextDict.drop()

        if self._log(event):
            self.logger.error("task", extra={"event":event})
        else:
            self.logger.info("task", extra={"event":event})

    @staticmethod
    def enqueue_end(*args, **kwargs):
        event = ContextDict.drop().get("task", None)
        if not event:
            return
        caller = TaskContext if TaskContext._contex_var.get() is not None else ContextEvent
        caller.update({"tasks": [event]}, append_lists=True, drop_none=True)


    def run_collector_hooks(self, hook_str, *args, **kwargs):
        _collectors = self.collectors.get(hook_str, [])
        for col_index in _collectors:
            try:
                col = self._collector_classes[col_index]
                getattr(col, hook_str)(*args, **kwargs)
            except Exception as e:
                TaskHookErrorEvent.save_hook_error(
                    hook_str,  "".join(traceback.format_exception(type(e), e, e.__traceback__)),
                )




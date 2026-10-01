from ipaddress import ip_network

from .context import TaskContext, TaskTokenContext, TaskState
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

    def __post_init__(self):
        if self._adapter:
            self.__func = lambda *args, **kwargs: self._func(self._adapter(*args, **kwargs))
        else:
            self.__func = lambda *args, **kwargs: self._func(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.__func(*args, **kwargs)

@dataclass
class MaskCollector:

    _start_func:Callable
    _finish_func:Callable


    def on_start(self, *args, **kwargs):
        self._start_func()

    def on_finish(self, *args, **kwargs):
        self._finish_func()

@dataclass
class MaskEnqueueCollector:

    _func:Callable

    def on_enqueue(self, *args, **kwargs):
        self._func()

class TaskEventBackend:

    hooks:ClassVar[StrEnum]
    backend_name:ClassVar[str] = "no_backend"

    signals:ClassVar[dict] = {}
    # key: native signal
    # value: tuple:
    #       str[Hook], lambda: adapter
    HookPositionChanges:ClassVar[tuple[HookPosition, ...] ] = ()
    builtin_HookPositionChanges = (

    )


    def __init__(self):
        _settings = wide_event_settings
        self.logger = logging.getLogger(_settings.TASK_LOGGER_NAME)

        _task_settings = _settings.TASK

        # builtin collectors always run, the configured ones replace the defaults
        self._collector_classes = [*BUILTIN_TASK_COLLECTORS, *_task_settings.get("TASK_COLLECTORS")]

        self._collector_classes = [c() for c in self._collector_classes]

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

            receivers[hook_str] = SignalCallable(
                functools.partial(self.run_collector_hooks, hook_str),
                _adapter
            )

        for change in [*self.HookPositionChanges, *self.builtin_HookPositionChanges]:
            change.apply(self._collector_classes, output_collectors)

        # Add the start and finish
        mask_collector = MaskCollector(self.init_ctx, self.finish)
        self._collector_classes.append(mask_collector)
        index = len(self._collector_classes) - 1

        output_collectors[TaskPhase.on_start] = [index, *output_collectors[TaskPhase.on_start]]
        output_collectors[TaskPhase.on_finish] = [*output_collectors[TaskPhase.on_finish], index]

        # Add write to the request context
        self._collector_classes.extend(
            [MaskEnqueueCollector(self.init_ctx), MaskEnqueueCollector(self.drop_context_to_request_event)]
        )

        output_collectors[TaskPhase.on_enqueued] = [index+1, *output_collectors[TaskPhase.on_enqueued], index+2]

        return output_collectors, receivers

    def connect(self):
        raise NotImplemented

    @staticmethod
    def init_ctx(*args, **kwargs):
        ContextDict.init()

    def finish(self, *args, **kwargs):
        event = ContextDict.drop()
        self.logger.info("task", extra={"event":event}) # Improve: better log logic

    @staticmethod
    def drop_context_to_request_event(*args, **kwargs):
        event = ContextDict.drop()
        EventBlock.set(*event)


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



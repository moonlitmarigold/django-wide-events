from .context import TaskContext, TaskTokenContext
import logging
from ..config import wide_event_settings
from typing import ClassVar
from enum import StrEnum
from enum import auto
from dataclasses import dataclass
from typing import Callable

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

    @staticmethod
    def drop():
        tokens = TaskTokenContext.get()

        token_context = TaskTokenContext(tokens[0])
        token_context.drop()

        task_context = TaskContext(tokens[1])
        print(task_context)
        return task_context.drop()

@dataclass
class SignalCallable:

    _func:Callable
    _adapter:Callable

    def __call__(self, *args, **kwargs):
        return self._func(self._adapter(*args, **kwargs))


class TaskEventBackend:

    hooks:ClassVar[StrEnum]
    backend_name:ClassVar[str] = "no_backend"

    signals:ClassVar[dict] = {}
    # key: native signal
    # value: tuple:
    #       str[Hook], lambda: adapter
    collector_modify_func:Callable | None = None


    def __init__(self):
        _settings = wide_event_settings
        self.logger = logging.getLogger(_settings.TASK_LOGGER_NAME)

        _task_settings = _settings.TASK

        self._collector_classes = list(_task_settings.get("TASK_COLLECTORS"))

        self.collectors = self.return_collectors()
        # Shape:
        #   key -> signal/hook
        #   value -> list of collectors

    def return_collectors(self):
        output_collectors = {}

        for native_signal, (hook_str, _adapter) in self.signals.items():
            _collectors = list()
            if hook_str == TaskPhase.on_enqueued:
                _collectors.append(self.init_ctx)

            for col in self.collectors:
                hook_func = getattr(col, hook_str, None)
                if hook_func:
                    _collectors.append(
                        hook_func
                    )


            if hook_str == TaskPhase.on_finish:
                _collectors.append(self.finish)

            output_collectors[hook_str] = _collectors

        return output_collectors

    def connect(self):
        raise NotImplemented

    @staticmethod
    def init_ctx(*args, **kwargs):
        ContextDict.init()

    def finish(self, *args, **kwargs):
        event = ContextDict.drop()
        self.logger.info("task", extra={"event":event}) # Improve: better log logic


    def run_collector_hooks(self, hook_str, *args, **kwargs):
        _collectors = self.collectors.get(hook_str, [])

        for col in _collectors:
            try:
                col(*args, **kwargs)
            except Exception as e:
                # save as an error
                ...
        pass



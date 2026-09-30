from ..event_blocks import EventBlock
from ..event_blocks.ErrorBlocks import ExceptionEvent, HookErrorEvent
from .context import TaskContext, TaskState

class TaskEventBlock(EventBlock):

    abstract = True
    _context_event = TaskContext

class TaskStateBlock(EventBlock):

    abstract = True
    _context_event = TaskState

class TaskHookErrorEvent(HookErrorEvent):

    _context_event = TaskContext

class TaskExceptionEvent(ExceptionEvent):

    _context_event = TaskContext

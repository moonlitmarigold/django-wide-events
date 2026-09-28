from .context import TaskContext, TaskTokenContext
import logging

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
        return task_context.drop()


class TaskEventBackend:

    logger_name = "wide_events.tasks"

    def __init__(self):
        self.logger = logging.getLogger(self.logger_name)

    def return_collectors(self):
        raise NotImplemented

    def connect(self):
        raise NotImplemented

    def enqueued(self, *args, **kwargs):
        ContextDict.init()

        TaskContext.set(test=True)

    def finish(self, *args, **kwargs):
        self.logger.info("task", extra={"event":ContextDict.drop()})



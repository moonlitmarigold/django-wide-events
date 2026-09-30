from ..events import TaskContext, TaskStateBlock

class TaskCollector:

    @property
    def event(self):
        return TaskContext.get()

    @property
    def state(self):
        return TaskStateBlock

    @staticmethod
    def set(**kwargs):
        TaskContext.update(kwargs)

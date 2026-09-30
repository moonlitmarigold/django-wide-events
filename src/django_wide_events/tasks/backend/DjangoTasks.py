from ..Base import TaskEventBackend, TaskPhase

class DjangoTaskBackend(TaskEventBackend):

    signals = {
        "on_enqueued" : (TaskPhase.on_enqueued, lambda _: 1)
    }

    def connect(self):
        from django.tasks.signals import task_enqueued, task_started, task_finished

        task_enqueued.connect(self.enqueued, dispatch_uid="wide_events.task_enqueued")
        #task_started.connect(self.on_task_started, dispatch_uid="wide_events.task_started")
        task_finished.connect(self.finish, dispatch_uid="wide_events.task_finished")

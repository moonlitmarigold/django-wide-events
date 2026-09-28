from ..Base import TaskEventBackend

class DjangoTaskBackend(TaskEventBackend):

    def connect(self):
        from django.tasks.signals import task_enqueued, task_started, task_finished

        task_enqueued.connect(self.enqueued, dispatch_uid="wide_events.task_enqueued")
        #task_started.connect(self.on_task_started, dispatch_uid="wide_events.task_started")
        task_finished.connect(self.finish, dispatch_uid="wide_events.task_finished")

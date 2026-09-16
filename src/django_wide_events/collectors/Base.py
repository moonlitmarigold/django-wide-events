import enum
from ..context import ContextEvent

class CollectorHooks(enum.Enum):

    on_create = 'on_create'
    on_exception = 'on_exception'
    on_finish = 'on_finish'
    on_finish_no_response = 'on_finish_no_response'

class Collector:

    @property
    def event(self):
        return ContextEvent.get()

    @staticmethod
    def set(**kwargs):
        ContextEvent.update(kwargs)

    def on_create(self, request):
        return None

    def on_finish(self, request, response):
        return None

    def on_finish_no_response(self, request, response=None):
        return None

    def on_exception(self, request, exception):
        return None

    def __call__(self, run_func:str, *args):
        if not hasattr(self, run_func):
            raise  # Implement fitting error
        func = getattr(self, run_func)
        func(*args)

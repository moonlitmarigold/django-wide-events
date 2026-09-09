import enum

class CollectorHooks(enum.Enum):

    on_create = 'on_create'
    on_exception = 'on_exception'
    on_finish = 'on_finish'

class Collector:

    def on_create(self, request, event:dict):
        return None

    def on_finish(self, request, response, event:dict):
        return None

    def on_exception(self, request, exception, event:dict):
        return None

    def __call__(self, run_func:str, *args):
        if not hasattr(self, run_func):
            raise  # Implement fitting error
        func = getattr(self, run_func)
        func(*args)

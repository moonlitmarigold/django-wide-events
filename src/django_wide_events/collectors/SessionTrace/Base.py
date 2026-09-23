

class SessionTrace:

    def should_trace(self, request, view_func, view_args, view_kwargs) -> bool:
        ...
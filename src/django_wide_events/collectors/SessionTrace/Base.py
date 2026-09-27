

class SessionTrace:

    # Logged as session.session_tracer when this tracer decides. Defaults to the class name.
    name: str | None = None

    def get_name(self) -> str:
        return self.name or type(self).__name__

    # True: always trace, False: never trace, None: no opinion (the next tracer decides)
    def should_trace(self, request, response) -> bool | None:
        ...

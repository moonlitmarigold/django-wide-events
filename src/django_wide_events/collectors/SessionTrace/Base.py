

class SessionTrace:

    # True: always trace, False: never trace, None: no opinion (the next tracer decides)
    def should_trace(self, request, response) -> bool | None:
        ...

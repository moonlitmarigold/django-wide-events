from .Base import EventBlock

class SessionStatus:

    new_id = "new_session_id"
    existing_id = "existing_session_id"
    no_existing_session = "no_existing_session"
    not_traced = "not_traced"



class SessionIDAddEvent(EventBlock):

    namespace = "session"
    use_namespace_on_write = True
    drop_none = False

    @classmethod
    def init(cls):
        return cls.from_kwargs(
            session_id=None, session_status=None,
        )

    @classmethod
    def decision(cls, should_trace:bool, tracer:str | None):
        # tracer is None when every session tracer had no opinion
        return cls.from_kwargs(
            should_trace=should_trace, session_tracer=tracer,
        )

    @classmethod
    def new_id(cls, _id):
        return cls.from_kwargs(
            session_id=_id, session_status=SessionStatus.new_id
        )

    @classmethod
    def existing_id(cls, _id):
        return cls.from_kwargs(
            session_id=_id, session_status=SessionStatus.existing_id
        )

    @classmethod
    def no_existing_session(cls):
        return cls.from_kwargs(
            session_status=SessionStatus.no_existing_session
        )

    @classmethod
    def not_traced(cls):
        return cls.from_kwargs(
            session_status=SessionStatus.not_traced
        )

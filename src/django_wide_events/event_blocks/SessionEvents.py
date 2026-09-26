from .Base import EventBlock
from enum import Enum

class SessionStatus:

    unknown = "unknown"
    new_id = "new_session_id"
    no_existing_session = "no_existing_session"
    invalid_session = "invalid_session"
    no_trace_path = "no_trace_path"
    no_trace_view = "no_trace_view"
    no_response = "no_response"



class SessionIDAddEvent(EventBlock):

    namespace = "session"
    use_namespace_on_write = True
    drop_none = False

    # TODO: Init for Sessions and trace context vars

    @classmethod
    def init(cls):
        return cls.from_kwargs(
            session_id=None, session_status=SessionStatus.unknown,
        )

    @classmethod
    def no_session_status(cls, status:str):
        return cls.from_kwargs(
            session_status=status,
        )

    @classmethod
    def no_session_id(cls):
        return cls.from_kwargs(
            session_id=None
        )

    @classmethod
    def add_id(cls, _id):
        return cls.from_kwargs(
            session_id=_id, session_status=SessionStatus.new_id
        )

    @classmethod
    def no_existing_session(cls):
        return cls.from_kwargs(
            session_status=SessionStatus.no_existing_session
        )

    @classmethod
    def invalid_session(cls):
        return cls.from_kwargs(
            session_status=SessionStatus.invalid_session
        )

    @classmethod
    def unknow_session_status(cls):
        return cls.from_kwargs(
            session_status=SessionStatus.unknown,
        )

    @classmethod
    def debug_session_trace(cls, _id):
        return cls.from_kwargs(
            session_id_before_check=_id
        )

    @classmethod
    def no_trace_path(cls):
        return cls.from_kwargs(
            session_status=SessionStatus.no_trace_path,
        )

    @classmethod
    def no_trace_view(cls):
        return cls.from_kwargs(
            session_status=SessionStatus.no_trace_view,
        )

    @classmethod
    def no_response(cls):
        return cls.no_session_status(SessionStatus.no_response)

    @classmethod
    def trace_capture(cls, _if_trace):
        _kwargs = {"should_trace":_if_trace}
        if not _if_trace:
            _kwargs["session_status"] = SessionStatus.no_trace_view
        return cls.from_kwargs(
            **_kwargs
        )
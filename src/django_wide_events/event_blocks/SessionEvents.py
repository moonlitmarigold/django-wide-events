from .Base import EventBlock
from enum import Enum

class SessionStatus:

    unknown = "unknown"
    new_id = "new_session_id"
    no_existing_session = "no_existing_session"
    invalid_session = "invalid_session"



class SessionIDAddEvent(EventBlock):

    namespace = "session"
    use_namespace_on_write = True
    drop_none = False

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
            session_id=None, session_status=SessionStatus.no_existing_session
        )

    @classmethod
    def invalid_session(cls):
        return cls.from_kwargs(
            session_id=None, sesion_status=SessionStatus.invalid_session
        )

    @classmethod
    def unknow_session_status(cls):
        return cls.from_kwargs(
            session_id=None, sesion_status=SessionStatus.unknown,
        )

    @classmethod
    def debug_session_trace(cls, _id):
        return cls.from_kwargs(
            session_id_before_check=_id
        )
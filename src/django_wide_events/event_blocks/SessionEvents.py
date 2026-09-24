from .Base import EventBlock

class SessionIDAddEvent(EventBlock):

    namespace = "session"
    use_namespace_on_write = True

    @classmethod
    def no_session_id(cls):
        cls.from_kwargs(session_id=None)

    @classmethod
    def add_id(cls, _id):
        cls.from_kwargs(session_id=_id)
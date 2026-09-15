from .Base import EventBlock

class ExceptionEvent(EventBlock):

    namespace = "error"

    @classmethod
    def save_error(cls, _type, message, stack):
        return cls.from_kwargs(
            type=_type,
            message=message,
            stack=stack
        )

class HookErrorEvent(EventBlock):

    namespace = "hook_error"
    append_list = True

    @classmethod
    def save_hook_error(cls, label, stack):
        return cls.from_kwargs(
            hook_errors=[{
                "hook": label,
                "stack": stack
            }]
        )
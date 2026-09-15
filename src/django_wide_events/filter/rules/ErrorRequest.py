from .Base import BaseRule
from dataclasses import dataclass
import logging

@dataclass
class ErrorRequest(BaseRule):
    """Anything logged as an error, or with an exception recorded on the event
    by process_exception - the response may still have been a 2xx."""

    level:int = logging.ERROR
    error_key:str = "error"

    def keep(self, record, event) -> bool:
        if record is not None and record.levelno >= self.level:
            return True
        return self.lookup(event, self.error_key) is not None

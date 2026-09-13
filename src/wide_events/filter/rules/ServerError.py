from .Base import BaseRule
from dataclasses import dataclass

@dataclass
class ServerError(BaseRule):
    """Broke, or never produced a response at all."""

    min_status:int = 500
    status_key:str = "status_code"

    def keep(self, record, event) -> bool:
        status = self.lookup(event, self.status_key)
        if status is None:
            return True
        return int(status) >= self.min_status

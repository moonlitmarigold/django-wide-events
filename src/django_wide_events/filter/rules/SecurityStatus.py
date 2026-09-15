from .Base import BaseRule
from dataclasses import dataclass

@dataclass
class SecurityStatus(BaseRule):
    """Security-relevant statuses, kept in full so auth failures and rate
    limiting stay countable rather than being scaled by a sample rate."""

    statuses:tuple = (401, 403, 429)
    status_key:str = "status_code"

    def keep(self, record, event) -> bool:
        status = self.lookup(event, self.status_key)
        if status is None:
            return False
        return int(status) in self.statuses

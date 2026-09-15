from .Base import BaseRule
from dataclasses import dataclass

@dataclass
class SlowRequest(BaseRule):

    slow_ms:int = 1000
    duration_key:str = "duration_ms"

    def keep(self, record, event) -> bool:
        duration = self.lookup(event, self.duration_key)
        if duration is None:
            return False
        return float(duration) >= self.slow_ms

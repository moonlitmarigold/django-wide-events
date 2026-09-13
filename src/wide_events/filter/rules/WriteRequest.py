from .Base import BaseRule
from dataclasses import dataclass

@dataclass
class WriteRequest(BaseRule):
    """Every write. The method is nested under whichever collector supplied it,
    so the path is configurable and an absent method is not treated as a write."""

    read_methods:tuple = ("GET", "HEAD")
    method_key:str = "meta.method"

    def keep(self, record, event) -> bool:
        method = self.lookup(event, self.method_key)
        if method is None:
            return False
        return str(method).upper() not in self.read_methods

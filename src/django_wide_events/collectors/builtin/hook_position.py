import dataclasses
from typing import Callable

from ..Base import Collector

CollectorEntry = type[Collector] | Callable[[], Collector | type[Collector]]


@dataclasses.dataclass
class Change:
    phase: str
    target_index: int

    def absolute(self, length: int) -> int:
        return self.target_index % length


@dataclasses.dataclass
class ChangeHookPosition:

    cls: type[Collector]
    collectors: list[CollectorEntry]
    hooks: dict[str, list[int]]
    changes: list[Change]

    @staticmethod
    def get_index_class_in_collectors(_cls, collectors):
        for i, hook in enumerate(collectors):
            # entries are classes or factory instances; only classes can match
            if isinstance(hook, type) and issubclass(hook, _cls):
                return i
        return None

    def change_position_of_hook(self, _change: Change, collector_index) -> list[int]:
        hook_phase = self.hooks[_change.phase]
        if collector_index not in hook_phase:
            # the class doesn't implement this phase, so there is nothing to move
            return hook_phase

        # resolve against the phase length *before* removal: -1 then lands on
        # len(rest), which makes insert() an append
        target_index = _change.absolute(len(hook_phase))
        rest = [i for i in hook_phase if i != collector_index]
        rest.insert(target_index, collector_index)
        return rest

    def convert(self):
        index: int | None = self.get_index_class_in_collectors(
            self.cls, self.collectors
        )
        if index is None:
            return

        for change in self.changes:
            self.hooks[change.phase] = self.change_position_of_hook(
                change, index
            )
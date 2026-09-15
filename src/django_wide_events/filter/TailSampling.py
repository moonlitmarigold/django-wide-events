from .RandomSampling import RandomSampling
from .rules import DEFAULT_RULES
import traceback

class TailSampling(RandomSampling):

    def __init__(self, base_rate: int, keep_rules:list | None = None, keep_non_wide_events:bool=True):
        super().__init__(base_rate, keep_rules, keep_non_wide_events)

        if not self.rules:
            self.rules = DEFAULT_RULES

    def _filter(self, record, event):

        for rule in self.rules:
            try:
                res = rule.keep(record, event)
                if res is True:
                    return True
            except Exception as e:
                self._record_rule_failure(
                    repr(rule), event, e
                )
                return True
        return None

    @staticmethod
    def _record_rule_failure(label, event, exception):
        errors = event.setdefault('rule_errors', [])
        errors.append(
            {
                "rule" : label,
                "stack": "".join(traceback.format_exception(type(exception), exception,
                exception.__traceback__))
            }
        )
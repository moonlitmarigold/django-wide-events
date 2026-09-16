import logging
import hashlib

class RandomSampling(logging.Filter):

    def __init__(self, base_rate: int, keep_rules:list | None = None, keep_non_wide_events:bool=True):
        super().__init__()
        self.base_rate = base_rate
        if base_rate < 0:
            raise ValueError("sample_rate must be a positive integer or 0")

        self.rules = keep_rules if keep_rules else []
        self.keep_non_wide_events = keep_non_wide_events


    def filter(self, record):
        event = getattr(record, "event", None)
        if not event:
            if self.keep_non_wide_events:
                return True
            return False

        if_capture = getattr(record, "capture", None)
        if if_capture is not None:
            return if_capture

        res = self._filter(record, event)
        if not res: # if filter returns None, then normal sample, if not just return true
            return self.sample_on_base_rate(self.base_rate, event)
        return True

    def _filter(self, record, event):
        return None

    @staticmethod
    def sample_on_base_rate(sample_rate:int, event):
        if sample_rate == 0:
            return False
        request_id = event['request_id']
        h = hashlib.sha1(str(request_id).encode()).hexdigest()
        return int(h, 16) % sample_rate == 0


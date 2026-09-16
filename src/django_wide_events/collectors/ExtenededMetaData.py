from .Base import Collector
from datetime import datetime, timezone as _timezone
from django.utils import timezone

class MetaData(Collector):

    def on_create(self, request):

        meta = {
            "method": request.method,
            "timezone": timezone.get_current_timezone_name(),
            "timestamp" : datetime.now(_timezone.utc).isoformat(timespec='milliseconds'),
        }
        self.set(meta=meta)



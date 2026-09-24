from .Base import Collector
from django.utils import timezone

class MetaData(Collector):

    def on_create(self, request):

        meta = {
            "method": request.method,
            "timezone": timezone.get_current_timezone_name(),
        }
        self.set(meta=meta)



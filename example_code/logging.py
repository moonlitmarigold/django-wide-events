import json
import logging
from django.conf import settings
import time
import uuid
from django.utils import timezone
import traceback
import datetime
import re
import hashlib


logger = logging.getLogger("app.request")

class JSONFormatter(logging.Formatter):

    def format(self, record):
        event:dict = {
            "severity": record.levelname,
            "loglevel": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "created": datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc).isoformat(),
        }
        event.update(getattr(record, "event", {}))
        if record.exc_info:
            event["error"] = {
                        "type": record.exc_info[0].__name__,
                        "stack": self.formatException(record.exc_info),
                    }

        return self._dumps(event)

    @staticmethod
    def _dumps(event:dict):
        return json.dumps(event, default=str)

class IndentJSONFormatter(JSONFormatter):

    @staticmethod
    def _dumps(event:dict):
        return json.dumps(event, indent=4, default=str)

class LoggingMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if self.if_no_logging(request.path):
            return self.get_response(request)

        start = time.perf_counter()
        request_id = self._request_id(request)
        request.request_id = request_id
        request.event = {
            "request_id": request_id,
            "request_date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
            "timezone":timezone.get_current_timezone_name(),
            "method": request.method,
            "path": request.path,
            "env": settings.ENV_NAME,
            "commit": settings.GIT_COMMIT,
        }

        try:
            response = self.get_response(request)
            match = getattr(request, "resolver_match", None)
            if match:
                request.event["route"] = match.view_name
            request.event['status_code'] = int(getattr(response, 'status_code', 200))
            response.headers['X-Request-Id'] = request_id
            return response
        finally:
            request.event['duration_ms'] = round((time.perf_counter() - start) * 1000, 2)
            if hasattr(request, 'user') and request.user.is_authenticated:  # after AuthenticationMiddleware
                request.event["user_id"] = request.user.id

            if 'status_code' not in request.event.keys() or request.event['status_code'] >= 500:
                logger.error("request", extra={"event": request.event})
            else:
                logger.info("request", extra={"event": request.event})



    @staticmethod
    def _request_id(request):
        #_REQUEST_ID_RE = re.compile(r'^[A-Za-z0-9_.-]{1,64}$')
        #incoming = request.headers.get("X-Request-Id", "")
        #return incoming if _REQUEST_ID_RE.match(incoming) else str(uuid.uuid4())
        return str(uuid.uuid4())

    @staticmethod
    def process_exception(request, exception):
        request.event["error"] = {
            "type": type(exception).__name__,
            "message": str(exception),
            "stack":traceback.format_exc()
        }

        return None

    @staticmethod
    def if_no_logging(request_path:str):
        for path in settings.NO_LOGGING_PATHS:
            if request_path.startswith(path):
                return True
        return False

class TailSampling(logging.Filter):

    def __init__(self, slow_ms=1000, base_rate=100):
        super().__init__()
        self.slow_ms = slow_ms
        self.base_rate = base_rate


    def filter(self, record):
        event = getattr(record, "event", None)

        if event is None:
            return True

        event['sample_rate'] = self.base_rate
        rate = self._keep(event, record)
        if rate <= 1:
            return True

        return self.sample(event.get("request_id", ""), self.base_rate)


    def _keep(self, event, record):
        status = event.get("status_code")

        if record.levelno >= logging.ERROR:  # anything you log as an error
            return 1
        if status is None or status >= 500:  # broke, or never produced a response
            return 1
        if "error" in event:  # exception recorded, response downgraded
            return 1
        if event.get("duration_ms", 0) >= self.slow_ms:
            return 1
        if event.get("method") not in ("GET", "HEAD"):  # every write
            return 1
        if status in (401, 403, 429):  # security-relevant, keep all
            return 1
        return self.base_rate


    @staticmethod
    def sample(request_id, rate):
        digest = hashlib.sha1(request_id.encode()).digest()
        return int.from_bytes(digest[:4], "big") < (2 ** 32) // rate




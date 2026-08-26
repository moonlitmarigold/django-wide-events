from .base import *

# make logs easier to read on terminal
_logger = "mysite.logging.JSONFormatter" if not is_dev else "mysite.logging.IndentJSONFormatter"

LOGGING = {
      "version": 1,
      "disable_existing_loggers": False,
      "formatters": {
          "json": {"()": _logger},
      },
      "filters": {
        "tail_sampling": {
            "()": "mysite.logging.TailSampling",
            "slow_ms": 1000,
            "base_rate": 100,
        }
      },
      "handlers": {
          "stdout": {
              "class": "logging.StreamHandler",
              "stream": "ext://sys.stdout",
              "formatter": "json",
              "filters": ["tail_sampling"]
          },
      },
      "root": {"handlers": ["stdout"], "level": "INFO"},
      "loggers": {
          "django.request": {"handlers": ["stdout"], "level": "ERROR", "propagate": False},
          "app": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
      },
  }
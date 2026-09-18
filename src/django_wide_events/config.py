from django.conf import settings as django_settings
from django.utils.module_loading import import_string
from django.core.signals import setting_changed
from .collectors import DEFAULT_COLLECTORS

IMPORT_STRINGS = {"COLLECTORS", "ID_GENERATOR"}          # values are dotted paths -> import them
NESTED = {"SAMPLING", "STATIC_FIELDS", "REQUEST_ID"}   # merge one level deep instead of replacing

DEFAULTS = {
    "COLLECTORS": DEFAULT_COLLECTORS,
    "STATIC_FIELDS": {},
    "LOGGER_NAME": "wide_events.request",
    "NO_LOGGING_PATHS": [],
    "REQUEST_ID": {
        "TRUST_ID_HEADER": True, # TRUE: Always trust False: Never
        "RESPONSE_HEADER": "X-Request-Id",
        "ID_GENERATOR": "django_wide_events.ids.uuid4_hex",
    }
    # "SAMPLING": {"BASE_RATE": 1, "SLOW_MS": 1000, "KEEP_RULES": []}, Sampling on the filter
}

class WideEventSettings:

    def __init__(self):
        self._cache = {}

    def __getattr__(self, key):
        if key not in DEFAULTS:
            raise AttributeError(f"Invalid WIDE_EVENTS setting: {key!r}")
        if key in self._cache:
            return self._cache[key]

        user = getattr(django_settings, "WIDE_EVENTS", {})
        default = DEFAULTS[key]

        if key not in user:
            value = default
        elif key in NESTED:
            value = {**default, **user[key]}
        else:
            value = user[key]

        # import string if present
        value = self.import_string_key(key, value)

        self._cache[key] = value
        return value

    def reload(self, **kwargs):
        if kwargs.get("setting") == "WIDE_EVENTS":
            self._cache.clear()

    @staticmethod
    def import_string_key(key, value):
        if isinstance(value, dict):
            for _k, _v in value.items():
                value[_k] =  WideEventSettings.import_string_key(_k, _v)
            return value

        if key in IMPORT_STRINGS:
            return WideEventSettings._import(value)
        return value

    @staticmethod
    def _import(value):
        if isinstance(value, list):
            return [WideEventSettings._import(p) for p in value]
        if isinstance(value, str):
            return import_string(value)
        return value

wide_event_settings = WideEventSettings()
setting_changed.connect(wide_event_settings.reload)
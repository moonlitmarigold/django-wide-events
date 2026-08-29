import json
import logging


class JSONFORMATTER(logging.Formatter):

    def __init__(self, indent: bool = False):
        super().__init__()
        if indent:
            self._dump = self.indent_dump
        else:
            self._dump = self.normal_dump

    def format(self, record):

        event = self.return_event(record)

        event.update(getattr(record, 'event', {}))

        if record.exc_info:
            event['error'] = self.return_error(record)

        return self._dump(event)

    def return_event(self, record):
        return {
            "loglevel": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.return_timestamp(record)
        }

    def return_error(self, record):
        return {
            "type": record.exc_info[0].__name__,
            "stack": self.formatException(record.exc_info),
        }

    def return_timestamp(self, record):
        return record.created

    @staticmethod
    def normal_dump(data: dict):
        return json.dumps(data, default=str)

    @staticmethod
    def indent_dump(data: dict):
        return json.dumps(data, indent=4, default=str)

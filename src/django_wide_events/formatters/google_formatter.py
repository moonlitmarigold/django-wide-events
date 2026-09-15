from .json_formatter import JSONFORMATTER

class GoogleFormatter(JSONFORMATTER):

    def return_event(self, record):
        return {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": self.return_timestamp(record)
        }
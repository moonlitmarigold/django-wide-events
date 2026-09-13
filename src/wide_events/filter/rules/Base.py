

class BaseRule:

    def keep(self, record, event) -> bool:
        ...

    @staticmethod
    def lookup(event, path:str, default=None):
        """Read a dotted path out of the event, e.g. "meta.method".

        Collectors nest their fields, so a rule can't assume the value it wants
        sits at the top level - and a missing key has to read as absent rather
        than raise, since which collectors are installed is up to the host."""
        value = event
        for key in path.split("."):
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value

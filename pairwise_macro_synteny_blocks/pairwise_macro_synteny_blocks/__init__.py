def int_or_str(value):
    try:
        return int(value)
    except ValueError:
        return value


__version__ = "1.3.4"
VERSION = tuple(map(int_or_str, __version__.split(".")))

__schema_version__ = "1.1.0"
SCHEMA_VERSION = tuple(map(int_or_str, __schema_version__.split(".")))

def int_or_str(value):
    try:
        return int(value)
    except ValueError:
        return value


__version__ = "1.1.0"
VERSION = tuple(map(int_or_str, __version__.split(".")))

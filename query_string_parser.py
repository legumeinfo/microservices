from enum import Enum


# the different types that can be parsed
class Type(Enum):
  INT = 1
  WHOLE_NUMBER = 2
  NATURAL_NUMBER = 3
  NON_EMPTY_STRING = 4
  STRING_LIST = 5
  NON_EMPTY_STRING_LIST = 6


# a parser object used for parsing query parameter values
class Parser(object):

  def __init__(self, type, default=None, optional=False):
    if type not in Type:
      raise ValueError("Parser: 'type' must be one of %r." % Type)
    self.type = type
    self.default = default
    self.optional = (default is not None) or optional

  def validate(self, string):
    if string is None:
      if self.default is not None:
        string = self.default
      elif self.optional:
        return None
    if self.type == Type.INT or self.type == Type.NATURAL_NUMBER or self.type == Type.WHOLE_NUMBER:
      i = int(string)
      if self.type == Type.NATURAL_NUMBER and i <= 0:
        raise ValueError("invalid literal for natural int() with base 10: '%r'" % string)
      elif self.type == Type.WHOLE_NUMBER and i < 0:
        raise ValueError("invalid literal for whole int() with base 10: '%r'" % string)
      return i
    elif self.type == Type.NON_EMPTY_STRING:
      if string == '':
        raise ValueError("invalid literal for non-empty str(): '%r'" % string)
      return string
    elif self.type == Type.STRING_LIST or self.type == Type.NON_EMPTY_STRING_LIST:
      l = string if isinstance(string, list) else string.split(',')
      if self.type == Type.NON_EMPTY_STRING_LIST:
        l = list(filter(lambda s: s != '', l))
      if not l and self.default is None:
        raise ValueError("invalid literal for string list(): '%r'" % string)
      return l


# a function that that parses a dictionary according to the provided schema
# data - the data to be parsed
# schema - a dictionary that shares keys with that of data. The value is the
#   Parser instance to be used to parse the key's value in data
def validate(data, schema):
  params = {}
  for param, parser in schema.items():
    params[param] = parser.validate(data.get(param))
  return params

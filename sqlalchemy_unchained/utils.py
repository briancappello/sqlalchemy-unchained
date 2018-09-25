import re

_missing = type('_missing', (), {'__bool__': lambda self: False})()


def de_camel(s, separator="_", _lowercase=True):
    """ Returns the string with CamelCase converted to underscores, e.g.,
        de_camel("TomDeSmedt", "-") => "tom-de-smedt"
        de_camel("getHTTPResponse2) => "get_http_response2"
    """
    s = re.sub(r"([a-z0-9])([A-Z])", "\\1%s\\2" % separator, s)
    s = re.sub(r"([A-Z])([A-Z][a-z])", "\\1%s\\2" % separator, s)
    return s.lower() if _lowercase else s


def snake_case(string):
    """
    Converts a string to snake case. For example::

        snake_case('OneTwoThree') -> 'one_two_three'
    """
    if not string:
        return string
    string = string.replace('-', '_').replace(' ', '_')
    return de_camel(string)

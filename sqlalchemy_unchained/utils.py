import re
import sqlalchemy as sa

from functools import reduce
from py_meta_utils import McsArgs
from typing import *


_missing = type('_missing', (), {'__bool__': lambda self: False})()


def de_camel(s: str, separator: str = "_", _lowercase: bool = True) -> str:
    """ Returns the string with CamelCase converted to underscores, e.g.,
        de_camel("TomDeSmedt", "-") => "tom-de-smedt"
        de_camel("getHTTPResponse2) => "get_http_response2"
    """
    s = re.sub(r"([a-z0-9])([A-Z])", "\\1%s\\2" % separator, s)
    s = re.sub(r"([A-Z])([A-Z][a-z])", "\\1%s\\2" % separator, s)
    return s.lower() if _lowercase else s


def snake_case(string: str) -> str:
    """
    Converts a string to snake case. For example::

        snake_case('OneTwoThree') -> 'one_two_three'
    """
    if not string:
        return string
    string = string.replace('-', '_').replace(' ', '_')
    return de_camel(string)


def title_case(string: str) -> str:
    """
    Converts a string to title case. For example::

        title_case('one_two_three') -> 'One Two Three'
    """
    if not string:
        return string
    string = string.replace('_', ' ').replace('-', ' ')
    parts = de_camel(string, ' ', _lowercase=False).strip().split(' ')
    return ' '.join([part if part.isupper() else part.title()
                     for part in parts])


def rec_getattr(obj, attr, default=None):
    """
        Recursive getattr.

        :param obj:
            The top-level object to get attributes off of
        :param attr:
            Dot delimited attribute name
        :param default:
            Default value

        Example::

            rec_getattr(obj, 'a.b.c')
    """
    try:
        return reduce(getattr, attr.split('.'), obj)
    except AttributeError:
        return default


def rec_hasattr(obj, attr):
    """
        Recursive hasattr.

        :param obj:
            The top-level object to check for attributes on
        :param attr:
            Dot delimited attribute name

        Example::

            rec_hasattr(obj, 'a.b.c')
    """
    try:
        reduce(getattr, attr.split('.'), obj)
    except AttributeError:
        return False
    else:
        return True


def _add_arg_to_table_args(mcs_args: McsArgs, new_arg: Any) -> Tuple:
    table_args = mcs_args.clsdict.get('__table_args__', ())
    if isinstance(table_args, dict):
        table_args = (table_args,)

    if table_args and isinstance(table_args[-1], dict):
        new_table_args = *table_args[:-1], new_arg, table_args[-1]
    else:
        new_table_args = *table_args, new_arg
    mcs_args.clsdict['__table_args__'] = new_table_args

    return new_table_args


def _get_column_names(mcs_args: McsArgs) -> Set[str]:
    return {col.name or attr_name
            for attr_name, col in mcs_args.clsdict.items()
            if isinstance(col, sa.Column)}


__all__ = [
    'de_camel',
    'rec_getattr',
    'rec_hasattr',
    'snake_case',
    'title_case',
]

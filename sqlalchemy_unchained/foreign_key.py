import inspect
import sqlalchemy as sa

from sqlalchemy.sql.type_api import TypeEngine as SQLAType
from typing import *

from .base_model import BaseModel as Model
from .model_registry import _ModelRegistry
from .utils import snake_case


def foreign_key(*args,
                fk_col: Optional[str] = None,
                primary_key: bool = False,
                nullable: bool = False,
                **kwargs) -> sa.Column:
    """
    Helper method to add a foreign key column to a model.

    For example::

        class Post(db.Model):
            category_id = db.foreign_key('Category')
            category = db.relationship('Category', back_populates='posts')

    Is equivalent to::

        class Post(db.Model):
            category_id = db.Column(db.Integer, db.ForeignKey('category.id'),
                                    nullable=False)
            category = db.relationship('Category', back_populates='posts')

    Customizing all the things::

        class Post(db.Model):
            _category_id = db.foreign_key('category_id',  # db column name
                                          db.String,      # db column type
                                          'categories',   # foreign table name
                                          fk_col='pk')    # foreign key col name

    Would be equivalent to::

        class Post(db.Model):
            _category_id = db.Column('category_id', db.String,
                                     db.ForeignKey('categories.pk'))

    :param args: :func:`foreign_key` takes up to three positional arguments.
    Most commonly, you will only pass one argument, which should be the table
    name you're linking to (or indirectly, the model class/name works too).
    If you want to customize the column name the foreign key gets stored in
    the database under, then it must be the first string argument, and you must
    *also* supply the table name. You can customize the column type that gets
    used by passing it too, eg ``sa.Integer`` or ``sa.String(36)``.

    :param str fk_col: The column name of the primary key on the *opposite* side
      of the relationship (defaults to
      :attr:`sqlalchemy_unchained._ModelRegistry.default_primary_key_column`).
    :param bool primary_key: Whether or not this :class:`~sqlalchemy.Column` is
                             a primary key.
    :param bool nullable: Whether or not this :class:`~sqlalchemy.Column` should
                          be nullable.
    :param kwargs: Any other kwargs to pass the :class:`~sqlalchemy.Column`
                   constructor.
    """
    return sa.Column(*_get_fk_col_args(args, fk_col),
                     primary_key=primary_key, nullable=nullable, **kwargs)


def _get_fk_col_args(args, fk_col=None, _default_col_type=sa.Integer):
    fk_col = fk_col or _ModelRegistry().default_primary_key_column

    try:
        model_class = [x for x in args
                       if inspect.isclass(x) and issubclass(x, Model)][0]
    except IndexError:
        model_class = None

    try:
        col_type = [x for x in args
                    if isinstance(x, SQLAType)
                    or (inspect.isclass(x) and issubclass(x, SQLAType))][0]
    except IndexError:
        col_type = _default_col_type

    str_args = [x for x in args if isinstance(x, str)]
    col_name = (str_args[0] if str_args and (len(str_args) == 2 or model_class)
                else None)
    table_name = str_args[0] if str_args else None
    if model_class:
        table_name = model_class.__tablename__
    elif col_name:
        table_name = str_args[1]

    if not table_name:
        raise TypeError('Could not determine the table name to use. Please provide '
                        'one as a positional argument.')

    if table_name != table_name.lower():
        table_name = snake_case(table_name)

    args = [col_name] if col_name else []
    args += [col_type, sa.ForeignKey(table_name + '.' + fk_col)]

    return args

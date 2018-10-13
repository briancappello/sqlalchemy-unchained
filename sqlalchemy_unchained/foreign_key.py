import inspect
import sqlalchemy as sa

from typing import *

from .base_model import BaseModel as Model
from .model_registry import _ModelRegistry
from .utils import snake_case


def foreign_key(model_or_table_name_or_column_name: Union[str, Type[Model]],
                model_or_table_name: Optional[Union[str, Type[Model]]] = None,
                *,
                fk_col: Optional[str] = None,
                primary_key: bool = False,
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

    :param model_or_table_name_or_column_name: If two arguments are given, then
        this is treated as the column name. Otherwise, it's treated as the table
        name (see docs for model_or_table_name)

    :param model_or_table_name: the model or table name to link to

        If given a lowercase string, it's treated as an explicit table name.

        If there are any uppercase characters, it's assumed to be a model name,
        and will be converted to snake case using the same automatic conversion
        as Flask-SQLAlchemy does itself.

        If given a subclass of :class:`flask_sqlalchemy.Model`, use its
        :attr:`__tablename__` attribute.

    :param str fk_col: column name of the primary key (defaults to "id")
    :param bool primary_key: Whether or not this Column is a primary key
    :param kwargs: any other kwargs to pass the Column constructor
    """
    fk_col = fk_col or _ModelRegistry().default_primary_key_column
    column_name = model_or_table_name_or_column_name
    if model_or_table_name is None:
        column_name = None
        model_or_table_name = model_or_table_name_or_column_name

    table_name = model_or_table_name
    if inspect.isclass(model_or_table_name):
        table_name = model_or_table_name.__tablename__
    elif table_name != table_name.lower():
        table_name = snake_case(model_or_table_name)

    args = [column_name] if column_name else []
    args += [sa.Integer, sa.ForeignKey(table_name + '.' + fk_col)]

    return sa.Column(*args, primary_key=primary_key, **kwargs)

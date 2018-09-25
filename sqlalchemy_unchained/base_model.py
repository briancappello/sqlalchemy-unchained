from sqlalchemy import orm
from sqlalchemy.orm.exc import UnmappedClassError

from .meta import ModelMetaOptionsFactory


class _QueryProperty(object):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __get__(self, obj, type):
        try:
            mapper = orm.class_mapper(type)
            if mapper:
                return type.query_class(mapper, session=self.session_factory())
        except UnmappedClassError:
            return None


class BaseModel(object):
    """
    Base model class for SQLAlchemy declarative base model.
    """
    class Meta:
        abstract = True
        pk = 'id'
        created_at = 'created_at'
        updated_at = 'updated_at'
        repr = ('id', 'created_at', 'updated_at')

        # FIXME would be nice not to need to have this here...
        # this is strictly for testing meta class stuffs
        _testing_ = 'this setting is only available when ' \
                    'os.getenv("SQLA_TESTING") == "True"'

    _meta_options_factory_class = ModelMetaOptionsFactory

    #: Query class used by :attr:`query`. Defaults to
    # :class:`SQLAlchemy.Query`, which defaults to :class:`BaseQuery`.
    query_class = None

    #: Convenience property to query the database for instances of this model
    # using the current session. Equivalent to ``db.session.query(Model)``
    # unless :attr:`query_class` has been changed.
    query = None

    def update(self, **kwargs):
        """
        Update fields on the model.

        :param kwargs: The model attribute values to update the instance with.
        """
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return self

    def __repr__(self):
        props = getattr(getattr(self, '_meta', object), 'repr', ())
        properties = [f'{prop}={getattr(self, prop)!r}'
                      for prop in props if hasattr(self, prop)]
        return f"{self.__class__.__name__}({', '.join(properties)})"

    def __eq__(self, other):
        """
        Checks the equality of two :class:`BaseModel` objects.
        """
        if not issubclass(getattr(other, '__class__', object), self.__class__):
            return False

        if not (self.Meta.pk and other.Meta.pk):
            return super().__eq__(other)

        return getattr(self, self.Meta.pk) == getattr(other, other.Meta.pk)

    def __ne__(self, other):
        """
        Checks the inequality of two :class`BaseModel` objects.
        """
        return not self.__eq__(other)

    # Python 3 implicitly sets __hash__ to None if we override __eq__
    # Therefore, we set it back to its default implementation
    __hash__ = object.__hash__

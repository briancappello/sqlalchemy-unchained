import inspect

from collections import defaultdict
from sqlalchemy.ext.associationproxy import _AssociationList

from .model_meta_options import ModelMetaOptionsFactory
from .utils import rec_getattr, rec_hasattr
from .validation import Required, ValidationError, ValidationErrors


class GettextDescriptor:
    def __get__(self, instance, cls):
        return getattr(instance, '_gettext_fn', lambda x: x)

    def __set__(self, instance, value):
        instance._gettext_fn = value


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
        str = None

        # FIXME would be nice not to need to have this here...
        # this is strictly for testing meta class stuffs
        _testing_ = 'this setting is only available when ' \
                    'os.getenv("SQLA_TESTING") == "True"'

    _meta_options_factory_class = ModelMetaOptionsFactory

    gettext_fn = GettextDescriptor()

    def __init__(self, **kwargs):
        super().__init__()
        self.update(partial_validation=True, **kwargs)

    def update(self, partial_validation=True, **kwargs):
        """
        Update fields on the model.
        """
        if self.Meta.validation:
            self.validate(partial=partial_validation, **kwargs)
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return self

    def validate(self, partial=False, **kwargs):
        """
        Validate kwargs before setting attributes on the model
        """
        data = kwargs
        if not partial:
            data = dict(**kwargs, **{col.name: getattr(self, col.name, None)
                                     for col in self.__class__.__table__.c.values()
                                     if col.name not in kwargs})
        self.validate_values(**data)

    @classmethod
    def validate_values(cls, **kwargs):
        errors = defaultdict(list)
        for name, value in kwargs.items():
            for validator in cls._get_validators(name):
                try:
                    validator(value)
                except ValidationError as e:
                    e.model = cls
                    e.column = name
                    errors[name].append(str(e))

        if errors:
            raise ValidationErrors(errors)

    @classmethod
    def _get_validators(cls, column_name):
        rv = []
        validators = cls.__validators__.get(column_name, [])
        for validator in validators:
            if isinstance(validator, str) and hasattr(cls, validator):
                rv.append(getattr(cls, validator))
            else:
                if inspect.isclass(validator):
                    validator = validator()
                rv.append(validator)

        col = cls.__table__.c.get(column_name)
        if col is None:
            # this happens for relationship attrs (and probably association proxies too)
            return rv

        required_msg = hasattr(col, 'info') and col.info.get('required', None)
        if (required_msg
                and not any(isinstance(x, Required) for x in validators)
                and col.default is None):
            if isinstance(required_msg, bool):
                required_msg = None
            elif isinstance(required_msg, str):
                required_msg = cls.gettext_fn(required_msg)
            rv.append(Required(required_msg or None))
        return rv

    def __setattr__(self, key, value):
        col = self.__mapper__.columns.get(key)
        if (self.Meta.validation
                and col is not None
                and ((col.name is None and hasattr(self, key)) or key == col.name)):
            for validator in self._get_validators(key):
                try:
                    validator(value)
                except ValidationError as e:
                    e.model = self.__class__
                    e.column = key
                    raise e
        super().__setattr__(key, value)

    def __repr__(self):
        def format_value(v):
            if isinstance(v, (list, _AssociationList)):
                return f'[{", ".join(repr(str(el)) for el in v)}]'
            return repr(v)

        pairs = [f'{attr}={format_value(rec_getattr(self, attr))}'
                 for attr in self.Meta.repr if rec_hasattr(self, attr)]
        return f'{self.__class__.__name__}({", ".join(pairs)})'

    def __str__(self):
        if not self.Meta.str:
            return repr(self)
        return str(getattr(self, self.Meta.str))

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


__all__ = [
    'BaseModel',
]

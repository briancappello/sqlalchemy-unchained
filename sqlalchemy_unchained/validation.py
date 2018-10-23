try:
    from speaklater import _LazyString
except ImportError:
    _LazyString = object

from typing import *

from .utils import title_case


class BaseValidationError(Exception):
    pass


class ValidationError(BaseValidationError):
    """
    Holds a validation error for a single column of a model.
    """
    def __init__(self, msg: str = None, model=None, column=None, validator=None):
        super().__init__(msg)
        self.msg = msg
        self.model = model
        self.column = column
        self.validator = validator

    def __str__(self):
        if self.validator and hasattr(self.validator, 'get_message'):
            return self.validator.get_message(self)
        return super().__str__()


class ValidationErrors(BaseValidationError):
    """
    Holds validation errors for an entire model.
    """
    def __init__(self, errors: Dict[str, List[str]]):
        super().__init__()
        self.errors = errors

    def __str__(self):
        return '\n'.join([k + ': ' + str(e) for k, e in self.errors.items()])


class BaseValidator:
    """
    Base class for column validators in SQLAlchemy Unchained.

    You should supply the error message to the constructor, and implement your
    validation logic in :meth:`~sqlalchemy_unchained.BaseValidator.__call__`::

        from sqlalchemy_unchained import BaseValidator, ValidationError

        class NameRequired(BaseValidator):
            def __init__():
                super().__init__(msg='Name is required.')

            def __call__(self, value):
                super().__call__(value)
                if not value:
                    raise ValidationError(validator=self)
                return True


        class YourModel(db.Model):
            name = db.Column(db.String, nullable=False, info=dict(
                validators=[NameRequired()]))
    """
    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg
        self.value = None

    def __call__(self, value):
        """
        Implement validation logic here. Return ``True`` if validation passes,
        otherwise raise :class:`~sqlalchemy_unchained.ValidationError`.
        """
        self.value = value
        return True

    def get_message(self, e: ValidationError):
        """
        Returns the message for this validation error. By default we just return
        ``self.msg``, but you can override this method if you need to customize
        the message.
        """
        return self.msg


class Required(BaseValidator):
    """
    A validator to require data (automatically applied to non-nullable
    scalar-value columns).
    """
    def __call__(self, value):
        super().__call__(value)
        if value is None or isinstance(value, str) and not value:
            raise ValidationError(validator=self)
        return True

    def get_message(self, e: ValidationError):
        if self.msg:
            if isinstance(self.msg, str):
                return self.msg
            elif isinstance(self.msg, _LazyString):
                return str(self.msg)
        return title_case(e.column) + ' is required.'

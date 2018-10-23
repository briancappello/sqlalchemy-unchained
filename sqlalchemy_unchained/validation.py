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
        """
        The constructor for validation errors.

        :param msg: The error message. If ``validator`` is provided and it implements
                    ``get_message``, that will take precedence over this parameter.
        :param model: The model this validation error is for.
        :param column: The :class:`~sqlalchemy.Column` this validation error is for.
        :param validator: The validator instance that raised this validation error.
        """
        super().__init__(msg)

        self.msg = msg
        """
        The error message. If ``validator`` is provided and it implements
        ``get_message``, that will take precedence over this value.
        """

        self.model = model
        """
        The model this validation error is for.
        """

        self.column = column
        """
        The :class:`~sqlalchemy.Column` this validation error is for.
        """

        self.validator = validator
        """
        The validator instance that raised this validation error.
        """

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
        """
        A dictionary of errors, where the keys are column names, and the values are
        lists of error messages for each column.
        """

    def __str__(self):
        return '\n'.join([k + ': ' + str(e) for k, e in self.errors.items()])


class BaseValidator:
    """
    Base class for column validators in SQLAlchemy Unchained.

    You should supply the error message to the constructor, and implement your
    validation logic in :meth:`~sqlalchemy_unchained.BaseValidator.__call__`::

        from sqlalchemy_unchained import BaseValidator, ValidationError


        class NameRequired(BaseValidator):
            def __init__(msg='Name is required.'):
                super().__init__(msg=msg)

            def __call__(self, value):
                super().__call__(value)
                if not value:
                    raise ValidationError(validator=self)


        class YourModel(db.Model):
            name = db.Column(db.String, nullable=False, info=dict(
                validators=[NameRequired]))
    """
    def __init__(self, msg=None):
        super().__init__()
        self.msg = msg
        """
        The message for this validator.
        """

        self.value = None

    def __call__(self, value):
        """
        Implement validation logic here. Raise
        :class:`~sqlalchemy_unchained.ValidationError` if validation does not pass.
        """
        self.value = value

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

    def get_message(self, e: ValidationError):
        if self.msg:
            if isinstance(self.msg, str):
                return self.msg
            elif isinstance(self.msg, _LazyString):
                return str(self.msg)
        return title_case(e.column) + ' is required.'

import inspect

from py_meta_utils import (AbstractMetaOption, McsArgs, MetaOption, MetaOptionsFactory,
                           process_factory_meta_options)
from sqlalchemy.exc import StatementError as SQLAlchemyStatementError
from typing import *

from .base_model import BaseModel
from .base_query import BaseQuery
from .session_manager import SessionManager, SessionManagerMetaclass


class ModelMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name='model', default=None, inherit=True)

    def check_value(self, value: Any, mcs_args: McsArgs):
        if mcs_args.is_abstract:
            return

        if not inspect.isclass(value) or not issubclass(value, BaseModel):
            raise Exception(
                'The class Meta model attribute must be a subclass of BaseModel')


class ModelManagerMetaOptionsFactory(MetaOptionsFactory):
    _options = [AbstractMetaOption, ModelMetaOption]


class ModelManagerMetaclass(SessionManagerMetaclass):
    def __new__(mcs, name, bases, clsdict):
        mcs_args = McsArgs(mcs, name, bases, clsdict)
        process_factory_meta_options(
            mcs_args, default_factory_class=ModelManagerMetaOptionsFactory)
        return super().__new__(*mcs_args)


class _QueryDescriptor:
    def __get__(self, instance, cls):
        return cls.session.query(cls.Meta.model)


class ModelManager(SessionManager, metaclass=ModelManagerMetaclass):
    """
    Base class for model managers. This is the **strongly** preferred pattern for
    managing all interactions with the database for models when using an ORM that
    implements the Data Mapper pattern (which SQLAlchemy does). You should create a
    subclass of ``ModelManager`` for every model in your app, customizing the
    :meth:`~sqlalchemy_unchained.ModelManager.create` method, and add any custom
    query methods you may need *here*, instead of on the model class as popularized
    by the Active Record pattern (which SQLAlchemy is *not*).

    For example::

        from your_package import db


        class Foobar(db.Model):
            name = db.Column(db.String, nullable=False)
            optional = db.Column(db.String, nullable=True)


        class FoobarManager(db.ModelManager):
            class Meta:
                model = Foobar

            def create(self, name, optional=None, commit=False):
                return super().create(name=name, optional=optional, commit=commit)

            def find_by_name(self, name):
                return self.get_by(name=name)

    Subclasses of :class:`~sqlalchemy_unchained.ModelManager` are singletons, and as
    such, anytime you call ``YourModelManager()``, you will get the same instance
    back.

    .. list-table:: Available :class:`~sqlalchemy_unchained.ModelManager` Meta options
       :header-rows: 1

       * - Meta option name
         - type
         - Description
       * - abstract
         - ``bool``
         - Whether or not this class should be considered abstract.
       * - model
         - Type[db.Model]
         - The model class this manager is for. Required, unless the class is marked abstract.
    """

    class Meta:
        abstract = True
        model = None

    query: BaseQuery = _QueryDescriptor()
    """
    The :class:`~sqlalchemy_unchained.BaseQuery` for this manager's model.
    """

    q: BaseQuery = _QueryDescriptor()
    """
    An alias for :attr:`query`.
    """

    def create(self, commit: bool = False, **kwargs) -> BaseModel:
        """
        Creates an instance of ``self.Meta.model``, optionally committing the
        current session transaction.

        :param bool commit: Whether or not to commit the current session transaction.
        :param kwargs: The data to initialize the model with.
        :return: The created model instance.
        """
        instance = self.Meta.model(**kwargs)
        self.save(instance, commit=commit)
        return instance

    def _maybe_get_by(self, **kwargs) -> Union[BaseModel, None]:
        with self.no_autoflush:
            try:
                return self.get_by(**kwargs)
            except SQLAlchemyStatementError as e:
                if 'no value has been set for this column' not in str(e):
                    raise e

    def get_or_create(self,
                      defaults: dict = None,
                      commit: bool = False,
                      **kwargs,
                      ) -> Tuple[BaseModel, bool]:
        """
        Get or create an instance of ``self.Meta.model`` by ``kwargs`` and
        ``defaults``, optionally committing te current session transaction.

        :param dict defaults: Extra values to create the model with, if not found
        :param bool commit: Whether or not to commit the current session transaction.
        :param kwargs: The values to filter by and create the model with
        :return: Tuple[the_model_instance, did_create_bool]
        """
        instance = self._maybe_get_by(**kwargs)
        if not instance:
            defaults = defaults or {}
            return self.create(**defaults, **kwargs, commit=commit), True

        return instance, False

    def update(self,
               instance: BaseModel,
               commit: bool = False,
               **kwargs,
               ) -> BaseModel:
        """
        Update ``kwargs`` on an instance, optionally committing the current session
        transaction.

        :param instance: The model instance to update.
        :param bool commit: Whether or not to commit the current session transaction.
        :param kwargs: The data to update on the model.
        :return: The updated model instance.
        """
        instance.update(**kwargs)
        self.save(instance, commit=commit)
        return instance

    def update_or_create(self,
                         defaults: dict = None,
                         commit: bool = False,
                         **kwargs,
                         ) -> Tuple[BaseModel, bool]:
        """
        Update or create an instance of ``self.Meta.model`` by ``kwargs`` and
        ``defaults``, optionally committing te current session transaction.

        :param dict defaults: Extra values to update on the model
        :param bool commit: Whether or not to commit the current session transaction.
        :param kwargs: The values to filter by and update on the model
        :return: Tuple[the_model_instance, did_create_bool]
        """
        instance = self._maybe_get_by(**kwargs)
        if not instance:
            defaults = defaults or {}
            return self.create(**defaults, **kwargs, commit=commit), True

        instance.update(**defaults)
        return instance, False

    def all(self) -> List[BaseModel]:
        """
        Query the database for all records of ``self.Meta.model``.

        :return: A list of all model instances (may be empty).
        """
        return self.q.all()

    def get(self,
            id: Union[int, str, Tuple[int, ...], Tuple[str, ...]],
            ) -> Union[BaseModel, None]:
        """
        Return an instance based on the given primary key identifier,
        or ``None`` if not found.

        E.g.::

            my_user = UserManager().get(5)

            some_object = SomeObjectManager().get((5, 10))

        :meth:`~.Query.get` is special in that it provides direct
        access to the identity map of the owning :class:`.Session`.
        If the given primary key identifier is present
        in the local identity map, the object is returned
        directly from this collection and no SQL is emitted,
        unless the object has been marked fully expired.
        If not present,
        a SELECT is performed in order to locate the object.

        :meth:`~.Query.get` also will perform a check if
        the object is present in the identity map and
        marked as expired - a SELECT
        is emitted to refresh the object as well as to
        ensure that the row is still present.
        If not, :class:`~sqlalchemy.orm.exc.ObjectDeletedError` is raised.

        :meth:`~.Query.get` is only used to return a single
        mapped instance, not multiple instances or
        individual column constructs, and strictly
        on a single primary key value.  The originating
        :class:`.Query` must be constructed in this way,
        i.e. against a single mapped entity,
        with no additional filtering criterion.  Loading
        options via :meth:`~.Query.options` may be applied
        however, and will be used if the object is not
        yet locally present.

        A lazy-loading, many-to-one attribute configured
        by :func:`.relationship`, using a simple
        foreign-key-to-primary-key criterion, will also use an
        operation equivalent to :meth:`~.Query.get` in order to retrieve
        the target value from the local identity map
        before querying the database.

        :param id: A scalar or tuple value representing
         the primary key.   For a composite primary key,
         the order of identifiers corresponds in most cases
         to that of the mapped :class:`.Table` object's
         primary key columns.  For a :func:`.mapper` that
         was given the ``primary key`` argument during
         construction, the order of identifiers corresponds
         to the elements present in this collection.

        :return: The object instance, or ``None``.

        """
        return self.q.get(id)

    def get_by(self, **kwargs) -> Union[BaseModel, None]:
        """
        Get one or none of ``self.Meta.model`` by ``kwargs``.

        :param kwargs: The data to filter by.
        :return: The model instance, or ``None``.
        """
        return self.q.filter_by(**kwargs).one_or_none()

    def filter(self, *criterion) -> BaseQuery:
        """
        Get all instances of ``self.Meta.model`` matching ``criterion``.

        :param criterion: The criterion to filter by.
        :return: A list of model instances (may be empty).
        """
        return self.q.filter(*criterion)

    def filter_by(self, **kwargs) -> BaseQuery:
        """
        Get all instances of ``self.Meta.model`` matching ``kwargs``.

        :param kwargs: The data to filter by.
        :return: A list of model instances (may be empty).
        """
        return self.q.filter_by(**kwargs)


__all__ = [
    'ModelManager',
    'ModelManagerMetaclass',
    'ModelManagerMetaOptionsFactory',
]

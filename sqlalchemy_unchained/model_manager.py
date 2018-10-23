import inspect

from py_meta_utils import (AbstractMetaOption, McsArgs, MetaOption, MetaOptionsFactory,
                           process_factory_meta_options)
from typing import *

from .base_model import BaseModel
from .base_query import BaseQuery
from .session_manager import SessionManager, _SessionMetaclass


class _ModelMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name='model', default=None, inherit=True)

    def check_value(self, value: Any, mcs_args: McsArgs):
        if mcs_args.is_abstract:
            return

        if not inspect.isclass(value) or not issubclass(value, BaseModel):
            raise Exception(
                'The class Meta model attribute must be a subclass of BaseModel')


class _ModelManagerMetaOptionsFactory(MetaOptionsFactory):
    _options = [AbstractMetaOption, _ModelMetaOption]


class _ModelManagerMetaclass(_SessionMetaclass):
    def __new__(mcs, name, bases, clsdict):
        mcs_args = McsArgs(mcs, name, bases, clsdict)
        process_factory_meta_options(
            mcs_args, default_factory_class=_ModelManagerMetaOptionsFactory)
        return super().__new__(*mcs_args)


class _QueryDescriptor:
    def __get__(self, instance, cls):
        return cls.session.query(cls.Meta.model)


class ModelManager(SessionManager, metaclass=_ModelManagerMetaclass):
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
        abstract: bool = True
        model: Type[BaseModel] = None

    query: BaseQuery = _QueryDescriptor()
    """
    The :class:`~sqlalchemy_unchained.BaseQuery` for this manager's model.
    """

    q: BaseQuery = _QueryDescriptor()
    """
    An alias for :attr:`query`.
    """

    def create(self, commit: bool = False, **kwargs):
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

    def get_or_create(self, commit: bool = False, **kwargs):
        """
        Get or create an instance of ``self.Meta.model`` by ``kwargs``, optionally
        committing te current session transaction.

        :param bool commit: Whether or not to commit the current session transaction.
        :param kwargs: The data to filter by, or to initialize the model with.
        :return: Tuple[the_model_instance, did_create_bool]
        """
        instance = self.get_by(**kwargs)
        if not instance:
            return self.create(**kwargs, commit=commit), True
        return instance, False

    def update(self, instance, commit=False, **kwargs):
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

    def all(self):
        """
        Query the database for all records of ``self.Meta.model``.

        :return: A list of all model instances (may be empty).
        """
        return self.q.all()

    def get_by(self, **kwargs):
        """
        Get one or none of ``self.Meta.model`` by ``kwargs``.

        :param kwargs: The data to filter by.
        :return: The model instance, or ``None``.
        """
        return self.q.filter_by(**kwargs).one_or_none()

    def filter(self, *criterion):
        """
        Get all instances of ``self.Meta.model`` matching ``criterion``.

        :param criterion: The criterion to filter by.
        :return: A list of model instances (may be empty).
        """
        return self.q.filter(*criterion).all()

    def filter_by(self, **kwargs):
        """
        Get all instances of ``self.Meta.model`` matching ``kwargs``.

        :param kwargs: The data to filter by.
        :return: A list of model instances (may be empty).
        """
        return self.q.filter_by(**kwargs).all()
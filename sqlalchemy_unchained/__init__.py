import functools

from py_meta_utils import META_OPTIONS_FACTORY_CLASS_ATTR_NAME
from sqlalchemy import *
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative import declarative_base as _declarative_base
from sqlalchemy.ext.declarative.base import _declarative_constructor
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import *
from sqlalchemy.orm import relationship as _relationship
from sqlalchemy.sql.schema import (
    DEFAULT_NAMING_CONVENTION as _SQLA_DEFAULT_NAMING_CONVENTION)

from .base_model import BaseModel
from .base_model_metaclass import DeclarativeMeta
from .base_query import BaseQuery, QueryMixin
from .foreign_key import foreign_key
from .model_manager import ModelManager
from .model_meta_options import ColumnMetaOption, ModelMetaOptionsFactory
from .model_registry import _ModelRegistry
from .session_manager import SessionManager
from .validation import BaseValidator, Required, ValidationError, ValidationErrors


METADATA_NAMING_CONVENTION = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_to_%(column_0_name)s_on_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}


# copied from flask-sqlalchemy (BSD license)
def _set_default_query_class(d, query_cls):
    if 'query_class' not in d:
        d['query_class'] = query_cls


# copied from flask-sqlalchemy (BSD license)
def _wrap_with_default_query_class(fn, query_cls):
    @functools.wraps(fn)
    def newfn(*args, **kwargs):
        _set_default_query_class(kwargs, query_cls)
        if "backref" in kwargs:
            backref = kwargs['backref']
            if isinstance(backref, str):
                backref = (backref, {})
            _set_default_query_class(backref[1], query_cls)
        return fn(*args, **kwargs)
    return newfn


def declarative_base(model=BaseModel, name='Model', bind=None, metadata=None,
                     mapper=None, class_registry=None, metaclass=DeclarativeMeta):
    """
    Construct a base class for declarative class definitions.

    The new base class will be given a metaclass that produces
    appropriate :class:`~sqlalchemy.schema.Table` objects and makes
    the appropriate :func:`~sqlalchemy.orm.mapper` calls based on the
    information provided declaratively in the class and any subclasses
    of the class.

    :param bind:
      An optional :class:`~sqlalchemy.engine.Connectable`, will be assigned
      the ``bind`` attribute on the :class:`~sqlalchemy.schema.MetaData`
      instance.

    :param metadata:
      An optional :class:`~sqlalchemy.schema.MetaData` instance.  All
      :class:`~sqlalchemy.schema.Table` objects implicitly declared by
      subclasses of the base will share this MetaData.  A MetaData instance
      will be created if none is provided.  The
      :class:`~sqlalchemy.schema.MetaData` instance will be available via the
      `metadata` attribute of the generated declarative base class.

    :param mapper:
      An optional callable, defaults to :func:`~sqlalchemy.orm.mapper`. Will
      be used to map subclasses to their Tables.

    :param model:
      Defaults to :class:`~sqlalchemy_unchained.BaseModel`. A type to use as
      the base for the generated declarative base class. May be a class or a
      tuple of classes.

    :param name:
      Defaults to ``Model``.  The display name for the generated class.
      Customizing this is not required, but can improve clarity in
      tracebacks and debugging.

    :param class_registry:
      An optional dictionary that will serve as the registry of
      class names-> mapped classes when string names are used to identify
      classes inside of :func:`.relationship` and others.  Allows two or
      more declarative base classes to share the same registry of class
      names for simplified inter-base relationships.

    :param metaclass:
      Defaults to :class:`~sqlalchemy_unchained.DeclarativeMeta`. The metaclass
      to use as the meta type of the generated declarative base class. If you
      want to customize this, your metaclass must extend
      :class:`~sqlalchemy_unchained.DeclarativeMeta`.
    """
    if not isinstance(model, DeclarativeMeta):
        def make_model_metaclass(name, bases, clsdict):
            clsdict['__abstract__'] = True
            clsdict['__module__'] = model.__module__
            if hasattr(model, 'Meta'):
                clsdict['Meta'] = model.Meta
            if hasattr(model, META_OPTIONS_FACTORY_CLASS_ATTR_NAME):
                clsdict[META_OPTIONS_FACTORY_CLASS_ATTR_NAME] = \
                    getattr(model, META_OPTIONS_FACTORY_CLASS_ATTR_NAME)
            return metaclass(name, bases, clsdict)

        if (metadata is not None
                and metadata.naming_convention is _SQLA_DEFAULT_NAMING_CONVENTION):
            metadata.naming_convention = METADATA_NAMING_CONVENTION

        model = _declarative_base(
            bind=bind,
            cls=model,
            class_registry=class_registry,
            name=name,
            mapper=mapper,
            metadata=metadata or MetaData(naming_convention=METADATA_NAMING_CONVENTION),
            metaclass=make_model_metaclass,
            # use the model's __init__ constructor if it's present
            constructor=(None if getattr(model, '__init__') != object.__init__
                         else _declarative_constructor),
        )
        _ModelRegistry().register_base_model_class(model)

    # if user passed in a declarative base and a metadata for some reason,
    # make sure the base uses the metadata
    if metadata is not None and model.metadata is not metadata:
        model.metadata = metadata

    return model


def scoped_session_factory(bind=None, scopefunc=None, query_cls=BaseQuery, **kwargs):
    """
    Creates a scoped session using :class:`~sqlalchemy.orm.session.sessionmaker`.
    See the SQLAlchemy documentation on
    `Contextual Sessions <https://docs.sqlalchemy.org/en/latest/orm/contextual.html>`_
    to learn more.

    :param bind: An :class:`~sqlalchemy.engine.Engine` or other
                 :class:`~sqlalchemy.engine.Connectable` with which newly
                 created :class:`~sqlalchemy.orm.session.Session` objects will
                 be associated.
    :param scopefunc: An optional function which defines the current scope. If
                      not passed, the :class:`~sqlalchemy.orm.scoping.scoped_session`
                      object assumes “thread-local” scope, and will use a Python
                      ``threading.local()`` in order to maintain the current
                      :class:`~sqlalchemy.orm.session.Session`. If passed, the
                      function should return a hashable token; this token will be
                      used as the key in a dictionary in order to store and
                      retrieve the current :class:`~sqlalchemy.orm.session.Session`.
    :param query_cls: Class which should be used to create new ``Query`` objects, as
                      returned by :attr:`~sqlalchemy_unchained.ModelManager.query`.
    :param kwargs: Any extra kwargs to pass along to
                   :class:`~sqlalchemy.orm.session.sessionmaker`.
    """
    return scoped_session(sessionmaker(bind=bind, query_cls=query_cls, **kwargs),
                          scopefunc=scopefunc)


def init_sqlalchemy_unchained(database_uri, session_scopefunc=None, query_cls=BaseQuery,
                              isolation_level=None, **kwargs):
    """
    Main entry point for connecting to the database.

    :param database_uri: The SQLAlchemy database URI to connect to.
    :param session_scopefunc: The function to use for automatically scoping the session.
                              Defaults to ``None``, which means you have full control
                              over the session lifecycle.
    :param query_cls: Class which should be used to create new ``Query`` objects, as
                      returned by :attr:`~sqlalchemy_unchained.ModelManager.query`.
    :param isolation_level: The isolation level to use for the engine connection.
    :param kwargs: Any extra keyword arguments to pass to :func:`declarative_base`.
    :return: Tuple[engine, Session, Model, relationship]
    """
    isolation_level = isolation_level or (
        'REPEATABLE READ' if database_uri.startswith('postgresql') else None)
    if isolation_level:
        engine = create_engine(database_uri, isolation_level=isolation_level)
    else:
        engine = create_engine(database_uri)

    Session = scoped_session_factory(bind=engine, scopefunc=session_scopefunc,
                                     query_cls=query_cls)
    SessionManager.set_session_factory(Session)
    Model = declarative_base(bind=engine, **kwargs)
    relationship = _wrap_with_default_query_class(_relationship, query_cls)

    return engine, Session, Model, relationship

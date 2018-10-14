import functools

from py_meta_utils import META_OPTIONS_FACTORY_CLASS_ATTR_NAME
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import (declarative_base as _declarative_base)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import scoped_session, sessionmaker, relationship as _relationship

from .base_model import BaseModel, _QueryProperty
from .base_model_metaclass import DeclarativeMeta
from .base_query import BaseQuery, QueryMixin
from .foreign_key import foreign_key
from .model_meta_options import ColumnMetaOption, ModelMetaOptionsFactory
from .model_registry import _ModelRegistry
from .validation import (BaseValidator, Required, ValidationError, ValidationErrors,
                         validates)


def _set_default_query_class(d, query_cls):
    if 'query_class' not in d:
        d['query_class'] = query_cls


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


def declarative_base(session_factory, bind=None, metadata=None, mapper=None,
                     model=BaseModel, name='Model', query_class=BaseQuery,
                     class_registry=None, metaclass=DeclarativeMeta):
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

        model = _declarative_base(
            bind=bind,
            cls=model,
            class_registry=class_registry,
            name=name,
            mapper=mapper,
            metadata=metadata,
            metaclass=make_model_metaclass,
            constructor=None,  # use BaseModel's explicitly declared constructor
        )
        _ModelRegistry().register_base_model_class(model)

    # if user passed in a declarative base and a metaclass for some reason,
    # make sure the base uses the metaclass
    if metadata is not None and model.metadata is not metadata:
        model.metadata = metadata

    if not getattr(model, 'query_class', None):
        model.query_class = query_class
    model.query = _QueryProperty(session_factory)

    return model


def scoped_session_factory(bind=None, scopefunc=None, **kwargs):
    return scoped_session(sessionmaker(bind=bind, **kwargs), scopefunc=scopefunc)


def init_sqlalchemy_unchained(db_uri, session_scopefunc=None, **kwargs):
    """
    Main entry point for connecting to the database.

    :param db_uri: The SQLAlchemy database URI to connect to.
    :param session_scopefunc: The function to use for automatically scoping the session.
                              Defaults to ``None``, which means you have full control
                              over the session lifecycle.
    :param kwargs: Any extra keyword arguments to pass to :func:`declarative_base`.
    :return: Tuple[engine, Session, Model, relationship]
    """
    engine = create_engine(db_uri)
    Session = scoped_session_factory(bind=engine, scopefunc=session_scopefunc)
    Model = declarative_base(Session, bind=engine, **kwargs)
    relationship = _wrap_with_default_query_class(_relationship, Model.query_class)
    return engine, Session, Model, relationship

from sqlalchemy import *
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import (declarative_base as _declarative_base,
                                        declared_attr)
from sqlalchemy.ext.declarative.base import _declarative_constructor
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import Query, Session, scoped_session, sessionmaker
from sqlalchemy.orm import relationship
from .base_model import BaseModel, _QueryProperty
from .foreign_key import foreign_key
from .meta.base_model_metaclass import DeclarativeMeta
from .meta.model_meta_options import (
    _TestingMetaOption,
    ColumnMetaOption,
    CreatedAtColumnMetaOption,
    LazyMappedMetaOption,
    MetaOption,
    PolymorphicBaseTablenameMetaOption,
    PolymorphicIdentityMetaOption,
    PolymorphicJoinedPkColumnMetaOption,
    PolymorphicMetaOption,
    PolymorphicOnColumnMetaOption,
    PrimaryKeyColumnMetaOption,
    ReprMetaOption,
    TableMetaOption,
    UpdatedAtColumnMetaOption,
)
from .meta.model_meta_options_factory import ModelMetaOptionsFactory
from .meta.model_registry import ModelRegistry


def declarative_base(session_factory, bind=None, metadata=None, mapper=None,
                     model=BaseModel, name='Model', constructor=_declarative_constructor,
                     query_class=Query, class_registry=None, metaclass=DeclarativeMeta):
    if not isinstance(model, DeclarativeMeta):
        def make_model_metaclass(name, bases, clsdict):
            clsdict['__abstract__'] = True
            clsdict['__module__'] = model.__module__
            if hasattr(model, 'Meta'):
                clsdict['Meta'] = model.Meta
            if hasattr(model, '_meta_options_factory_class'):
                clsdict['_meta_options_factory_class'] = model._meta_options_factory_class
            return metaclass(name, bases, clsdict)

        model = _declarative_base(
            bind=bind,
            cls=model,
            class_registry=class_registry,
            name=name,
            mapper=mapper,
            metadata=metadata,
            metaclass=make_model_metaclass,
            constructor=constructor,
        )

    # if user passed in a declarative base and a metaclass for some reason,
    # make sure the base uses the metaclass
    if metadata is not None and model.metadata is not metadata:
        model.metadata = metadata

    if not getattr(model, 'query_class', None):
        model.query_class = query_class
    model.query = _QueryProperty(session_factory)

    return model


def scoped_session_factory(bind=None, scopefunc=None, **kwargs):
    return scoped_session(sessionmaker(bind=bind, **kwargs),
                          scopefunc=scopefunc)

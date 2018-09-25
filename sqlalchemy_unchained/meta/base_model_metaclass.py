import sqlalchemy as sa

from py_meta_utils import McsArgs, McsInitArgs, deep_getattr
from sqlalchemy.ext.declarative import (
    DeclarativeMeta as BaseDeclarativeMeta, declared_attr)
from sqlalchemy.schema import _get_table_key

from .model_meta_options_factory import ModelMetaOptionsFactory
from ..utils import snake_case

# the `should_set_tablename` function, and the `NameMetaMixin` and `BindMetaMixin`
# classes are copied from the `flask_sqlalchemy.model` module source (3-clause BSD)


def should_set_tablename(cls):
    """
    Determine whether ``__tablename__`` should be automatically generated
    for a model.

    * If no class in the MRO sets a name, one should be generated.
    * If a declared attr is found, it should be used instead.
    * If a name is found, it should be used if the class is a mixin, otherwise
      one should be generated.
    * Abstract models should not have one generated.

    Later, :meth:`._BoundDeclarativeMeta.__table_cls__` will determine if the
    model looks like single or joined-table inheritance. If no primary key is
    found, the name will be unset.
    """
    if (
        cls.__dict__.get('__abstract__', False)
        or not any(isinstance(b, BaseDeclarativeMeta) for b in cls.__mro__[1:])
    ):
        return False

    for base in cls.__mro__:
        if '__tablename__' not in base.__dict__:
            continue

        if isinstance(base.__dict__['__tablename__'], declared_attr):
            return False

        return not (
            base is cls
            or base.__dict__.get('__abstract__', False)
            or not isinstance(base, BaseDeclarativeMeta)
        )

    return True


class NameMetaMixin:
    def __init__(cls, name, bases, d):
        if should_set_tablename(cls):
            cls.__tablename__ = snake_case(cls.__name__)

        super(NameMetaMixin, cls).__init__(name, bases, d)

        # __table_cls__ has run at this point
        # if no table was created, use the parent table
        if (
            '__tablename__' not in cls.__dict__
            and '__table__' in cls.__dict__
            and cls.__dict__['__table__'] is None
        ):
            del cls.__table__

    def __table_cls__(cls, *args, **kwargs):
        """This is called by SQLAlchemy during mapper setup. It determines the
        final table object that the model will use.

        If no primary key is found, that indicates single-table inheritance,
        so no table will be created and ``__tablename__`` will be unset.
        """
        # check if a table with this name already exists
        # allows reflected tables to be applied to model by name
        key = _get_table_key(args[0], kwargs.get('schema'))

        if key in cls.metadata.tables:
            return sa.Table(*args, **kwargs)

        # if a primary key or constraint is found, create a table for
        # joined-table inheritance
        for arg in args:
            is_pk_column = isinstance(arg, sa.Column) and arg.primary_key
            is_pk_constraint = isinstance(arg, sa.PrimaryKeyConstraint)
            if is_pk_column or is_pk_constraint:
                return sa.Table(*args, **kwargs)

        # if no base classes define a table, return one
        # ensures the correct error shows up when missing a primary key
        for base in cls.__mro__[1:-1]:
            if '__table__' in base.__dict__:
                break
        else:
            return sa.Table(*args, **kwargs)

        # single-table inheritance, use the parent tablename
        if '__tablename__' in cls.__dict__:
            del cls.__tablename__


class BindMetaMixin:
    def __init__(cls, name, bases, d):
        bind_key = (
            d.pop('__bind_key__', None)
            or getattr(cls, '__bind_key__', None)
        )

        super(BindMetaMixin, cls).__init__(name, bases, d)

        if bind_key is not None and hasattr(cls, '__table__'):
            cls.__table__.info['bind_key'] = bind_key


class DeclarativeMeta(NameMetaMixin, BindMetaMixin, BaseDeclarativeMeta):
    def __new__(mcs, name, bases, clsdict):
        from .model_registry import ModelRegistry

        mcs_args = McsArgs(mcs, name, bases, clsdict)
        ModelRegistry()._ensure_correct_base_model(mcs_args)

        factory_cls = deep_getattr(
            clsdict, mcs_args.bases, '_meta_options_factory_class',
            ModelMetaOptionsFactory)
        options_factory: ModelMetaOptionsFactory = factory_cls()
        options_factory._contribute_to_class(mcs_args)

        if options_factory.abstract:
            return super().__new__(*mcs_args)

        mcs._pre_mcs_new(mcs, mcs_args)
        ModelRegistry().register_new(mcs_args)
        return super().__new__(*mcs_args)

    def __init__(cls, name, bases, clsdict):
        # for some as-yet-not-understood reason, the arguments python passes
        # to __init__ do not match those we gave to __new__ (namely, the
        # bases parameter passed to __init__ is what the class was declared
        # with, instead of the new bases the model_registry determined it
        # should have. and in fact, __new__ does the right thing - it uses
        # the correct bases, and the generated class has the correct bases,
        # yet still, the ones passed to __init__ are wrong. however at this
        # point (inside __init__), because the class has already been
        # constructed, changing the bases argument doesn't seem to have any
        # effect (and that agrees with what conceptually should be the case).
        # Sooo, we're passing the correct arguments up the chain, to reduce
        # confusion, just in case anybody needs to inspect them)
        _, name, bases, clsdict = cls._meta._mcs_args

        if cls._meta.abstract:
            super().__init__(name, bases, clsdict)

        if should_set_tablename(cls):
            cls.__tablename__ = snake_case(cls.__name__)

        from .model_registry import ModelRegistry
        if not ModelRegistry().enable_lazy_mapping or \
                (not cls._meta.abstract and not cls._meta.lazy_mapped):
            cls._pre_mcs_init()
            super().__init__(name, bases, clsdict)
            cls._post_mcs_init()

        if not cls._meta.abstract:
            ModelRegistry().register(McsInitArgs(cls, name, bases, clsdict))

    def _pre_mcs_new(cls, mcs_args: McsArgs):
        pass

    def _pre_mcs_init(cls):
        """
        Callback for BaseModelMetaclass subclasses to run code just before a
        concrete Model class gets registered with SQLAlchemy.

        This is intended to be used for advanced meta options implementations.
        """
        # technically you could also put a @classmethod with the same name on
        # the Model class, if you prefer that approach

    def _post_mcs_init(cls):
        """
        Callback for BaseModelMetaclass subclasses to run code just after a
        concrete Model class gets registered with SQLAlchemy.

        This is intended to be used for advanced meta options implementations.
        """

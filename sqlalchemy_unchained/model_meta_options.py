import os
import sqlalchemy as sa

from py_meta_utils import (AbstractMetaOption, McsArgs, MetaOption,
                           MetaOptionsFactory, deep_getattr)
from sqlalchemy import func as sa_func, types as sa_types
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_unchained.utils import snake_case, _missing
from typing import *


TRUTHY_VALUES = {'true', 't', 'yes' 'y', '1'}


class ColumnMetaOption(MetaOption):
    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        value = super().get_value(meta, base_model_meta, mcs_args)
        return self.default if value is True else value

    def check_value(self, value, mcs_args: McsArgs):
        msg = f'{self.name} Meta option on {mcs_args.repr} ' \
              f'must be a str, bool or None'
        assert value is None or isinstance(value, (bool, str)), msg

    def contribute_to_class(self, mcs_args: McsArgs, col_name):
        is_polymorphic = mcs_args.Meta.polymorphic
        is_polymorphic_base = mcs_args.Meta._is_base_polymorphic_model

        if (mcs_args.Meta.abstract
                or (is_polymorphic and not is_polymorphic_base)):
            return

        if col_name and col_name not in mcs_args.clsdict:
            mcs_args.clsdict[col_name] = self.get_column(mcs_args)

    def get_column(self, mcs_args: McsArgs):
        raise NotImplementedError


class PrimaryKeyColumnMetaOption(ColumnMetaOption):
    def __init__(self, name='pk', default=_missing, inherit=True):
        super().__init__(name=name, default=default, inherit=inherit)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        value = super().get_value(meta, base_model_meta, mcs_args)
        if value is not _missing:
            return value

        from .model_registry import ModelRegistry
        return ModelRegistry().default_primary_key_column

    def get_column(self, mcs_args: McsArgs):
        return sa.Column(sa.Integer, primary_key=True)


class CreatedAtColumnMetaOption(ColumnMetaOption):
    def __init__(self, name='created_at', default='created_at', inherit=True):
        super().__init__(name=name, default=default, inherit=inherit)

    def get_column(self, mcs_args: McsArgs):
        return sa.Column(sa.DateTime, server_default=sa_func.now())


class UpdatedAtColumnMetaOption(ColumnMetaOption):
    def __init__(self, name='updated_at', default='updated_at', inherit=True):
        super().__init__(name=name, default=default, inherit=inherit)

    def get_column(self, mcs_args: McsArgs):
        return sa.Column(sa.DateTime,
                         server_default=sa_func.now(), onupdate=sa_func.now())


class ReprMetaOption(MetaOption):
    def __init__(self, name='repr', default=None, inherit=True):
        super().__init__(name, default=default or ('id',), inherit=inherit)


class LazyMappedMetaOption(MetaOption):
    def __init__(self, name='lazy_mapped', default=False, inherit=True):
        super().__init__(name=name, default=default, inherit=inherit)


class _TestingMetaOption(MetaOption):
    def __init__(self):
        super().__init__('_testing_', default=None, inherit=True)


class ValidationMetaOption(MetaOption):
    def __init__(self):
        super().__init__('validation', default=True, inherit=False)


class PolymorphicBaseTablenameMetaOption(MetaOption):
    def __init__(self):
        super().__init__('_base_tablename', default=None, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if base_model_meta and not base_model_meta.abstract:
            bm = base_model_meta._mcs_args
            clsdicts = [bm.clsdict] + [b.Meta._mcs_args.clsdict
                                       for b in bm.bases
                                       if hasattr(b, 'Meta')]
            declared_attrs = [isinstance(d.get('__tablename__'), declared_attr)
                              for d in clsdicts]
            if any(declared_attrs):
                return None
            return bm.clsdict.get('__tablename__', snake_case(bm.name))


class PolymorphicOnColumnMetaOption(ColumnMetaOption):
    def __init__(self, name='polymorphic_on', default='discriminator'):
        super().__init__(name=name, default=default)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if mcs_args.Meta.polymorphic not in {'single', 'joined'}:
            return None
        return super().get_value(meta, base_model_meta, mcs_args)

    def contribute_to_class(self, mcs_args: McsArgs, col_name):
        if mcs_args.Meta.polymorphic not in {'single', 'joined'}:
            return

        # maybe add the polymorphic_on discriminator column
        super().contribute_to_class(mcs_args, col_name)

        mapper_args = mcs_args.clsdict.get('__mapper_args__', {})
        if (mcs_args.Meta._is_base_polymorphic_model
                and 'polymorphic_on' not in mapper_args):
            mapper_args['polymorphic_on'] = mcs_args.clsdict[col_name]
            mcs_args.clsdict['__mapper_args__'] = mapper_args

    def get_column(self, model_meta_options):
        return sa.Column(sa_types.String)


class PolymorphicJoinedPkColumnMetaOption(ColumnMetaOption):
    def __init__(self):
        # name, default, and inherited are all ignored for this option
        super().__init__(name='_', default='_')

    def contribute_to_class(self, mcs_args: McsArgs, value):
        meta = mcs_args.Meta
        if meta.abstract or not meta._base_tablename:
            return

        pk = meta.pk or 'id'  # FIXME is this default a good idea?
        if (meta.polymorphic == 'joined'
                and not meta._is_base_polymorphic_model
                and pk not in mcs_args.clsdict):
            mcs_args.clsdict[pk] = self.get_column(mcs_args)

    def get_column(self, mcs_args: McsArgs):
        from .foreign_key import foreign_key
        return foreign_key(mcs_args.Meta._base_tablename,
                           primary_key=True, fk_col=mcs_args.Meta.pk)


class PolymorphicTableArgsMetaOption(MetaOption):
    def __init__(self):
        # name, default, and inherited are all ignored for this option
        super().__init__(name='_', default='_')

    def contribute_to_class(self, mcs_args: McsArgs, value):
        if (mcs_args.Meta.polymorphic == 'single'
                and mcs_args.Meta._is_base_polymorphic_model):
            mcs_args.clsdict['__table_args__'] = None


class PolymorphicIdentityMetaOption(MetaOption):
    def __init__(self, name='polymorphic_identity', default=None):
        super().__init__(name=name, default=default, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if mcs_args.Meta.polymorphic in {False, '_fully_manual_'}:
            return None

        identifier = super().get_value(meta, base_model_meta, mcs_args)
        mapper_args = mcs_args.clsdict.get('__mapper_args__', {})
        return mapper_args.get('polymorphic_identity',
                               identifier or mcs_args.name)

    def contribute_to_class(self, mcs_args: McsArgs, identifier):
        if mcs_args.Meta.polymorphic in {False, '_fully_manual_'}:
            return

        mapper_args = mcs_args.clsdict.get('__mapper_args__', {})
        if 'polymorphic_identity' not in mapper_args:
            mapper_args['polymorphic_identity'] = identifier
            mcs_args.clsdict['__mapper_args__'] = mapper_args


class PolymorphicMetaOption(MetaOption):
    def __init__(self):
        super().__init__('polymorphic', default=False, inherit=True)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        mapper_args = mcs_args.clsdict.get('__mapper_args__', {})
        if isinstance(mapper_args, declared_attr):
            return '_fully_manual_'
        elif 'polymorphic_on' in mapper_args:
            return '_manual_'

        value = super().get_value(meta, base_model_meta, mcs_args)
        return 'joined' if value is True else value

    def check_value(self, value, mcs_args: McsArgs):
        if value in {'_manual_', '_fully_manual_'}:
            return

        valid = ['joined', 'single', True, False]
        msg = '{name} Meta option on {model} must be one of {choices}'.format(
            name=self.name,
            model=mcs_args.repr,
            choices=', '.join(f'{c!r}' for c in valid))
        assert value in valid, msg


class TableMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name='table', default=_missing, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        manual = mcs_args.clsdict.get('__tablename__')
        if isinstance(manual, declared_attr):
            return None
        elif manual:
            return manual

        value = super().get_value(meta, base_model_meta, mcs_args)
        if value:
            return value
        elif 'selectable' in mcs_args.clsdict:  # db.MaterializedView
            return snake_case(mcs_args.name)

    def contribute_to_class(self, mcs_args: McsArgs, value):
        if value:
            mcs_args.clsdict['__tablename__'] = value


class ModelMetaOptionsFactory(MetaOptionsFactory):
    def _get_meta_options(self) -> List[MetaOption]:
        """"
        Define fields allowed in the Meta class on end-user models, and the
        behavior of each.

        Custom ModelMetaOptions classes should override this method to customize
        the options supported on class Meta of end-user models.
        """
        testing_options = [_TestingMetaOption()] if _is_testing() else []

        # when options require another option, its dependent must be listed.
        # options in this list are not order-dependent, except where noted.
        # all ColumnMetaOptions subclasses require PolymorphicMetaOption
        return testing_options + [
            AbstractMetaOption(),  # required; must be first
            LazyMappedMetaOption(),
            TableMetaOption(),
            ReprMetaOption(),
            ValidationMetaOption(),

            PolymorphicMetaOption(),  # must be first of all polymorphic options
            PolymorphicOnColumnMetaOption(),
            PolymorphicIdentityMetaOption(),
            PolymorphicBaseTablenameMetaOption(),
            PolymorphicJoinedPkColumnMetaOption(),  # requires _BaseTablename

            # must be after PolymorphicJoinedPkColumnMetaOption
            PrimaryKeyColumnMetaOption(),
            CreatedAtColumnMetaOption(),
            UpdatedAtColumnMetaOption(),
        ]

    def _contribute_to_class(self, mcs_args: McsArgs):
        options = self._get_meta_options()
        if not _is_testing() and not isinstance(options[0], AbstractMetaOption):
            raise Exception('The first option in _get_model_meta_options '
                            'must be an instance of AbstractMetaOption')

        return super()._contribute_to_class(mcs_args)

    @property
    def _is_base_polymorphic_model(self):
        if not self.polymorphic:
            return False
        base_meta = deep_getattr({}, self._mcs_args.bases, 'Meta')
        return base_meta.abstract

    @property
    def _model_repr(self):
        return self._mcs_args.repr

    def __repr__(self):
        return '<{cls} model={model!r} model_meta_options={attrs!r}>'.format(
            cls=self.__class__.__name__,
            model=self._model_repr,
            attrs={option.name: getattr(self, option.name, None)
                   for option in self._get_meta_options()})


def _is_testing():
    return os.getenv('SQLA_TESTING', 'f').lower() in TRUTHY_VALUES

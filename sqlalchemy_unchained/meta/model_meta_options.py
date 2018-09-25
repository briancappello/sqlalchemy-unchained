import sqlalchemy as sa

from py_meta_utils import McsArgs, MetaOption
from sqlalchemy import func as sa_func, types as sa_types
from sqlalchemy.ext.declarative import declared_attr

from ..utils import snake_case, _missing


class ColumnMetaOption(MetaOption):
    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        value = super().get_value(meta, base_model_meta, mcs_args)
        return self.default if value is True else value

    def check_value(self, value, mcs_args: McsArgs):
        msg = f'{self.name} Meta option on {mcs_args.model_repr} ' \
              f'must be a str, bool or None'
        assert value is None or isinstance(value, (bool, str)), msg

    def contribute_to_class(self, mcs_args: McsArgs, col_name):
        is_polymorphic = mcs_args.model_meta.polymorphic
        is_polymorphic_base = mcs_args.model_meta._is_base_polymorphic_model

        if (mcs_args.model_meta.abstract
                or (is_polymorphic and not is_polymorphic_base)):
            return

        if col_name and col_name not in mcs_args.clsdict:
            mcs_args.clsdict[col_name] = self.get_column(mcs_args)

    def get_column(self, mcs_args: McsArgs):
        raise NotImplementedError


class PrimaryKeyColumnMetaOption(ColumnMetaOption):
    def __init__(self, name='pk', default='id', inherit=True):
        super().__init__(name=name, default=default, inherit=inherit)

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


class PolymorphicBaseTablenameMetaOption(MetaOption):
    def __init__(self):
        super().__init__('_base_tablename', default=None, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if base_model_meta and not base_model_meta.abstract:
            bm = base_model_meta._mcs_args
            clsdicts = [bm.clsdict] + [b._meta._mcs_args.clsdict
                                       for b in bm.bases
                                       if hasattr(b, '_meta')]
            declared_attrs = [isinstance(d.get('__tablename__'), declared_attr)
                              for d in clsdicts]
            if any(declared_attrs):
                return None
            return bm.clsdict.get('__tablename__', snake_case(bm.name))


class PolymorphicOnColumnMetaOption(ColumnMetaOption):
    def __init__(self, name='polymorphic_on', default='discriminator'):
        super().__init__(name=name, default=default)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if mcs_args.model_meta.polymorphic not in {'single', 'joined'}:
            return None
        return super().get_value(meta, base_model_meta, mcs_args)

    def contribute_to_class(self, mcs_args: McsArgs, col_name):
        if mcs_args.model_meta.polymorphic not in {'single', 'joined'}:
            return

        # maybe add the polymorphic_on discriminator column
        super().contribute_to_class(mcs_args, col_name)

        mapper_args = mcs_args.clsdict.get('__mapper_args__', {})
        if (mcs_args.model_meta._is_base_polymorphic_model
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
        model_meta = mcs_args.model_meta
        if model_meta.abstract or not model_meta._base_tablename:
            return

        pk = model_meta.pk or 'id'  # FIXME is this default a good idea?
        if (model_meta.polymorphic == 'joined'
                and not model_meta._is_base_polymorphic_model
                and pk not in mcs_args.clsdict):
            mcs_args.clsdict[pk] = self.get_column(mcs_args)

    def get_column(self, mcs_args: McsArgs):
        from ..foreign_key import foreign_key
        return foreign_key(mcs_args.model_meta._base_tablename,
                           primary_key=True, fk_col=mcs_args.model_meta.pk)


class PolymorphicTableArgsMetaOption(MetaOption):
    def __init__(self):
        # name, default, and inherited are all ignored for this option
        super().__init__(name='_', default='_')

    def contribute_to_class(self, mcs_args: McsArgs, value):
        if (mcs_args.model_meta.polymorphic == 'single'
                and mcs_args.model_meta._is_base_polymorphic_model):
            mcs_args.clsdict['__table_args__'] = None


class PolymorphicIdentityMetaOption(MetaOption):
    def __init__(self, name='polymorphic_identity', default=None):
        super().__init__(name=name, default=default, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if mcs_args.model_meta.polymorphic in {False, '_fully_manual_'}:
            return None

        identifier = super().get_value(meta, base_model_meta, mcs_args)
        mapper_args = mcs_args.clsdict.get('__mapper_args__', {})
        return mapper_args.get('polymorphic_identity',
                               identifier or mcs_args.name)

    def contribute_to_class(self, mcs_args: McsArgs, identifier):
        if mcs_args.model_meta.polymorphic in {False, '_fully_manual_'}:
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
            model=mcs_args.model_repr,
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

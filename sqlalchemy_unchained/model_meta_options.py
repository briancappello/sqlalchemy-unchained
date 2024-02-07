from __future__ import annotations

import os
import typing as t

import sqlalchemy as sa

from py_meta_utils import (
    AbstractMetaOption,
    McsArgs,
    MetaOption,
    MetaOptionsFactory,
    deep_getattr,
)
from sqlalchemy import func as sa_func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import column_property, ColumnProperty, RelationshipProperty
from sqlalchemy_unchained.utils import snake_case, _missing

from .model_registry import ModelRegistry
from .utils import _add_arg_to_table_args, _get_column_names


TRUTHY_VALUES = {"true", "t", "yes" "y", "1"}


class ColumnMetaOption(MetaOption):
    """
    A :class:`~py_meta_utils.MetaOption` subclass that simplifies adding columns
    to models. For example::

        import sqlalchemy as sa

        from sqlalchemy_unchained import ColumnMetaOption


        class NameColumnMetaOption(ColumnMetaOption):
            def __init__():
                super().__init__(name='name', default='name', inherit=True)

            def get_column(mcs_args):
                return sa.Column(sa.String, nullable=False)
    """

    def check_value(self, value: t.Any, mcs_args: McsArgs):
        if not (value is None or isinstance(value, str)):
            raise TypeError(
                "{name} Meta option on {cls} must be a str or None".format(
                    name=self.name,
                    cls=mcs_args.qualname,
                )
            )

    def contribute_to_class(self, mcs_args: McsArgs, col_name: str) -> None:
        if self.should_contribute_to_class(mcs_args, col_name):
            mcs_args.clsdict[col_name] = self.get_column(mcs_args)

    def should_contribute_to_class(self, mcs_args: McsArgs, col_name: str) -> bool:
        is_polymorphic = mcs_args.Meta.polymorphic  # type: ignore
        is_polymorphic_base = mcs_args.Meta._is_base_polymorphic_model  # type: ignore

        if mcs_args.Meta.abstract or (  # type: ignore
            is_polymorphic and not is_polymorphic_base
        ):
            return False

        return bool(col_name and col_name not in mcs_args.clsdict)

    def get_column(self, mcs_args: McsArgs) -> sa.Column:
        raise NotImplementedError


class PrimaryKeyColumnMetaOption(ColumnMetaOption):
    def __init__(self):
        super().__init__(name="pk", default=_missing, inherit=True)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        value = super().get_value(meta, base_model_meta, mcs_args)
        if value is not _missing:
            return value

        from .model_registry import ModelRegistry

        return ModelRegistry().default_primary_key_column

    def should_contribute_to_class(self, mcs_args: McsArgs, col_name):
        if not super().should_contribute_to_class(mcs_args, col_name):
            return False

        # check if the user defined a primary key column
        for col in [x for x in mcs_args.clsdict.values() if isinstance(x, sa.Column)]:
            if col.primary_key:
                return False

        # check if the user defined a custom primary key constraint in __table_args__
        table_args = mcs_args.clsdict.get("__table_args__", None)
        if table_args and isinstance(table_args, (tuple, list)):
            for obj in table_args:
                if isinstance(obj, sa.PrimaryKeyConstraint):
                    return False

        return True

    def get_column(self, mcs_args: McsArgs) -> sa.Column:
        return sa.Column(sa.Integer, primary_key=True)


class CreatedAtColumnMetaOption(ColumnMetaOption):
    def __init__(self):
        super().__init__(name="created_at", default="created_at", inherit=True)

    def get_column(self, mcs_args: McsArgs) -> sa.Column:
        return sa.Column(sa.DateTime, server_default=sa_func.now(), nullable=False)


class UpdatedAtColumnMetaOption(ColumnMetaOption):
    def __init__(self):
        super().__init__(name="updated_at", default="updated_at", inherit=True)

    def get_column(self, mcs_args: McsArgs) -> sa.Column:
        return sa.Column(
            sa.DateTime,
            server_default=sa_func.now(),
            onupdate=sa_func.now(),
            nullable=False,
        )


class ReprMetaOption(MetaOption):
    def __init__(self):
        default = (ModelRegistry().default_primary_key_column,)
        super().__init__(name="repr", default=default, inherit=True)

    def check_value(self, value: t.Any, mcs_args: McsArgs):
        if not value:
            return
        elif not isinstance(value, (list, tuple)):
            raise ValueError(
                f"The `repr` Meta option on {mcs_args.qualname} "
                f"must be a list or tuple of column names."
            )


class StrMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name="str", default=None, inherit=True)

    def check_value(self, value: t.Any, mcs_args: McsArgs):
        if not value:
            return
        elif not isinstance(value, str) or value not in _get_column_names(mcs_args):
            raise ValueError(
                f"The `str` Meta option on {mcs_args.qualname} "
                f"must be a single column name."
            )


class LazyMappedMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name="lazy_mapped", default=False, inherit=True)


class _TestingMetaOption(MetaOption):
    def __init__(self):
        super().__init__("_testing_", default=None, inherit=True)


class ValidationMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name="validation", default=True, inherit=True)


class PolymorphicBaseTablenameMetaOption(MetaOption):
    def __init__(self):
        super().__init__("_base_tablename", default=None, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if base_model_meta and not base_model_meta.abstract:
            bm = base_model_meta._mcs_args
            clsdicts = [bm.clsdict] + [
                b.Meta._mcs_args.clsdict for b in bm.bases if hasattr(b, "Meta")
            ]
            declared_attrs = [
                isinstance(d.get("__tablename__"), declared_attr) for d in clsdicts
            ]
            if any(declared_attrs):
                return None
            return bm.clsdict.get("__tablename__", snake_case(bm.name))


class PolymorphicBasePkNameMetaOption(MetaOption):
    def __init__(self):
        super().__init__("_base_pk_name", default=None, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if base_model_meta and not base_model_meta.abstract:
            if base_model_meta.pk is not None:
                return base_model_meta.pk

            cols = [
                (k, v)
                for k, v in base_model_meta._mcs_args.clsdict.items()
                if isinstance(v, sa.Column)
            ]
            for name, col in cols:
                if col.primary_key and col.foreign_keys:
                    return name
            raise Exception(
                "Could not find a joined primary key column on "
                + base_model_meta._mcs_args.name
            )


class PolymorphicOnColumnMetaOption(ColumnMetaOption):
    def __init__(self, name="polymorphic_on", default="discriminator"):
        super().__init__(name=name, default=default, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if mcs_args.Meta.polymorphic not in {"single", "joined"}:  # type: ignore
            return None
        return super().get_value(meta, base_model_meta, mcs_args)

    def contribute_to_class(self, mcs_args: McsArgs, col_name):
        if mcs_args.Meta.polymorphic not in {"single", "joined"}:  # type: ignore
            return

        # maybe add the polymorphic_on discriminator column
        super().contribute_to_class(mcs_args, col_name)

        mapper_args = mcs_args.clsdict.get("__mapper_args__", {})
        if (
            mcs_args.Meta._is_base_polymorphic_model  # type: ignore
            and "polymorphic_on" not in mapper_args
        ):
            mapper_args["polymorphic_on"] = mcs_args.clsdict[col_name]
            mcs_args.clsdict["__mapper_args__"] = mapper_args

    def get_column(self, mcs_args: McsArgs) -> sa.Column:
        return sa.Column(sa.String)


class PolymorphicJoinedPkColumnMetaOption(ColumnMetaOption):
    def __init__(self):
        # name, default, and inherited are all ignored for this option
        super().__init__(name="_", default="_")

    def contribute_to_class(self, mcs_args: McsArgs, value: t.Any):
        meta = mcs_args.Meta
        if (
            meta.abstract  # type: ignore
            or meta.polymorphic != "joined"  # type: ignore
            or meta._is_base_polymorphic_model  # type: ignore
            or not meta._base_tablename  # type: ignore
        ):
            return

        if getattr(meta, "pk", _missing) is None:
            for col in [
                v
                for v in mcs_args.clsdict.values()
                if isinstance(v, (sa.Column, ColumnProperty))
            ]:
                if isinstance(col, ColumnProperty):
                    col = col._orig_columns[0]
                if col.primary_key and col.foreign_keys:
                    return
            raise Exception(
                "Could not find a joined primary key column on " + mcs_args.name
            )

        pk = getattr(meta, "pk", None) or ModelRegistry().default_primary_key_column
        if pk not in mcs_args.clsdict:
            mcs_args.clsdict[pk] = self.get_column(mcs_args, pk)

    def get_column(  # type: ignore
        self,
        mcs_args: McsArgs,
        pk,
    ) -> sa.Column:
        def _get_fk_col():
            from .foreign_key import foreign_key

            return foreign_key(
                mcs_args.Meta._base_tablename,  # type: ignore
                fk_col=mcs_args.Meta._base_pk_name,  # type: ignore
                primary_key=True,
            )

        if (
            mcs_args.bases
            and pk not in mcs_args.bases[0].Meta._mcs_args.clsdict  # type: ignore
        ):
            for b in mcs_args.bases:
                for c in b.__mro__:
                    if (
                        isinstance(getattr(c, "Meta", None), MetaOptionsFactory)
                        and pk in c.Meta._mcs_args.clsdict  # type: ignore
                    ):
                        return column_property(_get_fk_col(), getattr(c, pk))  # type: ignore
        return _get_fk_col()


class PolymorphicTableArgsMetaOption(MetaOption):
    def __init__(self):
        # name, default, and inherited are all ignored for this option
        super().__init__(name="_", default="_")

    def contribute_to_class(self, mcs_args: McsArgs, value):
        if (
            mcs_args.Meta.polymorphic == "single"  # type: ignore
            and mcs_args.Meta._is_base_polymorphic_model  # type: ignore
        ):
            mcs_args.clsdict["__table_args__"] = None


class PolymorphicIdentityMetaOption(MetaOption):
    def __init__(self, name="polymorphic_identity", default=None):
        super().__init__(name=name, default=default, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        if mcs_args.Meta.polymorphic in {False, "_fully_manual_"}:  # type: ignore
            return None

        identifier = super().get_value(meta, base_model_meta, mcs_args)
        mapper_args = mcs_args.clsdict.get("__mapper_args__", {})
        return mapper_args.get("polymorphic_identity", identifier or mcs_args.name)

    def contribute_to_class(self, mcs_args: McsArgs, identifier):
        if mcs_args.Meta.polymorphic in {False, "_fully_manual_"}:  # type: ignore
            return

        mapper_args = mcs_args.clsdict.get("__mapper_args__", {})
        if "polymorphic_identity" not in mapper_args:
            mapper_args["polymorphic_identity"] = identifier
            mcs_args.clsdict["__mapper_args__"] = mapper_args


class PolymorphicMetaOption(MetaOption):
    def __init__(self):
        super().__init__("polymorphic", default=False, inherit=True)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        mapper_args = mcs_args.clsdict.get("__mapper_args__", {})
        if isinstance(mapper_args, declared_attr):
            return "_fully_manual_"
        elif "polymorphic_on" in mapper_args:
            return "_manual_"

        value = super().get_value(meta, base_model_meta, mcs_args)
        return "joined" if value is True else value

    def check_value(self, value, mcs_args: McsArgs):
        if value in {"_manual_", "_fully_manual_"}:
            return

        valid_values = ["joined", "single", True, False]
        if value not in valid_values:
            raise ValueError(
                "{name} Meta option on {model} must be one of {choices}".format(
                    name=self.name,
                    model=mcs_args.qualname,
                    choices=", ".join("%r" % v for v in valid_values),
                )
            )


class RelationshipsMetaOption(MetaOption):
    def __init__(self):
        super().__init__("relationships", inherit=True)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        """overridden to merge with inherited value"""
        if mcs_args.Meta.abstract:  # type: ignore
            return None
        value = getattr(base_model_meta, self.name, {}) or {}
        value.update(getattr(meta, self.name, {}))
        return value

    def contribute_to_class(self, mcs_args: McsArgs, relationships):
        if mcs_args.Meta.abstract:  # type: ignore
            return

        discovered_relationships = {}

        def discover_relationships(d):
            for k, v in d.items():
                if isinstance(v, RelationshipProperty):
                    discovered_relationships[v.argument] = k
                    if v.backref and mcs_args.Meta.lazy_mapped:  # type: ignore
                        raise NotImplementedError(
                            f"Discovered a lazy-mapped backref `{k}` on "
                            f"`{mcs_args.qualname}`. Currently this "
                            "is unsupported; please use `db.relationship` with "
                            "the `back_populates` kwarg on both sides instead."
                        )

        for base in mcs_args.bases:
            discover_relationships(vars(base))
        discover_relationships(mcs_args.clsdict)

        relationships.update(discovered_relationships)


class TableMetaOption(MetaOption):
    def __init__(self):
        super().__init__(name="table", default=_missing, inherit=False)

    def get_value(self, meta, base_model_meta, mcs_args: McsArgs):
        manual = mcs_args.clsdict.get("__tablename__")
        if isinstance(manual, declared_attr):
            return None
        elif manual:
            return manual

        value = super().get_value(meta, base_model_meta, mcs_args)
        if value:
            return value
        elif "selectable" in mcs_args.clsdict:  # db.MaterializedView
            return snake_case(mcs_args.name)

    def contribute_to_class(self, mcs_args: McsArgs, value):
        if value:
            mcs_args.clsdict["__tablename__"] = value


class IndexTogetherMetaOption(MetaOption):
    """
    class SomeModel(Base):
        class Meta:
            index_together = ('one', 'two')
            index_together = ('one', 'two', dict(unique=True))
            index_together = ('one', 'two', dict(name='ix_some_model_one_two'))

        one = sa.Column(sa.String)
        two = sa.Column(sa.String)
    """

    def __init__(self):
        super().__init__(name="index_together", default=_missing, inherit=False)

    def check_value(self, value: t.Any, mcs_args: McsArgs):
        if not value:
            return

        if not isinstance(value, (list, tuple)):
            raise ValueError(
                "The `index_together` Meta option must be a tuple of "
                "column names (optionally with a dict of kwargs as the "
                "last value in the tuple)"
            )
        elif (isinstance(value[-1], dict) and len(value) < 3) or len(value) < 2:
            raise ValueError(
                "The `index_together` Meta option must contain at "
                "least two column names"
            )

        valid_col_names = _get_column_names(mcs_args)
        col_names = value[:-1] if isinstance(value[-1], dict) else value
        invalid_col_names = [x for x in col_names if x not in valid_col_names]
        if invalid_col_names:
            phrase = (
                "is not a valid column name"
                if len(invalid_col_names) == 1
                else "are not valid column names"
            )
            raise ValueError(
                f'{", ".join(invalid_col_names)} {phrase} for ' f"{mcs_args.qualname}"
            )

    def contribute_to_class(self, mcs_args: McsArgs, value: t.Any):
        if not value:
            return

        index_name = None
        index_cols = value
        index_kwargs = {}
        if isinstance(value[-1], dict):
            index_cols = value[:-1]
            index_kwargs = value[-1]
            index_name = index_kwargs.pop("name", None)

        if index_name is None:
            table = mcs_args.clsdict.get("__tablename__", snake_case(mcs_args.name))
            index_name = f'ix_{table}_{"_".join(index_cols)}'

        index = sa.Index(index_name, *index_cols, **index_kwargs)
        _add_arg_to_table_args(mcs_args, index)


class UniqueTogetherMetaOption(MetaOption):
    """
    class SomeModel(Base):
        class Meta:
            unique_together = ('one', 'two')
            unique_together = ('one', 'two', dict(name='uq_some_model_one_two'))

        one = sa.Column(sa.String)
        two = sa.Column(sa.String)
    """

    def __init__(self):
        super().__init__(name="unique_together", default=_missing, inherit=False)

    def check_value(self, value: t.Any, mcs_args: McsArgs):
        if not value:
            return

        if not isinstance(value, (list, tuple)):
            raise ValueError(
                "The `unique_together` Meta option must be a tuple of "
                "column names (optionally with a dict of kwargs as the "
                "last value in the tuple)"
            )
        elif (isinstance(value[-1], dict) and len(value) < 3) or len(value) < 2:
            raise ValueError(
                "The `unique_together` Meta option must contain at "
                "least two column names"
            )

        valid_col_names = {
            col.name or attr_name
            for attr_name, col in mcs_args.clsdict.items()
            if isinstance(col, sa.Column)
        }
        col_names = value[:-1] if isinstance(value[-1], dict) else value
        for col_name in col_names:
            if col_name not in valid_col_names:
                raise ValueError(
                    f"{col_name} is not a valid column name for " f"{mcs_args.qualname}"
                )

    def contribute_to_class(self, mcs_args: McsArgs, value: t.Any):
        if not value:
            return

        if isinstance(value[-1], dict):
            unique_constraint = sa.UniqueConstraint(*value[:-1], **value[-1])
        else:
            unique_constraint = sa.UniqueConstraint(*value)
        _add_arg_to_table_args(mcs_args, unique_constraint)


class ModelMetaOptionsFactory(MetaOptionsFactory):
    """
    The default :class:`~py_meta_utils.MetaOptionsFactory` subclass used by
    SQLAlchemy Unchained.
    """

    _options = [
        AbstractMetaOption,  # required; must be first
        LazyMappedMetaOption,
        TableMetaOption,
        ReprMetaOption,
        StrMetaOption,
        ValidationMetaOption,
        PolymorphicMetaOption,  # must be first of all polymorphic options
        PolymorphicOnColumnMetaOption,
        PolymorphicIdentityMetaOption,
        PolymorphicBaseTablenameMetaOption,
        PolymorphicBasePkNameMetaOption,
        PolymorphicJoinedPkColumnMetaOption,  # requires PolymorphicBaseTablename
        # PrimaryKeyColumnMetaOption must be after PolymorphicJoinedPkColumnMetaOption
        # All ColumnMetaOptions must be after PolymorphicMetaOption
        PrimaryKeyColumnMetaOption,
        CreatedAtColumnMetaOption,
        UpdatedAtColumnMetaOption,
        IndexTogetherMetaOption,
        UniqueTogetherMetaOption,
        RelationshipsMetaOption,
    ]

    def _get_meta_options(self) -> list[MetaOption]:
        testing_options = [_TestingMetaOption()] if _is_testing() else []
        return testing_options + super()._get_meta_options()

    def _contribute_to_class(self, mcs_args: McsArgs):
        options = self._get_meta_options()
        if not _is_testing() and not isinstance(options[0], AbstractMetaOption):
            raise Exception(
                "The first option in _get_model_meta_options "
                "must be an instance of AbstractMetaOption"
            )

        return super()._contribute_to_class(mcs_args)

    @property
    def _is_base_polymorphic_model(self):
        if not self.polymorphic:  # type: ignore
            return False
        base_meta = deep_getattr({}, self._mcs_args.bases, "Meta")
        return base_meta.abstract

    def __repr__(self):
        return "<{cls} model={model!r} model_meta_options={attrs!r}>".format(
            cls=self.__class__.__name__,
            model=self._mcs_args.qualname,
            attrs={
                option.name: getattr(self, option.name, None)
                for option in self._get_meta_options()
            },
        )


def _is_testing():
    return os.getenv("SQLA_TESTING", "f").lower() in TRUTHY_VALUES


__all__ = [
    "ColumnMetaOption",
    "ModelMetaOptionsFactory",
]

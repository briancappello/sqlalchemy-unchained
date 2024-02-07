import typing as t
import warnings

from collections import defaultdict

import sqlalchemy as sa

from py_meta_utils import McsArgs, McsInitArgs, Singleton, deep_getattr
from sqlalchemy.exc import SAWarning
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.interfaces import MapperProperty


class ModelRegistry(metaclass=Singleton):
    """
    The SQLAlchemy Unchained model registry.
    """

    enable_lazy_mapping: bool = False
    default_primary_key_column: str = "id"

    def __init__(self) -> None:
        from .base_model import BaseModel as Model

        # keyed by: full.base.model.module.name.BaseModelClassName
        # values are the base classes themselves
        # ordered by registration/discovery order, so the last class to be
        # inserted into this lookup is the correct base class to use
        self._base_model_classes: dict[str, t.Type[Model]] = {}

        # all discovered models "classes", before type.__new__ has been called:
        # - keyed by model class name
        # - order of keys signifies model class discovery order at import time
        # - values are a lookup of:
        #   - keys: module name of this particular model class
        #   - values: McsArgs(model_mcs, name, bases, clsdict)
        # this dict is used for inspecting base classes when __new__ is
        # called on a model class that extends another of the same name
        self._registry: dict[str, dict[str, McsArgs]] = defaultdict(dict)

        # actual model classes awaiting initialization (after type.__new__ but
        # before type.__init__):
        # - keyed by model class name
        # - values are McsInitArgs(model_cls, name, bases, clsdict)
        # this lookup contains the knowledge of which version of a model class
        # should maybe get mapped (BaseModelMetaclass populates this dict
        # via the register method - insertion order of the correct version of a
        # model class by name is therefore determined by the import order of
        # bundles' models modules (essentially, by the RegisterModelsHook))
        self._models: dict[str, McsInitArgs] = {}

        # like self._models, except its values are the relationships each model
        # class name expects on the other side
        # - keyed by model class name
        # - values are a dict:
        #   - keyed by the model name on the other side
        #   - value is the attribute expected to exist
        self._relationships: dict[str, dict[str, str]] = {}

        # which keys in self._models have already been initialized
        self._initialized: set[str] = set()

    def register_base_model_class(self, model) -> None:
        self._base_model_classes[model.__module__ + "." + model.__name__] = model

    def _reset(self) -> None:
        """
        This method is for use by tests only!
        """
        self._base_model_classes = {}
        self._registry = defaultdict(dict)
        self._models = {}
        self._initialized = set()
        self._relationships = {}

    def register_new(self, mcs_args: McsArgs) -> None:
        if self._should_convert_bases_to_mixins(mcs_args):
            self._convert_bases_to_mixins(mcs_args)
        self._registry[mcs_args.name][mcs_args.module or ""] = mcs_args

    def register(self, mcs_init_args: McsInitArgs) -> None:
        self._models[mcs_init_args.name] = mcs_init_args
        if not self.enable_lazy_mapping or not mcs_init_args.cls.Meta.lazy_mapped:
            self._initialized.add(mcs_init_args.name)

        relationships = mcs_init_args.cls.Meta.relationships
        if relationships:
            self._relationships[mcs_init_args.name] = relationships

    def finalize_mappings(self) -> dict[str, object]:
        """
        Returns a dictionary of the model classes that were finalized.

        Keyed by the names of the model classes, values are the classes themselves.
        """
        from sqlalchemy_unchained.base_model_metaclass import DeclarativeMeta

        # this outer loop is needed to perform initializations in the order the
        # classes were originally discovered at import time
        for name in self._registry:
            if self.should_initialize(self._models[name]):
                model_cls, name, bases, clsdict = self._models[name]
                model_cls._pre_mcs_init()
                super(DeclarativeMeta, model_cls).__init__(name, bases, clsdict)  # type: ignore
                model_cls._post_mcs_init()
                self._initialized.add(name)
        return {name: self._models[name].cls for name in self._initialized}

    def should_initialize(self, mcs_init_args: McsInitArgs) -> bool:
        """
        Whether or not the model represented by ``mcs_init_args`` should be initialized.
        """
        model_name = mcs_init_args.name

        if model_name in self._initialized:
            return False

        if model_name not in self._relationships:
            return True

        with warnings.catch_warnings():
            # not all related classes will have been initialized yet, ie they
            # might still be non-mapped from SQLAlchemy's perspective, which is
            # safe to ignore here
            filter_re = (
                r"Unmanaged access of declarative attribute \w+ from "
                r"non-mapped class \w+"
            )
            warnings.filterwarnings("ignore", filter_re, SAWarning)

            for related_model_name in self._relationships[model_name]:
                related_model = self._models[related_model_name].cls

                try:
                    other_side_relationships = self._relationships[related_model_name]
                except KeyError:
                    related_model_module = self._models[
                        related_model_name
                    ].cls.__module__
                    raise KeyError(
                        "Incomplete `relationships` Meta declaration for "
                        f"{related_model_module}.{related_model_name} "
                        f"(missing {model_name})"
                    )

                if model_name not in other_side_relationships:
                    continue
                related_attr = other_side_relationships[model_name]
                if hasattr(related_model, related_attr):
                    return True

        return False

    def _ensure_correct_base_model(self, mcs_args: McsArgs) -> None:
        """
        Makes sure the given ``mcs_args`` uses the correct BaseModel class.
        """
        if not self._base_model_classes:
            return

        correct_base = list(self._base_model_classes.values())[-1]
        for b in mcs_args.bases:
            if issubclass(b, correct_base):
                return

        mcs_args.clsdict["Meta"] = deep_getattr({}, mcs_args.bases, "Meta", None)
        mcs_args.bases = tuple([correct_base] + list(mcs_args.bases))

    def _should_convert_bases_to_mixins(self, mcs_args: McsArgs) -> bool:
        """
        Figures out whether the base classes for the given ``mcs_args`` should be
        converted to mixins (as opposed to extending BaseModel)
        """
        if mcs_args.Meta.polymorphic:  # type: ignore
            return False

        for b in mcs_args.bases:
            if b.__name__ in self._registry:
                return True

        return mcs_args.name in self._registry

    def _convert_bases_to_mixins(self, mcs_args: McsArgs) -> None:
        """
        For each base class in bases that the ModelRegistry knows about, create
        a replacement class containing the methods and attributes from the base
        class:
         - the mixin should only extend object (not db.Model)
         - if any of the attributes are MapperProperty instances (relationship,
           association_proxy, etc), then turn them into @declared_attr props
        """

        def _mixin_name(name):
            return name + "_FSQLAConvertedMixin"

        new_base_names = set()
        new_bases = []
        for b in reversed(mcs_args.bases):
            if b.__name__ not in self._registry:
                if b not in new_bases:
                    new_bases.append(b)
                continue

            _, base_name, base_bases, base_clsdict = self._registry[b.__name__][
                b.__module__
            ]

            for bb in reversed(base_bases):
                if bb.__module__ + "." + bb.__name__ in self._base_model_classes:
                    if bb not in new_bases:
                        new_bases.append(bb)
                elif (
                    bb.__name__ not in new_base_names
                    and _mixin_name(bb.__name__) not in new_base_names
                ):
                    new_base_names.add(bb.__name__)
                    new_bases.append(bb)

            clsdict: dict[str, t.Any] = {}
            for attr, value in base_clsdict.items():
                if attr in {"__name__", "__qualname__"}:
                    continue

                has_fk = isinstance(value, sa.Column) and value.foreign_keys
                if has_fk or isinstance(value, MapperProperty):
                    # programmatically add a method wrapped with declared_attr
                    # to the new mixin class
                    exec(
                        """\
@declared_attr
def {attr}(self):
    return value
""".format(
                            attr=attr
                        ),
                        {"value": value, "declared_attr": declared_attr},
                        clsdict,
                    )
                else:
                    clsdict[attr] = value

            mixin_name = _mixin_name(base_name)
            new_bases.append(type(mixin_name, (object,), clsdict))
            new_base_names.add(mixin_name)

        mcs_args.bases = tuple(reversed(new_bases))


__all__ = [
    "ModelRegistry",
]

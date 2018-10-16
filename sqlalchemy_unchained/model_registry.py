import sqlalchemy as sa

from collections import defaultdict
from py_meta_utils import McsArgs, McsInitArgs, Singleton, deep_getattr
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.interfaces import MapperProperty
from typing import *


class _ModelRegistry(metaclass=Singleton):
    enable_lazy_mapping = False
    default_primary_key_column = 'id'

    def __init__(self):
        from .base_model import BaseModel as Model

        # keyed by: full.base.model.module.name.BaseModelClassName
        # values are the base classes themselves
        # ordered by registration/discovery order, so the last class to be
        # inserted into this lookup is the correct base class to use
        self._base_model_classes = {}  # type: Dict[str, Type[Model]]

        # all discovered models "classes", before type.__new__ has been called:
        # - keyed by model class name
        # - order of keys signifies model class discovery order at import time
        # - values are a lookup of:
        #   - keys: module name of this particular model class
        #   - values: McsArgs(model_mcs, name, bases, clsdict)
        # this dict is used for inspecting base classes when __new__ is
        # called on a model class that extends another of the same name
        self._registry = defaultdict(dict)  # type: Dict[str, Dict[str, McsArgs]]

        # actual model classes awaiting initialization (after type.__new__ but
        # before type.__init__):
        # - keyed by model class name
        # - values are McsInitArgs(model_cls, name, bases, clsdict)
        # this lookup contains the knowledge of which version of a model class
        # should maybe get mapped (BaseModelMetaclass populates this dict
        # via the register method - insertion order of the correct version of a
        # model class by name is therefore determined by the import order of
        # bundles' models modules (essentially, by the RegisterModelsHook))
        self._models = {}  # type: Dict[str, McsInitArgs]

        # which keys in self._models have already been initialized
        self._initialized = set()  # type: Set[str]

    def register_base_model_class(self, model):
        self._base_model_classes[model.__module__ + '.' + model.__name__] = model

    def _reset(self):
        self._base_model_classes = {}
        self._registry = defaultdict(dict)
        self._models = {}
        self._relationships = {}
        self._initialized = set()

    def register_new(self, mcs_args: McsArgs):
        if self._should_convert_bases_to_mixins(mcs_args):
            self._convert_bases_to_mixins(mcs_args)
        self._registry[mcs_args.name][mcs_args.module] = mcs_args

    def register(self, mcs_init_args: McsInitArgs):
        self._models[mcs_init_args.name] = mcs_init_args
        if not self.enable_lazy_mapping or not mcs_init_args.cls.Meta.lazy_mapped:
            self._initialized.add(mcs_init_args.name)

    def finalize_mappings(self):
        from sqlalchemy_unchained.base_model_metaclass import DeclarativeMeta

        # this outer loop is needed to perform initializations in the order the
        # classes were originally discovered at import time
        for name in self._registry:
            if self.should_initialize(name):
                model_cls, name, bases, clsdict = self._models[name]
                model_cls._pre_mcs_init()
                super(DeclarativeMeta, model_cls).__init__(name, bases, clsdict)
                model_cls._post_mcs_init()
                self._initialized.add(name)
        return {name: self._models[name].cls for name in self._initialized}

    def should_initialize(self, model_name):
        if model_name in self._initialized:
            return False
        return True

    def _ensure_correct_base_model(self, mcs_args: McsArgs):
        if not self._base_model_classes:
            return

        correct_base = list(self._base_model_classes.values())[-1]
        for b in mcs_args.bases:
            if issubclass(b, correct_base):
                return

        mcs_args.clsdict['Meta'] = \
            deep_getattr({}, mcs_args.bases, 'Meta', None)
        mcs_args.bases = tuple([correct_base] + list(mcs_args.bases))

    def _should_convert_bases_to_mixins(self, mcs_args: McsArgs):
        if mcs_args.Meta.polymorphic:
            return False

        for b in mcs_args.bases:
            if b.__name__ in self._registry:
                return True

        return mcs_args.name in self._registry

    def _convert_bases_to_mixins(self, mcs_args: McsArgs):
        """
        For each base class in bases that the _ModelRegistry knows about, create
        a replacement class containing the methods and attributes from the base
        class:
         - the mixin should only extend object (not db.Model)
         - if any of the attributes are MapperProperty instances (relationship,
           association_proxy, etc), then turn them into @declared_attr props
        """
        def _mixin_name(name):
            return name + '_FSQLAConvertedMixin'

        new_base_names = set()
        new_bases = []
        for b in reversed(mcs_args.bases):
            if b.__name__ not in self._registry:
                if b not in new_bases:
                    new_bases.append(b)
                continue

            _, base_name, base_bases, base_clsdict = \
                self._registry[b.__name__][b.__module__]

            for bb in reversed(base_bases):
                if bb.__module__ + '.' + bb.__name__ in self._base_model_classes:
                    if bb not in new_bases:
                        new_bases.append(bb)
                elif (bb.__name__ not in new_base_names
                        and _mixin_name(bb.__name__) not in new_base_names):
                    new_base_names.add(bb.__name__)
                    new_bases.append(bb)

            clsdict = {}
            for attr, value in base_clsdict.items():
                if attr in {'__name__', '__qualname__'}:
                    continue

                has_fk = isinstance(value, sa.Column) and value.foreign_keys
                if has_fk or isinstance(value, MapperProperty):
                    # programmatically add a method wrapped with declared_attr
                    # to the new mixin class
                    exec("""\
@declared_attr
def {attr}(self):
    return value
""".format(attr=attr),
                         {'value': value, 'declared_attr': declared_attr},
                         clsdict)
                else:
                    clsdict[attr] = value

            mixin_name = _mixin_name(base_name)
            new_bases.append(type(mixin_name, (object,), clsdict))
            new_base_names.add(mixin_name)

        mcs_args.bases = tuple(reversed(new_bases))

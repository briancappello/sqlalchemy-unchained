# CHANGELOG

## v0.14.0 (2024/02/07)

- Add `py.typed` for typing support
- Improve type hints
- Drop `BaseQuery` in favor of directly using upstream `sqlalchemy.orm.Query`
- format code with `black`

## v0.13.0 (2024/02/06)

- bump minimum required Python version to 3.10+
- compatible with SQLAlchemy versions 1.3.x and 1.4.x
- convert to `pyproject.toml`

## v0.12.2 (2021/08/04)

- add `rec_getattr` and `rec_hasattr` functions for recursive attribute access
- add support for recursive getattr in automatic `Model.__repr__`
- add `str` Meta option for automatic `Model.__str__`

## v0.12.1 (2021/08/03)

- fix bug with automatic index name for `index_together`

## v0.12.0 (2021/08/03)

- update from m2r to m2rr for docs
- add `unique_together` Meta option for models
- add `index_together` Meta option for models
- add `relationships` Meta option for models (moved from Flask Unchained)

## v0.11.1 (2021/06/07)

- fix compatability with SQLAlchemy 1.4

## v0.11.0 (2020/05/07)

- make `ModelRegistry` and other protected internal classes public

## v0.10.0 (2020/01/21)

- support passing `ondelete` and `onupdate` keyword arguments to the `foreign_key` helper function

**Breaking Changes**

- removed the `__getattr__` magic method from `SessionManager`

## v0.9.1 (2019/09/30)

- fix tests for `ModelManager.filter` and `ModelManager.filter_by`

## v0.9.0 (2019/09/30)

- drop support for Python 3.5
- return `BaseQuery` from `ModelManager.filter` and `ModelManager.filter_by`

## v0.8.0 (2019/09/10)

- make the default timestamp `created_at` and `updated_at` columns not-nullable
- disable automatically adding the `Required` validator to model fields
- pass `McsInitArgs` to `ModelRegistry.should_initialize` instead of just the model class name

## v0.7.6 (2019/05/19)

- make `BaseModel.validate` a normal method, default to non-partial validation
- add `BaseModel.validate_values` as a classmethod
- fix tests

## v0.7.5 (2019/05/19)

- fix BaseModel constructor to only perform partial validation

## v0.7.4 (2019/04/21)

- bump required `alembic` version to 1.0.9 (fixes `immutabledict is not defined` error)

## v0.7.3 (2019/04/11)

- bump required `alembic` and `py-meta-utils` versions

## v0.7.2 (2019/04/11)

- fix `ModelManager.get_or_create` and `ModelManager.update_or_create`

## v0.7.1 (2019/02/25)

- disable `autoflush` for `ModelManager.get_or_create` and `ModelManager.update_or_create`
- fix project name on PyPI having spaces

## v0.7.0 (2018/12/16)

- breaking: change signature of `ModelManager.get_or_create` to take a `defaults` parameter
- add `ModelManager.update_or_create`

## v0.6.9 (2018/12/01)

- do not add a primary key column if the user defined a custom primary key constraint in `__table_args__`
- update default naming convention for foreign keys to be more human readable

## v0.6.8 (2018/11/07)

- improve support for non-integer primary keys
- add support for setting the transaction `isolation_level` of the db engine

## v0.6.7 (2018/11/03)

- the primary key meta option now checks if the model already has a user-declared primary key column, and if so, it will not add another itself

## v0.6.6 (2018/10/28)

- rename `_SessionMetaclass` to `_SessionManagerMetaclass`

## v0.6.5 (2018/10/28)

- require py-meta-utils v0.7.3
- fix automatic required validator to not be applied to foreign key columns
- fix `declarative_base` so that it correctly determines whether or not to use the passed in model's constructor

## v0.6.4 (2018/10/28)

- removed the factory_boy fix added in v0.6.3 because it really belongs in flask unchained

## v0.6.3 (2018/10/28)

- fix the `ModelRegistry.reset` method so it allows using factory_boy from `conftest.py`
- require alembic 1.0.1, py-meta-utils 0.7.2, and sqlalchemy 1.2.12

## v0.6.2 (2018/10/26)

- update `BaseQuery.get` so that tuple identifiers get converted to `int` as well
- add `ModelManager.get` query method
- add `SessionManager.delete` and `SessionManager.delete_all` methods

## v0.6.1 (2018/10/23)

- require py-meta-utils 0.7.0
- fix SessionManager tests

## v0.6.0 (2018/10/23)

- documentation improvements
- rename `DB_URI` to `DATABASE_URI`
- rename the `db_uri` argument of `init_sqlalchemy_unchained` to `database_uri`
- remove the `ModelMetaOptionsFactory._model_repr` property
- remove the `validates` decorator
- discourage the use of Active Record anti-patterns (remove `query` attribute from `BaseModel`)
- add `SessionManager` and `ModelManager` to encourage use of Data Mapper patterns
- add `query_cls` keyword argument to `init_sqlalchemy_unchained` and `scoped_session_factory`
- bugfix for `declarative_base` if a custom base model is passed in without a constructor
- configure the `MetaData` naming convention if none is provided

## v0.5.1 (2018/10/20)

- bugfix: cannot automatically determine if relationship/association_proxy attributes should be required

## v0.5.0 (2018/10/16)

- configure tox & travis
- make compatible with Python 3.5
- fix `ReprMetaOption` to pull default primary key name from `ModelRegistry()`
- `ColumnMetaOption` values should only be `str` or `None`
- bump required `py-meta-utils` to v0.6.1
- `ColumnMetaOption.check_value` should raise `TypeError` or `ValueError`, not `AssertionError`
- Move declaration of factory meta options from `ModelMetaOptionsFactory._get_meta_options()` to `ModelMetaOptionsFactory._options`
- bugfix: use correct foreign key for the primary key on joined polymorphic models
- publish documentation on read the docs

## v0.4.0 (2018/10/09)

- fix automatic required validators
- rename `ModelRegistry` to `_ModelRegistry`

## v0.3.1 (2018/10/04)

- set default primary key as a class attribute on the `ModelRegistry`

## v0.3.0 (2018/09/30)

- update to py-meta-utils 0.3

## v0.2.2 (2018/09/29)

- update to py-meta-utils 0.2

## v0.2.1 (2018/09/26)

- fix automatic Required validation (should not raise if the column has a default value)

## v0.2.0 (2018/09/26)

- implement validation for models
- wrap `sqlalchemy.orm.relationship` with the configured `Query` class
- override the `alembic` command to customize the generated migrations templates
- export `ColumnMetaOption` from the top-level `sqlalchemy_unchained` package
- export `association_proxy`, `declared_attr`, `hybrid_method`, and `hybrid_property` from the top-level `sqlalchemy_unchained` package
- add documentation
- add tests

## v0.1.0 (2018/09/24)

- initial release

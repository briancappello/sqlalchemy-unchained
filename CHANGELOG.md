# CHANGELOG

## v0.5.0 (2018/10/16)

- configure tox & travis
- make compatible with Python 3.5
- fix `ReprMetaOption` to pull default primary key name from `_ModelRegistry()`
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

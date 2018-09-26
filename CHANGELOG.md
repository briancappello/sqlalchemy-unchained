# CHANGELOG

## v0.2.0 (unreleased)

- implement validation for models
- wrap `sqlalchemy.orm.relationship` with the configured `Query` class
- override the `alembic` command to customize the generated migrations templates
- export `ColumnMetaOption` from the top-level `sqlalchemy_unchained` package
- export `association_proxy`, `declared_attr`, `hybrid_method`, and `hybrid_property` from the top-level `sqlalchemy_unchained` package
- add documentation
- add tests

## v0.1.0 (2018/09/24)

- initial release

# SQLAlchemy Unchained

Enhanced declarative models for SQLAlchemy.

## Usage

### 1. Install:

```bash
$ pip install sqlalchemy-unchained
```

And let's create a directory structure to work with:

```bash
mkdir your-project && cd your-project
mkdir your_package && mkdir db && touch setup.py
touch your_package/config.py your_package/db.py your_package/models.py
```

From now it is assumed that you are working from the `your-project` directory. All file paths at the top of code samples will be relative to this directory, and all commands should be run from this directory (unless otherwise noted).

### 2. Configure:

```python
# your_package/config.py

import os


class Config:
    PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    DB_URI = 'sqlite:///' + os.path.join(PROJECT_ROOT, 'db', 'dev.sqlite')
```

Here we're creating an on-disk SQLite database at `project-root/db/dev.sqlite`. See the official documentation on [SQLAlchemy Dialects](https://docs.sqlalchemy.org/en/latest/dialects/) to learn more about connecting to other database engines.

### 3. Connect:

```python
# your_package/db.py

from sqlalchemy.orm import relationship as _relationship
from sqlalchemy_unchained import *
from sqlalchemy_unchained import _wrap_with_default_query_class

from .config import Config


_registry = ModelRegistry()
engine = create_engine(Config.DB_URI)
Session = scoped_session_factory(bind=engine)
Model = declarative_base(Session, bind=engine)
relationship = _wrap_with_default_query_class(_relationship, Model.query_class)
```

This pattern is so common that as long as you don't need to customize any of the arguments to `create_engine`, you can use the `init_sqlalchemy_unchained` convenience function:

```python
# your_package/db.py

from sqlalchemy_unchained import *

from .config import Config


engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DB_URI)
```

### 4. Create some models

```python
# your_package/models.py

from . import db


class Parent(db.Model):
    name = db.Column(db.String, nullable=False)

    children = db.relationship('Child', back_populates='parent')


class Child(db.Model):
    name = db.Column(db.String, nullable=False)

    parent_id = db.foreign_key('Parent', nullable=False)
    parent = db.relationship('Parent', back_populates='children')
```

This is the first bit that's different from using stock SQLAlchemy. By default, models in SQLAlchemy Unchained automatically include a primary key column `id`, as well as the automatically-timestamped columns `created_at` and `updated_at`.

This is, of course, customizable. For example, if you wanted to rename the columns on `Parent` and disable timestamping on `Child`:

```python
# your_package/models.py

from . import db


class Parent(db.Model):
    class Meta:
        pk = 'pk'
        created_at = 'created'
        updated_at = 'updated'

    name = db.Column(db.String, nullable=False)

    children = db.relationship('Child', back_populates='parent')


class Child(db.Model):
    class Meta:
        created_at = None
        updated_at = None

    name = db.Column(db.String, nullable=False)

    parent_id = db.foreign_key('Parent', nullable=False)
    parent = db.relationship('Parent', back_populates='children')
```

The are other `Meta` options that SQLAlchemy Unchained supports, and we'll have a look at those in a bit. We'll also cover how to change the defaults for all models, as well as how to add support for your own custom `Meta` options. But for now, let's get migrations configured before we continue any further.

### 5. Configure database migrations

Install Alembic:

```bash
pip install alembic && alembic init db/migrations
```

Next, we need to configure Alembic to use the same database as we've already configured. This happens towards the top of the `db/migrations/env.py` file, which the `alembic init db/migrations` command generated for us. Modify the following lines:

```python
from your_package.config import Config
from your_package.db import Model
from your_package.models import *
```

For these import statements to work, we need to install our package. Let's create a minimal `setup.py`:

```python
# setup.py

from setuptools import setup, find_packages


setup(
    name='your-project',
    version='0.1.0',
    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'sqlalchemy-unchained>=0.1',
    ],
)
```

And install our package into the virtual environment you're using for development:

```bash
pip install -e .
```

That should be all that's required to get migrations working. Let's generate a migration for our models, and run it:

```bash
alembic revision --autogenerate -m 'create models'
# verify the generated migration is going to do what you want, and then run it:
alembic upgrade head
```

## Included Meta Options

### Table

```python
class Foo(db.Model):
    class Meta:
        table: str = 'foo'
```

Set to customize the name of the table in the database for the model. By default, we use the model's class name converted to snake case. 

NOTE: The snake case logic used is slightly different from that of Flask-SQLAlchemy, so if you're porting your models over and any of them have sequential upper-case letters, you will probably need to change the default.

### Primary Key

```python
class Foo(db.Model):
    class Meta:
        pk: Union[str, None] = 'id'  # 'id' is the default
```

Set to a string to customize the column name used for the primary key, or set to `None` to disable the column.

### Created At

```python
class Foo(db.Model):
    class Meta:
        created_at: Union[str, None] = 'created_at'  # 'created_at' is the default
```

Set to a string to customize the column name used for the creation timestamp, or set to `None` to disable the column.

### Updated At

```python
class Foo(db.Model):
    class Meta:
        updated_at: Union[str, None] = 'updated_at'  # 'updated_at' is the default
```

Set to a string to customize the column name used for the updated timestamp, or set to `None` to disable the column.

### Repr

```python
class Foo(db.Model):
    class Meta:
        repr: Tuple[str, ...] = ('id',)  # ('id',) is the default

print(Foo())  # prints: Foo(id=1)
```

Set to a tuple of attribute names to customize the representation of models.

### Validation

```python
class Foo(db.Model):
    class Meta:
        validation: bool = True  # True is the default
```

Set to `False` to disable validation of model instances.

### Polymorphic

```python
class Foo(db.Model):
    class Meta:
        polymorphic: Union[bool, str, None] = True  # None is the default


class Bar(Foo):
    pass
```

This meta option is disabled by default, and can be set to one of `'joined'`, `True` (an alias for `'joined'`), or `'single'`. See [here](https://docs.sqlalchemy.org/en/latest/orm/inheritance.html) for more info.

When `polymorphic` is enabled, there are two other meta options available to further customize its behavior:

```python
class Foo(db.Model):
    class Meta:
        polymorphic = True
        polymorphic_on: str = 'discriminator'  # the name of the column to use
        polymorphic_identity: str = 'models.Foo'  # the unique identifier to use for this model


class Bar(Foo):
    class Meta:
        polymorphic_identity = 'models.Bar'
```

`polymorphic_on` defaults to `'discriminator'`, and is the name of the column used to store the `polymorphic_identity`, which is the unique identifier used by SQLAlchemy to distinguish which model class a row should use. `polymorphic_identity` defaults to using each model class's name.

## Customizing Meta Options

The meta options available are configurable. Let's take a look at the implementation of the primary key meta option:

```python
import sqlalchemy as sa

from py_meta_utils import McsArgs, MetaOption


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
```

For examples sake, let's say you wanted every model to have a required name column. First we need to implement a `ColumnMetaOption`:

```python
# your_package/base_model.py

import sqlalchemy as sa

from py_meta_utils import McsArgs
from sqlalchemy_unchained import (BaseModel as _BaseModel, ColumnMetaOption, 
                                  ModelMetaOptionsFactory)

class NameColumnMetaOption(ColumnMetaOption):
    def __init__(self):
        super().__init__('name', default='name', inherit=True)
    
    def get_column(self, mcs_args: McsArgs):
        return sa.Column(sa.String, nullable=False)


class CustomModelMetaOptionsFactory(ModelMetaOptionsFactory):
    def _get_meta_options(self):
        return super()._get_meta_options() + [NameColumnMetaOption()]


class BaseModel(_BaseModel):
    _meta_options_factory_class = CustomModelMetaOptionsFactory
```

The last step is to use our customized `BaseModel` class:

```python
# your_package/db.py

from sqlalchemy_unchained import *

from .base_model import BaseModel
from .config import Config


engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DB_URI, 
                                                                 model=BaseModel)
```


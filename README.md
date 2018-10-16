# SQLAlchemy Unchained

Enhanced declarative models for SQLAlchemy.

## Usage

### Install

Requires Python 3.5+

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

### Configure

```python
# your_package/config.py

import os


class Config:
    PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    DB_URI = 'sqlite:///' + os.path.join(PROJECT_ROOT, 'db', 'dev.sqlite')
```

Here we're creating an on-disk SQLite database at `project-root/db/dev.sqlite`. See the official documentation on [SQLAlchemy Dialects](https://docs.sqlalchemy.org/en/latest/dialects/) to learn more about connecting to other database engines.

### Connect

```python
# your_package/db.py

from sqlalchemy_unchained import *

from .config import Config


engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DB_URI)
```

If you need to customize the creation of any of these parameters, this is the equivalent behind-the-scenes setup code:

```python
# your_package/db.py

from sqlalchemy.orm import relationship as _relationship
from sqlalchemy_unchained import *
from sqlalchemy_unchained import _wrap_with_default_query_class

from .config import Config


engine = create_engine(Config.DB_URI)
Session = scoped_session_factory(bind=engine)
Model = declarative_base(Session, bind=engine)
relationship = _wrap_with_default_query_class(_relationship, Model.query_class)
```

### Create some models

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

This is the first bit that's really different from using stock SQLAlchemy. By default, models in SQLAlchemy Unchained automatically include a primary key column `id`, as well as the automatically-timestamped columns `created_at` and `updated_at`.

This is customizable. For example, if you wanted to rename the columns on `Parent` and disable timestamping on `Child`:

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

### Configure database migrations

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
        pk: Union[str, None] = _ModelRegistry().default_primary_key_column = 'id'
```

Set to a string to customize the column name used for the primary key, or set to `None` to disable the column.

NOTE: Customizing the default primary key column name used for all models is different from customizing the defaults for other meta options. (You should subclass `_ModelRegistry` and set its `default_primary_key_column` attribute. This is necessary for the `foreign_key` helper function to work correctly.)

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

The meta options available are configurable. Let's take a look at the implementation of the `created_at` meta option:

```python
import sqlalchemy as sa

from py_meta_utils import McsArgs
from sqlalchemy import func as sa_func
from sqlalchemy_unchained import ColumnMetaOption


class CreatedAtColumnMetaOption(ColumnMetaOption):
    def __init__(self, name='created_at', default='created_at', inherit=True):
        super().__init__(name=name, default=default, inherit=inherit)

    def get_column(self, mcs_args: McsArgs):
        return sa.Column(sa.DateTime, server_default=sa_func.now())
```

For examples sake, let's say you wanted every model to have a required name column, but no automatic timestamping behavior. First we need to implement a `ColumnMetaOption`:

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
    _options = ModelMetaOptionsFactory._options + [NameColumnMetaOption]


class BaseModel(_BaseModel):
    _meta_options_factory_class = CustomModelMetaOptionsFactory

    class Meta:
        created_at = None
        updated_at = None
```

The last step is to tell SQLAlchemy Unchained to use our customized `BaseModel` class:

```python
# your_package/db.py

from sqlalchemy_unchained import *

from .base_model import BaseModel
from .config import Config


engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DB_URI, 
                                                                 model=BaseModel)
```

## Customizing the Default Primary Key Column Name

The primary key column is special in that knowledge of its setting is required for determining foreign key column names during model class creation. The first step is to subclass the `_ModelRegistry` and set its `default_primary_key_column` class attribute:

```python
# your_package/model_registry.py

from sqlalchemy_unchained import _ModelRegistry as BaseModelRegistry


class CustomModelRegistry(BaseModelRegistry):
    default_primary_key_column = 'pk'
```

And then, in order to inform SQLAlchemy Unchained about your customized model registry, you need call `_ModelRegistry.set_singleton_class`:

```python
# your_package/db.py

from sqlalchemy_unchained import *
from sqlalchemy_unchained import _ModelRegistry

from .config import Config
from .model_registry import CustomModelRegistry


_ModelRegistry.set_singleton_class(CustomModelRegistry)
engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DB_URI)
```

## Lazy Mapping

Lazy mapping is feature that this package introduces on top of SQLAlchemy. It's experimental, and disabled by default. In stock SQLAlchemy, when you define a model, the second that code gets imported, the base model's metaclass will register the model with SQLAlchemy's mapper. 99% of the time this is what you want to happen, but if for some reason you *don't* want that behavior, then you have to enable lazy mapping. There are two components to enabling lazy mapping.

The first step is to customize the model registry:

```python
# your_package/model_registry.py

from sqlalchemy_unchained import _ModelRegistry


class LazyModelRegistry(_ModelRegistry):
    enable_lazy_mapping = True

    def should_initialize(self, model_name: str) -> bool:
        pass # implement your custom logic for determining which models to register
        # with SQLAlchemy
```

And just like for customizing the primary key column, we need to inform `_ModelRegistry` of our subclass by calling `_ModelRegistry.set_singleton_class`:

```python
# your_package/db.py

from sqlalchemy_unchained import *
from sqlalchemy_unchained import _ModelRegistry

from .config import Config
from .model_registry import LazyModelRegistry


_ModelRegistry.set_singleton_class(LazyModelRegistry)
engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DB_URI)
```

The last step is to define your models like so:

```python
class Foo(db.Model):
    class Meta:
        lazy_mapped = True
```

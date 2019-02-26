# SQLAlchemy Unchained

Enhanced declarative models for SQLAlchemy.

## Useful Links

* [Read the Docs](https://sqlalchemy-unchained.readthedocs.io)
* [GitHub](https://github.com/briancappello/sqlalchemy-unchained)
* [PyPI](https://pypi.org/project/SQLAlchemy-Unchained/)

## Usage

### Installation

Requires Python 3.5+, SQLAlchemy and Alembic (for migrations)

```bash
$ pip install sqlalchemy-unchained
```

And let's create a directory structure to work with:

```bash
mkdir your-project && cd your-project && \
mkdir your_package && mkdir db && \
touch setup.py your_package/config.py your_package/db.py your_package/models.py
```

From now it is assumed that you are working from the `your-project` directory. All file paths at the top of code samples will be relative to this directory, and all commands should be run from this directory (unless otherwise noted).

### Configure

#### Using SQLite

```python
# your_package/config.py

import os


class Config:
    PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    DATABASE_URI = 'sqlite:///' + os.path.join(PROJECT_ROOT, 'db', 'dev.sqlite')
```

Here we're creating an on-disk SQLite database at `project-root/db/dev.sqlite`.

#### Using PostgreSQL or MariaDB/MySQL

If instead you'd like to use PostgreSQL or MariaDB/MySQL, now would be the time to configure it. For example, to use PostgreSQL with the ``psycopg2`` engine:

```python
# your_package/config.py

import os


class Config:
    DATABASE_URI = '{engine}://{user}:{pw}@{host}:{port}/{db}'.format(
        engine=os.getenv('SQLALCHEMY_DATABASE_ENGINE', 'postgresql+psycopg2'),
        user=os.getenv('SQLALCHEMY_DATABASE_USER', 'your_db_user'),
        pw=os.getenv('SQLALCHEMY_DATABASE_PASSWORD', 'your_db_user_password'),
        host=os.getenv('SQLALCHEMY_DATABASE_HOST', '127.0.0.1'),
        port=os.getenv('SQLALCHEMY_DATABASE_PORT', 5432),
        db=os.getenv('SQLALCHEMY_DATABASE_NAME', 'your_db_name'))
```

For MariaDB/MySQL, replace the ``engine`` parameter with ``mysql+mysqldb`` and the ``port`` parameter with ``3306``.

Note that you'll probably need to install the relevant driver package, eg:

```bash
# for postgresql+psycopg2
pip install --no-binary psycopg2

# for mysql+mysqldb
pip install mysqlclient
```

See the official documentation on [SQLAlchemy Dialects](https://docs.sqlalchemy.org/en/latest/dialects/) to learn more about connecting to other database engines.

### Connect

```python
# your_package/db.py

from sqlalchemy_unchained import *

from .config import Config


engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DATABASE_URI)
```

If you need to customize the creation of any of these parameters, this is what `init_sqlalchemy_unchained` is doing behind the scenes:

```python
# your_package/db.py

from sqlalchemy.orm import relationship as _relationship
from sqlalchemy_unchained import *
from sqlalchemy_unchained import _wrap_with_default_query_class

from .config import Config


engine = create_engine(Config.DATABASE_URI)
Session = scoped_session_factory(bind=engine, query_cls=BaseQuery)
SessionManager.set_session_factory(Session)
Model = declarative_base(bind=engine)
relationship = _wrap_with_default_query_class(_relationship, BaseQuery)
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

This is the first bit that's really different from using stock SQLAlchemy. By default, models in SQLAlchemy Unchained automatically have their `__tablename__` configured, and include a primary key column `id` as well as the automatically-timestamped columns `created_at` and `updated_at`.

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
        table = 'child'  # explicitly set/customize the table name
        created_at = None
        updated_at = None

    name = db.Column(db.String, nullable=False)

    parent_id = db.foreign_key('Parent', nullable=False)
    parent = db.relationship('Parent', back_populates='children')
```

The are other `Meta` options that SQLAlchemy Unchained supports, and we'll have a look at those in a bit. We'll also cover how to change the defaults for all models, as well as how to add support for your own custom `Meta` options. But for now, let's get migrations configured before we continue any further.

### Configure database migrations

Initialize Alembic:

```bash
alembic init db/migrations
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
        'sqlalchemy-unchained==0.7.1',
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

## Using SessionManager and Model Managers

SQLAlchemy Unchained encourages embracing the design patterns recommended by the Data Mapper Pattern that SQLAlchemy uses. This means we use managers (or services, if you prefer) to handle all of our interactions with the database. SQLAlchemy Unchained includes two classes to facilitate making this as easy as possible: [SessionManager](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#sessionmanager) and [ModelManager](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#modelmanager). 

[SessionManager](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#sessionmanager) is a concrete class that you can and should use directly whenever you need to interact with the database session. [ModelManager](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#modelmanager) is an abstract subclass of [SessionManager](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#sessionmanager) that you should extend for each of the models in your application:

```python
from your_package import db


class YourModel(db.Model):
    name = db.Column(db.String, nullable=False)


class YourModelManager(db.ModelManager):
    class Meta:
        model = YourModel

    def create(self, name, commit=False, **kwargs) -> YourModel:
        return super().create(name=name, commit=commit, **kwargs)

    def find_by_name(self, name) -> Union[YourModel, None]:
        return self.get_by(name=name)


instance = YourModelManager().create(name='foobar', commit=True)
```

Both [SessionManager](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#sessionmanager) and [ModelManager](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#modelmanager) are singletons, so whenever you call `SessionManager()` or `YourModelManager()`, you will always get the same instance.

## Included Meta Options

### table (`__tablename__`)

```python
class Foo(db.Model):
    class Meta:
        table: str = 'foo'
```

Set to customize the name of the table in the database for the model. By default, we use the model's class name converted to snake case. 

NOTE: The snake case logic used is slightly different from that of Flask-SQLAlchemy, so if you're porting your models over and any of them have sequential upper-case letters, you will probably need to change the default.

### pk (primary key column)

```python
class Foo(db.Model):
    class Meta:
        pk: Union[str, None] = _ModelRegistry().default_primary_key_column = 'id'
```

Set to a string to customize the column name used for the primary key, or set to `None` to disable the column.

NOTE: Customizing the default primary key column name used for all models is different from customizing the defaults for other meta options. (You should subclass `_ModelRegistry` and set its `default_primary_key_column` attribute. This is necessary for the `foreign_key` helper function to work correctly.)

### created_at (row insertion timestamp)

```python
class Foo(db.Model):
    class Meta:
        created_at: Union[str, None] = 'created_at'  # 'created_at' is the default
```

Set to a string to customize the column name used for the creation timestamp, or set to `None` to disable the column.

### updated_at (last updated timestamp)

```python
class Foo(db.Model):
    class Meta:
        updated_at: Union[str, None] = 'updated_at'  # 'updated_at' is the default
```

Set to a string to customize the column name used for the updated timestamp, or set to `None` to disable the column.

### repr (automatic pretty `__repr__`)

```python
class Foo(db.Model):
    class Meta:
        repr: Tuple[str, ...] = (_ModelRegistry.default_primary_key_column,) # default is ('id',)

print(Foo())  # prints: Foo(id=1)
```

Set to a tuple of column (attribute) names to customize the representation of models.

### validation

```python
class Foo(db.Model):
    class Meta:
        validation: bool = True  # True is the default
```

Set to `False` to disable validation of model instances.

### polymorphic (mapped model class hierarchies)

```python
class Foo(db.Model):
    class Meta:
        polymorphic: Union[bool, str, None] = True  # None is the default


class Bar(Foo):
    pass
```

This meta option is disabled by default, and can be set to one of `'joined'`, `'single'`, or `True` (an alias for `'joined'`). See [the SQLAlchemy documentation on class inheritance hierarchies](https://docs.sqlalchemy.org/en/latest/orm/inheritance.html) for more info.

When `polymorphic` is enabled, there are two other meta options available to further customize its behavior:

```python
class Foo(db.Model):
    class Meta:
        polymorphic = True
        polymorphic_on: str = 'discriminator'  # column name to store polymorphic_identity in
        polymorphic_identity: str = 'models.Foo'  # unique identifier to use for this model


class Bar(Foo):
    class Meta:
        polymorphic_identity = 'models.Bar'
```

`polymorphic_identity` is the identifier used by SQLAlchemy to distinguish which model class a row should use, and defaults to using the model's class name. The `polymorphic_identity` gets stored in the `polymorphic_on` column, which defaults to `'discriminator'`.

**IMPORTANT:** The `polymorphic` and `polymorphic_on` Meta options should be specified on the base model of the hierarchy *only*. Conversely if you want to customize `polymorphic_identity`, it should be specified on *every* model in the hierarchy.

## Model Validation

SQLAlchemy Unchained adds support for validating models before persisting them to the database. This is enabled by default, although you can disable it with the [validation](https://sqlalchemy-unchained.readthedocs.io/en/latest/readme.html#validation) Meta option. When validation is enabled, by default all non-nullable, scalar-value columns will be validated with [Required](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#required).

There are two different ways you can write custom validation for your models.

The first is by extending [BaseValidator](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#basevalidator), implementing `__call__`, and raising [ValidationError](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#validationerror) if the validation fails:

```python
from your_package import db


class ValidateEmail(db.BaseValidator):
    def __call__(self, value):
        super().__call__(value)
        if '@' not in value:  # not how you should actually verify email addresses
            raise db.ValidationError(self.msg or 'Invalid email address')


class YourModel(db.Model):
    email = db.Column(db.String, info=dict(validators=[ValidateEmail]))
```

The second is by defining a validation `classmethod` or `staticmethod` directly on the model class:

```python
from your_package import db

class YourModel(db.Model):
    email = db.Column(db.String)

    @staticmethod
    def validate_email(value):
        if '@' not in value:  # not how you should actually verify email addresses
            raise db.ValidationError('Invalid email address')
```

Validation methods defined on model classes must follow a specific naming convention: either `validate_<column_name>` or `validates_<column_name>` will work. Just like when implementing `__call__` on [BaseValidator](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#basevalidator), model validation methods should raise [ValidationError](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#validationerror) if their validation fails.

Validation happens automatically whenever your create or update a model instance. If any of the validators fail, [ValidationErrors](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#validationerrors) will be raised.

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

For examples sake, let's say you wanted every model to have a required name column, but no automatic timestamping behavior. First we need to implement a [ColumnMetaOption](https://sqlalchemy-unchained.readthedocs.io/en/latest/api.html#columnmetaoption):

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


engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DATABASE_URI, 
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
engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DATABASE_URI)
```

## Lazy Mapping (experimental)

Lazy mapping is feature that this package introduces on top of SQLAlchemy. It's experimental and disabled by default. In stock SQLAlchemy, when you define a model, the second that code gets imported, the base model's metaclass will register the model with SQLAlchemy's mapper. 99% of the time this is what you want to happen, but if for some reason you *don't* want that behavior, then you have to enable lazy mapping. There are two components to enabling lazy mapping.

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
engine, Session, Model, relationship = init_sqlalchemy_unchained(Config.DATABASE_URI)
```

The last step is to define your models like so:

```python
class Foo(db.Model):
    class Meta:
        lazy_mapped = True
```

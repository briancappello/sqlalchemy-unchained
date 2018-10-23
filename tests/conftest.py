import os
import pytest
import sqlalchemy
import sqlalchemy.orm

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy_unchained import init_sqlalchemy_unchained, foreign_key, SessionManager


@pytest.fixture()
def db():
    os.environ['SQLA_TESTING'] = 'True'

    engine, Session, Model, relationship = init_sqlalchemy_unchained('sqlite://')

    class DB:
        def __init__(self):
            self.association_proxy = association_proxy
            self.declared_attr = declared_attr
            self.foreign_key = foreign_key
            self.hybrid_method = hybrid_method
            self.hybrid_property = hybrid_property

            self.engine = engine
            self.Session = Session
            self.Model = Model
            self.relationship = relationship

            for module in [sqlalchemy, sqlalchemy.orm]:
                for key in module.__all__:
                    if not hasattr(self, key):
                        setattr(self, key, getattr(module, key))

    yield DB()

    SessionManager.set_session_factory(None)
    del os.environ['SQLA_TESTING']

from __future__ import annotations

import typing as t
from contextlib import contextmanager

from py_meta_utils import Singleton
from sqlalchemy.orm import Session, Query

from .base_model import BaseModel


class _SessionDescriptor:
    def __get__(self, instance, cls):
        return cls._session_factory()


class _QueryDescriptor:
    def __get__(self, instance, cls):
        return cls.session.query


class SessionManagerMetaclass(Singleton):
    def __call__(cls, *args, **kwargs):
        cls = super().__call__(*args, **kwargs)
        if cls._session_factory is None:
            raise Exception(
                "SessionManager was not properly initialized. "
                "Please set the session factory via "
                "`SessionManager.set_session_factory`"
            )
        return cls


class SessionManager(metaclass=SessionManagerMetaclass):
    """
    The session manager for SQLAlchemy Unchained.
    """

    _session_factory = None
    session: Session = _SessionDescriptor()  # type: ignore[assignment]
    query: t.Callable[[t.Type[BaseModel]], Query] = _QueryDescriptor()  # type: ignore[assignment]

    @classmethod
    def set_session_factory(cls, session_factory):
        """
        Classmethod to set the session factory
        :class:`~sqlalchemy_unchained.SessionManager` should use.

        :param session_factory: The session factory callable.
        """
        cls._session_factory = session_factory

    def save(self, instance: BaseModel, commit: bool = False) -> BaseModel:
        """
        Add a model instance to the session, optionally committing the current
        transaction immediately.

        :param instance: The model instance to save.
        :param commit: Whether or not to immediately commit. **WARNING:** This
                       will commit the *entire* session, including any other model
                       instances that may have been added to the session but not
                       yet committed.
        :return: The model instance.
        """
        instance.validate(partial=False)
        self.session.add(instance)
        if commit:
            self.commit()
        return instance

    def save_all(
        self,
        instances: list[BaseModel],
        commit: bool = False,
    ) -> list[BaseModel]:
        """
        Adds a list of model instances to the session, optionally committing the
        current transaction immediately.

        :param instances: The list of model instance to save.
        :param commit: Whether or not to immediately commit. **WARNING:** This
                       will commit the *entire* session, including any other model
                       instances that may have been added to the session but not
                       yet committed.
        :return: The list of model instances.
        """
        self.session.add_all(instances)
        if commit:
            self.commit()
        return instances

    def delete(self, instance: BaseModel, commit: bool = False) -> None:
        self.session.delete(instance)
        if commit:
            self.commit()

    def delete_all(self, instances: list[BaseModel], commit: bool = False) -> None:
        for instance in instances:
            self.session.delete(instance)
        if commit:
            self.commit()

    def commit(self) -> None:
        """
        Commits the current transaction.
        """
        self.session.commit()

    @property
    @contextmanager
    def no_autoflush(self) -> t.Generator["SessionManager", None, None]:
        """
        Return a context manager that disables autoflush.

        e.g.::

            with session.no_autoflush:

                some_object = SomeClass()
                session.add(some_object)
                # won't autoflush
                some_object.related_thing = session.query(SomeRelated).first()

        Operations that proceed within the ``with:`` block will not be subject to
        flushes occurring upon query access.  This is useful when initializing a
        series of objects which involve existing database queries, where the
        uncompleted object should not yet be flushed.
        """
        autoflush = self.session.autoflush
        self.session.autoflush = False
        try:
            yield self
        finally:
            self.session.autoflush = autoflush


__all__ = [
    "SessionManager",
    "SessionManagerMetaclass",
]

from sqlalchemy.orm import Query as _Query
from typing import *


class QueryMixin:
    def get(self, id: Union[int, str, Tuple[int, ...], Tuple[str, ...]]):
        """
        Return an instance based on the given primary key identifier,
        or ``None`` if not found.

        For example::

            my_user = session.query(User).get(5)

            some_object = session.query(VersionedFoo).get((5, 10))

        :meth:`~.Query.get` is special in that it provides direct
        access to the identity map of the owning :class:`.Session`.
        If the given primary key identifier is present
        in the local identity map, the object is returned
        directly from this collection and no SQL is emitted,
        unless the object has been marked fully expired.
        If not present,
        a SELECT is performed in order to locate the object.

        :meth:`~.Query.get` also will perform a check if
        the object is present in the identity map and
        marked as expired - a SELECT
        is emitted to refresh the object as well as to
        ensure that the row is still present.
        If not, :class:`~sqlalchemy.orm.exc.ObjectDeletedError` is raised.

        :meth:`~.Query.get` is only used to return a single
        mapped instance, not multiple instances or
        individual column constructs, and strictly
        on a single primary key value.  The originating
        :class:`.Query` must be constructed in this way,
        i.e. against a single mapped entity,
        with no additional filtering criterion.  Loading
        options via :meth:`~.Query.options` may be applied
        however, and will be used if the object is not
        yet locally present.

        A lazy-loading, many-to-one attribute configured
        by :func:`.relationship`, using a simple
        foreign-key-to-primary-key criterion, will also use an
        operation equivalent to :meth:`~.Query.get` in order to retrieve
        the target value from the local identity map
        before querying the database.

        :param id: A scalar or tuple value representing
         the primary key.   For a composite primary key,
         the order of identifiers corresponds in most cases
         to that of the mapped :class:`.Table` object's
         primary key columns.  For a :func:`.mapper` that
         was given the ``primary key`` argument during
         construction, the order of identifiers corresponds
         to the elements present in this collection.

        :return: The object instance, or ``None``.
        """
        # attempt to coerce values to integers, but if that fails, it probably just
        # means the primary key column is a VARCHAR
        if isinstance(id, tuple):
            try:
                return super().get(tuple(int(x) for x in id))
            except (TypeError, ValueError):
                pass

        try:
            return super().get(int(id))
        except (TypeError, ValueError):
            return super().get(id)

    def get_by(self, **kwargs):
        """
        Returns a single model filtering by ``kwargs``, only if a single model
        was found, otherwise it returns ``None``.

        :param kwargs: column names and their values to filter by
        :return: An instance of the model
        """
        return self.filter_by(**kwargs).one_or_none()


class BaseQuery(QueryMixin, _Query):
    """
    Base class to use for the :attr:`~sqlalchemy_unchained.ModelManager.query`
    attribute on model managers.
    """

    pass


__all__ = [
    "BaseQuery",
    "QueryMixin",
]

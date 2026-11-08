"""The columns a projection may select: the whitelist, and so the privacy boundary.

A registered function `fn(subject, *args, **kwargs)` becomes a factory: calling
`columns["salary"](2, label="Monthly pay")` binds the arguments right away and
returns a one-field `Projection`. A field that is not registered cannot be
selected at all, from Python lookups or from JSON.
"""

from collections.abc import Callable, Mapping
from functools import update_wrapper
from inspect import Parameter, Signature, signature
from typing import Any, Protocol

from pyvocabulary import Vocabulary

from .exceptions import (
    ColumnAlreadyRegisteredError,
    ColumnDoesNotExistError,
    InvalidColumnArgumentsError,
    InvalidColumnError,
    InvalidColumnNameError,
)
from .projection import Projection

_SUBJECT_KINDS = (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
_LABEL = "label"


class ColumnFactory[T](Protocol):
    """Builds a one-field `Projection` from the column's arguments and an optional label."""

    def __call__(self, *args: Any, label: str | None = None, **kwargs: Any) -> Projection[T]: ...


class ProjectionRegistry[T]:
    """Named columns over subjects of type `T`, registered with `@registry.column()`.

    Example:
    ```python
    >>> columns = ProjectionRegistry[dict[str, str]]()
    >>> @columns.column()
    ... def name(user: dict[str, str], *, upper: bool = False) -> str:
    ...     return user["name"].upper() if upper else user["name"]
    >>> @columns.column(hidden=True)
    ... def password(user: dict[str, str]) -> str:
    ...     return user["password"]
    >>> list(columns.columns)
    ['name']
    >>> columns["name"](upper=True, label="Name")({"name": "Alice", "password": "x"})
    {'Name': 'ALICE'}
    >>> columns["password"]
    Traceback (most recent call last):
    ...
    pyprojection.exceptions.ColumnDoesNotExistError: Column 'password' does not exist. ...

    ```

    """

    __slots__ = ("_columns",)

    def __init__(self) -> None:
        self._columns: Vocabulary[ColumnFactory[T]] = Vocabulary(
            "column",
            does_not_exist=ColumnDoesNotExistError,
            already_registered=ColumnAlreadyRegisteredError,
            invalid_name=InvalidColumnNameError,
        )

    @property
    def columns(self) -> Mapping[str, ColumnFactory[T]]:
        """A read-only view of the visible columns, the ones a compiler may select."""
        return self._columns

    def __getitem__(self, name: str, /) -> ColumnFactory[T]:
        return self._columns[name]

    def column(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        hidden: bool = False,
    ) -> Callable[[Callable[..., Any]], ColumnFactory[T]]:
        """Return a decorator that registers a function as a column and returns its factory.

        Args:
            name: The column name. Defaults to the function's name.
            description: Documents the column in its JSON Schema. Defaults to the docstring.
            hidden: Keep the column usable from Python but out of lookups, compilers
                and schemas, e.g. for a field only internal reports may show.

        """

        def decorator(fn: Callable[..., Any]) -> ColumnFactory[T]:
            return self.register_column(fn, name=name, description=description, hidden=hidden)

        return decorator

    def register_column(
        self,
        fn: Callable[..., Any],
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        hidden: bool = False,
    ) -> ColumnFactory[T]:
        """Register `fn(subject, *args, **kwargs)` as a column and return its factory.

        Raises:
            InvalidColumnNameError: If the name is not a Python identifier (a lambda needs `name=`).
            ColumnAlreadyRegisteredError: If the name is taken, hidden or not.
            InvalidColumnError: If `fn` takes no subject, or has a `label` parameter.

        """
        column_name: str = name or getattr(fn, "__name__", "")
        factory: ColumnFactory[T] = _factory(fn, column_name, description)
        return self._columns.add(column_name, factory, hidden=hidden)


def _factory(fn: Callable[..., Any], name: str, description: str | None) -> ColumnFactory[Any]:
    parameters = list(signature(fn).parameters.values())

    if not parameters or parameters[0].kind not in _SUBJECT_KINDS:
        msg = f"Column '{name}' must take the subject as its first positional parameter."
        raise InvalidColumnError(msg)

    if any(parameter.name == _LABEL for parameter in parameters):
        msg = (
            f"Column '{name}' has a 'label' parameter, but 'label' is reserved for the output name."
        )
        raise InvalidColumnError(msg)

    arguments = Signature(parameters[1:])

    def factory(*args: Any, label: str | None = None, **kwargs: Any) -> Projection[Any]:
        try:
            bound = arguments.bind(*args, **kwargs)
        except TypeError as error:
            msg = f"Column '{name}' got invalid arguments: {error}"
            raise InvalidColumnArgumentsError(msg) from error

        def value(subject: Any) -> Any:
            return fn(subject, *bound.args, **bound.kwargs)

        return Projection(((name if label is None else label, value),))

    update_wrapper(factory, fn)
    # the JSON Schema describes the arguments JSON sends, so the subject is left out
    factory.__signature__ = arguments  # pyright: ignore[reportFunctionMemberAccess]
    factory.__doc__ = description or fn.__doc__
    return factory

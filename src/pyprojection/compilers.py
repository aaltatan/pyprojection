"""Compile a projection from JSON: a list of columns, in output order.

```json
[
  "name",
  {"name": "salary", "args": [2], "kwargs": {}, "label": "Monthly pay"},
  {"label": "Yearly pay", "formula": {"operator": "multiply", "expressions": ["salary", 12]}}
]
```

A bare string selects a column with no arguments, so `?fields=name,salary` is
`compiler.compile(fields.split(","))`. Formulas are delegated to an injected
compiler, e.g. pyformula's `FormulaCompiler`.
"""

from collections.abc import Callable, Mapping
from typing import Any, NotRequired, Protocol, TypedDict, cast

from pyvocabulary import index_path, key_path, located

from .exceptions import (
    ColumnDoesNotExistError,
    DuplicateOutputNameError,
    InvalidColumnArgumentsError,
    InvalidProjectionDefinitionError,
)
from .projection import Projection, computed
from .registry import ProjectionRegistry

_ROOT = "$"
_CALL_KEYS = {"name", "args", "kwargs", "label"}
_COMPUTED_KEYS = {"label", "formula"}


class ColumnCallDict(TypedDict):
    name: str
    args: NotRequired[list[Any]]
    kwargs: NotRequired[dict[str, Any]]
    label: NotRequired[str]


class ComputedDict(TypedDict):
    label: str
    formula: Any


type ColumnDefinition = str | ColumnCallDict | ComputedDict


class Compiler[F](Protocol):
    """Anything with a `compile(definition) -> F` method."""

    def compile(self, definition: Any, /) -> F: ...


class ProjectionCompiler[T]:
    """Compile projection definitions against a registry of columns.

    Every problem is reported here, before any subject is exported. Errors from
    the registry and the formula compiler keep their type and get a note with
    their JSON path.

    Args:
        columns: The registry; only its visible columns can be selected.
        formulas: Compiles the `formula` of computed columns. Without it, a
            definition with a computed column is rejected.

    Example:
    ```python
    >>> columns = ProjectionRegistry[dict[str, str]]()
    >>> @columns.column()
    ... def name(user: dict[str, str]) -> str:
    ...     return user["name"]
    >>> compiler = ProjectionCompiler(columns)
    >>> compiler.compile(["name", {"name": "name", "label": "Name again"}])
    Projection(name, Name again)
    >>> compiler.compile(["name", "email"])
    Traceback (most recent call last):
    ...
    pyprojection.exceptions.ColumnDoesNotExistError: Column 'email' does not exist. ...

    ```

    """

    __slots__ = ("_columns", "_formulas")

    def __init__(
        self,
        columns: ProjectionRegistry[T],
        formulas: Compiler[Callable[[T], Any]] | None = None,
        /,
    ) -> None:
        self._columns = columns
        self._formulas = formulas

    def compile(self, definition: list[ColumnDefinition] | Any, /) -> Projection[T]:
        """Compile `definition` into a `Projection`.

        Raises:
            InvalidProjectionDefinitionError: If the definition has the wrong shape.
            ColumnDoesNotExistError: If a column is not registered or is hidden.
            InvalidColumnArgumentsError: If a column's `args`/`kwargs` do not fit it.
            DuplicateOutputNameError: If two columns share an output name.

        """
        if not isinstance(definition, list):
            raise _invalid(_ROOT, f"expected a list, received {definition!r}")
        if not definition:
            raise _invalid(_ROOT, "expected at least one column")

        projection: Projection[T] = Projection(())
        for index, item in enumerate(cast("list[Any]", definition)):
            path = index_path(_ROOT, index)
            column = self._compile_column(item, path)
            with located(path, DuplicateOutputNameError):
                projection &= column

        return projection

    def _compile_column(self, item: Any, path: str) -> Projection[T]:
        match item:
            case str():
                with located(path, ColumnDoesNotExistError):
                    return self._columns[item]()
            case Mapping():
                item = cast("Mapping[str, Any]", item)
                if "name" in item and "formula" in item:
                    raise _invalid(path, "use either 'name' or 'formula', not both")
                if "formula" in item:
                    return self._compile_computed(item, path)
                if "name" in item:
                    return self._compile_call(item, path)
                raise _invalid(path, "missing 'name' or 'formula'")
            case _:
                raise _invalid(path, f"expected a column name or an object, received {item!r}")

    def _compile_call(self, item: Mapping[str, Any], path: str) -> Projection[T]:
        _check_unknown_keys(item, _CALL_KEYS, path)
        name, args, kwargs = item["name"], item.get("args", []), item.get("kwargs", {})

        if not isinstance(name, str):
            raise _invalid(key_path(path, "name"), f"expected a string, received {name!r}")
        if not isinstance(args, list):
            raise _invalid(key_path(path, "args"), f"expected a list, received {args!r}")
        if not isinstance(kwargs, Mapping):
            raise _invalid(key_path(path, "kwargs"), f"expected an object, received {kwargs!r}")
        if "label" in kwargs:
            raise _invalid(key_path(path, "kwargs"), "'label' goes beside 'name', not in 'kwargs'")
        label = _label(item, path) if "label" in item else None

        with located(path, ColumnDoesNotExistError, InvalidColumnArgumentsError):
            return self._columns[name](
                *cast("list[Any]", args), label=label, **cast("Mapping[str, Any]", kwargs)
            )

    def _compile_computed(self, item: Mapping[str, Any], path: str) -> Projection[T]:
        _check_unknown_keys(item, _COMPUTED_KEYS, path)
        if "label" not in item:
            raise _invalid(path, "missing 'label', a computed column needs an output name")
        label = _label(item, path)

        if self._formulas is None:
            raise _invalid(path, "computed columns are not allowed: no formula compiler was given")

        with located(key_path(path, "formula"), Exception):
            formula = self._formulas.compile(item["formula"])

        return computed(label, formula)


# -----------------------
# helpers
# -----------------------


def _label(item: Mapping[str, Any], path: str) -> str:
    label = item["label"]
    if not isinstance(label, str) or not label:
        raise _invalid(key_path(path, "label"), f"expected a non-empty string, received {label!r}")
    return label


def _check_unknown_keys(item: Mapping[str, Any], allowed: set[str], path: str) -> None:
    if unknown := sorted(set(item) - allowed):
        problem = (
            f"unknown {', '.join(map(repr, unknown))}. Allowed keys: {', '.join(sorted(allowed))}"
        )
        raise _invalid(path, problem)


def _invalid(path: str, problem: str) -> InvalidProjectionDefinitionError:
    return InvalidProjectionDefinitionError(f"Invalid projection at {path}: {problem}")

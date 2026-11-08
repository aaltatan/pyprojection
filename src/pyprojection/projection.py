"""Output shapes as values: which fields, under which names, computed how.

```python
export = (
    columns["name"]()
    & columns["salary"](label="Monthly pay")
    & computed("Yearly pay", salary * 12)
)
export(employee)  # {"name": ..., "Monthly pay": ..., "Yearly pay": ...}
```

A projection is an ordered tuple of `(output name, callable)` pairs. `&` joins
two of them; a repeated output name is rejected when the projection is built,
not when the first row is exported.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .exceptions import DuplicateOutputNameError, InvalidColumnError, InvalidOutputNameError

type Field[T] = tuple[str, Callable[[T], Any]]


@dataclass(frozen=True, slots=True)
class Projection[T]:
    """Fields in output order. Calling it maps one subject to one dict.

    Build projections with a `ProjectionRegistry` and `computed`, then join them with `&`.

    Example:
    ```python
    >>> person = computed("name", lambda p: p["name"]) & computed("age", lambda p: p["age"])
    >>> person
    Projection(name, age)
    >>> person({"name": "Alice", "age": 30, "password": "hunter2"})
    {'name': 'Alice', 'age': 30}
    >>> person.names
    ('name', 'age')
    >>> person & computed("age", lambda p: p["age"] + 1)
    Traceback (most recent call last):
    ...
    pyprojection.exceptions.DuplicateOutputNameError: Output name 'age' is used more than once. ...

    ```

    """

    fields: tuple[Field[T], ...]

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for name, value in self.fields:
            _check_output_name(name)
            if not callable(value):
                msg = f"Column '{name}' must be callable, received {value!r}"
                raise InvalidColumnError(msg)
            if name in seen:
                msg = (
                    f"Output name '{name}' is used more than once. "
                    "Give one of them another name with label=..."
                )
                raise DuplicateOutputNameError(msg)
            seen.add(name)

    @property
    def names(self) -> tuple[str, ...]:
        """The output names in order, e.g. a CSV header."""
        return tuple(name for name, _ in self.fields)

    def __call__(self, subject: T, /) -> dict[str, Any]:
        return {name: value(subject) for name, value in self.fields}

    def __and__(self, other: "Projection[T]", /) -> "Projection[T]":
        match other:
            case Projection(fields=fields):
                return Projection((*self.fields, *fields))
            case _:
                return NotImplemented

    def __repr__(self) -> str:
        return f"Projection({', '.join(self.names)})"


def computed[T](name: str, value: Callable[[T], Any], /) -> Projection[T]:
    """Return a one-field projection that outputs `value(subject)` under `name`.

    Args:
        name: The output name, any non-empty string (`"Yearly pay"` is fine).
        value: Any `T -> R` callable, typically a pyformula `Formula`.

    Example:
    ```python
    >>> computed("Initial", lambda name: name[0])("Alice")
    {'Initial': 'A'}

    ```

    """
    return Projection(((name, value),))


def _check_output_name(name: object) -> None:
    if not isinstance(name, str) or not name:
        msg = f"Invalid output name: {name!r}, expected a non-empty string"
        raise InvalidOutputNameError(msg)

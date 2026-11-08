"""Exceptions raised by pyprojection.

Errors raised by an injected formula compiler keep their own type (e.g.
pyformula's `FormulaNotFoundError`); pyprojection only adds a note with their
JSON path, e.g. `at $[3].formula`.
"""

from collections.abc import Iterable

from pyvocabulary import InvalidNameError


class PyprojectionError(Exception):
    """Base class for every exception raised by pyprojection."""


class ColumnDoesNotExistError(PyprojectionError, LookupError):
    """Raised when a column is not registered, or is hidden.

    Example:
    ```python
    >>> str(ColumnDoesNotExistError("salary", ["name", "department"]))
    "Column 'salary' does not exist. Available columns: name, department"

    ```

    """

    def __init__(self, name: str, available: Iterable[str], /) -> None:
        names = ", ".join(available) or "(none)"
        super().__init__(f"Column '{name}' does not exist. Available columns: {names}")


class ColumnAlreadyRegisteredError(PyprojectionError):
    """Raised when a column name is registered twice in the same registry."""

    def __init__(self, name: str, /) -> None:
        super().__init__(f"Column '{name}' is already registered.")


class InvalidColumnNameError(PyprojectionError, InvalidNameError):
    """Raised when a column name is not a valid ASCII Python identifier."""

    def __init__(self, name: object, /) -> None:
        super().__init__(name, kind="column")


class InvalidColumnError(PyprojectionError, TypeError):
    """Raised when a function cannot be used as a column (checked when registered)."""


class InvalidColumnArgumentsError(PyprojectionError, TypeError):
    """Raised when a column factory is called with arguments its function does not take."""


class InvalidOutputNameError(PyprojectionError, ValueError):
    """Raised when an output name (a label) is not a non-empty string."""


class DuplicateOutputNameError(PyprojectionError, ValueError):
    """Raised when two fields of one projection share an output name."""


class InvalidProjectionDefinitionError(PyprojectionError, ValueError):
    """Raised when a JSON projection definition does not have the expected shape."""

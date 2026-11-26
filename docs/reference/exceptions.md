# Exceptions

```text
Exception
└── PyprojectionError
    ├── ColumnDoesNotExistError           (also a LookupError)
    ├── ColumnAlreadyRegisteredError
    ├── InvalidColumnNameError            (also a ValueError, via pyvocabulary's InvalidNameError)
    ├── InvalidColumnError                (also a TypeError)
    ├── InvalidColumnArgumentsError       (also a TypeError)
    ├── InvalidOutputNameError            (also a ValueError)
    ├── DuplicateOutputNameError          (also a ValueError)
    └── InvalidProjectionDefinitionError  (also a ValueError)
```

Every exception raised by pyprojection derives from `PyprojectionError`, and most also from
the matching built-in, so `except LookupError` / `ValueError` / `TypeError` work too:

```python
from pyprojection import (
    ColumnAlreadyRegisteredError,
    ColumnDoesNotExistError,
    DuplicateOutputNameError,
    InvalidColumnArgumentsError,
    InvalidColumnError,
    InvalidColumnNameError,
    InvalidOutputNameError,
    InvalidProjectionDefinitionError,
    PyprojectionError,
)

[issubclass(error, PyprojectionError) for error in (
    ColumnAlreadyRegisteredError,
    ColumnDoesNotExistError,
    DuplicateOutputNameError,
    InvalidColumnArgumentsError,
    InvalidColumnError,
    InvalidColumnNameError,
    InvalidOutputNameError,
    InvalidProjectionDefinitionError,
)]
# [True, True, True, True, True, True, True, True]

issubclass(ColumnDoesNotExistError, LookupError), issubclass(InvalidColumnNameError, ValueError)
# (True, True)
```

| Exception | Also a | Raised when |
| --- | --- | --- |
| `ColumnDoesNotExistError` | `LookupError` | a column is not registered or is hidden |
| `ColumnAlreadyRegisteredError` | | a column name is registered twice (hidden or not) |
| `InvalidColumnNameError` | `ValueError` | a column name is not an ASCII Python identifier (a lambda needs `name=`) |
| `InvalidColumnError` | `TypeError` | a function takes no subject or has a `label` parameter; a field value is not callable |
| `InvalidColumnArgumentsError` | `TypeError` | a factory gets arguments its function does not take |
| `InvalidOutputNameError` | `ValueError` | an output name is not a non-empty string |
| `DuplicateOutputNameError` | `ValueError` | two fields of one projection share an output name |
| `InvalidProjectionDefinitionError` | `ValueError` | a JSON definition has the wrong shape |

## Messages say what is valid

```python
ColumnDoesNotExistError("salary", ["name", "department"])
# ColumnDoesNotExistError("Column 'salary' does not exist. Available columns: name, department")
```

## JSON paths are notes

When `ProjectionCompiler.compile` fails, the error keeps its type and message and gets a
note with its JSON path. Errors raised by an injected formula compiler (for example
pyformula's `FormulaNotFoundError`) keep their own type too; pyprojection only adds the note,
e.g. `at $[3].formula`. `InvalidProjectionDefinitionError` carries the path in its message
instead. See [Definition format](definitions.md#checks).

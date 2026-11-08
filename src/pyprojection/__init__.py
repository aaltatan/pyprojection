"""pyprojection: output shapes as values.

`columns["name"]() & computed("Yearly pay", salary * 12)` is a `Projection`:
it maps one subject to one dict. Columns come from a registry, the whitelist,
so a field that is not registered can never be selected, from Python or JSON.
"""

from .compilers import (
    ColumnCallDict,
    ColumnDefinition,
    Compiler,
    ComputedDict,
    ProjectionCompiler,
)
from .exceptions import (
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
from .json_schema import FORMULA_SCHEMA_ID, get_projection_json_schema
from .projection import Field, Projection, computed
from .registry import ColumnFactory, ProjectionRegistry

__all__ = [
    "FORMULA_SCHEMA_ID",
    "ColumnAlreadyRegisteredError",
    "ColumnCallDict",
    "ColumnDefinition",
    "ColumnDoesNotExistError",
    "ColumnFactory",
    "Compiler",
    "ComputedDict",
    "DuplicateOutputNameError",
    "Field",
    "InvalidColumnArgumentsError",
    "InvalidColumnError",
    "InvalidColumnNameError",
    "InvalidOutputNameError",
    "InvalidProjectionDefinitionError",
    "Projection",
    "ProjectionCompiler",
    "ProjectionRegistry",
    "PyprojectionError",
    "computed",
    "get_projection_json_schema",
]

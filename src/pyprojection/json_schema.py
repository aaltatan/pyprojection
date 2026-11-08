"""The JSON Schema of a projection definition, as accepted by `ProjectionCompiler.compile`.

Generated from the registry, so a column picker can list exactly the selectable
columns (`$defs.column_name.enum`) and an editor can check arguments as typed.
"""

from collections.abc import Mapping
from typing import Any

from pyvocabulary import JSON_SCHEMA_DIALECT, call_json_schema

from .registry import ProjectionRegistry

FORMULA_SCHEMA_ID = "urn:pyprojection:formula"

_LABEL_SCHEMA = {"type": "string", "minLength": 1}


def get_projection_json_schema(
    columns: ProjectionRegistry[Any],
    formula_schema: Mapping[str, Any] | None = None,
    /,
) -> dict[str, Any]:
    """Return the JSON Schema of a list of column names, column calls and computed columns.

    Args:
        columns: The registry; hidden columns are left out.
        formula_schema: The schema of one `formula`. Without it, computed columns
            are not allowed, matching a `ProjectionCompiler` without a formula compiler.

    Example:
    ```python
    >>> columns = ProjectionRegistry[dict[str, int]]()
    >>> @columns.column()
    ... def age(user: dict[str, int], *, in_months: bool = False) -> int:
    ...     '''Age in years.'''
    ...     return user["age"] * 12 if in_months else user["age"]
    >>> schema = get_projection_json_schema(columns)
    >>> schema["$defs"]["column_name"]
    {'type': 'string', 'enum': ['age']}
    >>> call = schema["$defs"]["call"]["anyOf"][0]
    >>> call["properties"]["kwargs"]["properties"], call["description"]
    ({'in_months': {'type': 'boolean', 'default': False}}, 'Age in years.')

    ```

    """
    calls = [
        call_json_schema(name, factory, extra_properties={"label": _LABEL_SCHEMA})
        for name, factory in columns.columns.items()
    ]
    items: list[dict[str, Any]] = [{"$ref": "#/$defs/column_name"}, {"$ref": "#/$defs/call"}]
    defs: dict[str, Any] = {
        "column_name": {"type": "string", "enum": list(columns.columns)},
        # `anyOf` must not be empty; with no columns, no call is valid
        "call": {"anyOf": calls} if calls else False,
    }

    if formula_schema is not None:
        items.append({"$ref": "#/$defs/computed"})
        defs["computed"] = {
            "type": "object",
            "properties": {"label": _LABEL_SCHEMA, "formula": {"$ref": FORMULA_SCHEMA_ID}},
            "required": ["label", "formula"],
            "additionalProperties": False,
        }
        # its own `$id`, so `#/$defs/...` refs inside it keep pointing into itself
        defs["formula"] = {**formula_schema, "$id": FORMULA_SCHEMA_ID}

    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "type": "array",
        "minItems": 1,
        "items": {"anyOf": items},
        "$defs": defs,
    }

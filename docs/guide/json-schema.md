# JSON Schema

`get_projection_json_schema(columns, formula_schema=None)` returns the JSON Schema of the
definitions [`ProjectionCompiler.compile`](compiling.md) accepts. It is generated from the
registry, so a column picker can list exactly the selectable columns and an editor can check
arguments as they are typed. This page continues the `Employee` example from
[Columns and registries](columns.md).

```python
from pyprojection import get_projection_json_schema

schema = get_projection_json_schema(columns)

schema["type"], schema["minItems"]
# ('array', 1)

schema["$defs"]["column_name"]["enum"]  # what a column picker lists
# ['name', 'monthly_salary', 'department', 'initial']
```

Hidden columns are left out, just as the compiler refuses them.

## Columns and their arguments

`$defs.call` has one entry per visible column, in registration order. Each describes the
column's arguments (from its signature, without the subject), its `label`, and its
description (from `description=` or the docstring).

```python
department = schema["$defs"]["call"]["anyOf"][2]

department["description"]
# 'Department, optionally upper-cased.'

department["properties"]["kwargs"]["properties"]
# {'upper': {'type': 'boolean', 'default': False}}

department["properties"]["label"]
# {'type': 'string', 'minLength': 1}
```

## Allowing computed columns

Without `formula_schema`, computed columns are not in the schema, matching a compiler
without a formula compiler. Pass the schema of one formula to allow them. With pyformula,
that is `get_formula_json_schema({"salary": salary})`; any schema works:

```python
from pyprojection import FORMULA_SCHEMA_ID

formula_schema = {"type": ["string", "number", "object"]}

with_formulas = get_projection_json_schema(columns, formula_schema)

with_formulas["$defs"]["computed"]["required"]
# ['label', 'formula']

with_formulas["$defs"]["formula"]["$id"] == FORMULA_SCHEMA_ID
# True
```

The formula schema is embedded under its own `$id` (`urn:pyprojection:formula`), so the
`$ref`s inside it keep pointing into itself.

## Validating a definition

Any JSON Schema validator works; the schema uses draft 2020-12. With
[jsonschema](https://pypi.org/project/jsonschema/):

```python
from jsonschema import Draft202012Validator

validator = Draft202012Validator(schema)

validator.is_valid(["name", {"name": "department", "kwargs": {"upper": True}}])
# True

validator.is_valid(["name", "national_id"])
# False
```

The compiler checks the same rules (and reports a JSON path), so validating first is only
useful on the client, for example to grey out a Save button.

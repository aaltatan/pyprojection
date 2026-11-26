# Definition format

`ProjectionCompiler.compile` takes a JSON **list** of at least one item, in output order.

```json
[
  "name",
  {"name": "monthly_salary", "args": [0], "kwargs": {}, "label": "Monthly pay"},
  {"label": "Yearly pay", "formula": {"operator": "multiply", "expressions": ["salary", 12]}}
]
```

## Items

### Column name

```json
"name"
```

A visible column, called with no arguments, output under its own name.

### Column call

```json
{"name": "department", "args": [], "kwargs": {"upper": true}, "label": "Dept"}
```

| Key | Required | Type | Meaning |
| --- | --- | --- | --- |
| `name` | yes | string | a visible column |
| `args` | no | list | positional arguments, after the subject |
| `kwargs` | no | object | keyword arguments; may not contain `label` |
| `label` | no | non-empty string | the output name; defaults to the column name |

### Computed column

```json
{"label": "Yearly pay", "formula": {"operator": "multiply", "expressions": ["salary", 12]}}
```

| Key | Required | Type | Meaning |
| --- | --- | --- | --- |
| `label` | yes | non-empty string | the output name |
| `formula` | yes | anything | passed to the formula compiler given to `ProjectionCompiler` |

Allowed only when the compiler was given a formula compiler. With pyformula, `formula` is a
[pyformula expression](https://aaltatan.github.io/pyformula/reference/expressions/).

## Checks

Every check runs in `compile`, before any subject is exported. `$[i]` is the item's index.

| Problem | Error | Path |
| --- | --- | --- |
| the definition is not a list | `InvalidProjectionDefinitionError` | `$` |
| the list is empty | `InvalidProjectionDefinitionError` | `$` |
| an item is neither a string nor an object | `InvalidProjectionDefinitionError` | `$[i]` |
| an object has neither `name` nor `formula`, or both | `InvalidProjectionDefinitionError` | `$[i]` |
| an object has an unknown key | `InvalidProjectionDefinitionError` | `$[i]` |
| `name` is not a string, `args` not a list, `kwargs` not an object | `InvalidProjectionDefinitionError` | `$[i].name`, `.args`, `.kwargs` |
| `label` is inside `kwargs` | `InvalidProjectionDefinitionError` | `$[i].kwargs` |
| `label` is not a non-empty string | `InvalidProjectionDefinitionError` | `$[i].label` |
| a computed column has no `label` | `InvalidProjectionDefinitionError` | `$[i]` |
| a computed column, but no formula compiler | `InvalidProjectionDefinitionError` | `$[i]` |
| the column is not registered, or is hidden | `ColumnDoesNotExistError` | note `at $[i]` |
| `args` / `kwargs` do not fit the column | `InvalidColumnArgumentsError` | note `at $[i]` |
| two items share an output name | `DuplicateOutputNameError` | note `at $[i]` |
| the formula compiler raises | its own error type | note `at $[i].formula...` |

`InvalidProjectionDefinitionError` has the path in its message:
`Invalid projection at $[0]: unknown 'kwarg'. Allowed keys: args, kwargs, label, name`. The
other errors keep their message and get the path as an exception note
(`error.__notes__`).

## JSON Schema

[`get_projection_json_schema`](api.md#get_projection_json_schema) describes this format for a
given registry. See [JSON Schema](../guide/json-schema.md).

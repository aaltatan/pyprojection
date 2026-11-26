# Compiling projections from JSON

`ProjectionCompiler` builds a `Projection` from a JSON definition: a list of columns, in
output order. This is how a user-built layout (an export dialog, a saved report, a `?fields=`
parameter) becomes a projection. This page continues the `Employee` example from
[Columns and registries](columns.md).

## The definition

Each item in the list is one of:

| Item | Meaning |
| --- | --- |
| `"name"` | a column with no arguments |
| `{"name": ..., "args": [...], "kwargs": {...}, "label": ...}` | a column call; all keys but `name` are optional |
| `{"label": ..., "formula": ...}` | a computed column; `formula` goes to the formula compiler you inject |

The full shape is in the [Definition format](../reference/definitions.md) reference.

```python
from pyprojection import ProjectionCompiler

compiler = ProjectionCompiler(columns)

compiler.compile(
    [
        "name",
        {"name": "department", "kwargs": {"upper": True}, "label": "Dept"},
        {"name": "monthly_salary", "args": [0], "label": "Monthly pay"},
    ]
)(alice)
# {'name': 'Alice', 'Dept': 'SALES', 'Monthly pay': Decimal('3000')}
```

Only the registry's **visible** columns can be selected. Hidden and unregistered ones are
refused, which is the point:

```python
compiler.compile(["name", "national_id"])
# ColumnDoesNotExistError: Column 'national_id' does not exist. Available columns: name, monthly_salary, department, initial
```

## Computed columns from JSON

Pass a formula compiler as the second argument to allow `{"label", "formula"}` items. Any
object with a `compile(definition)` method that returns a callable fits; pyformula's
`FormulaCompiler` is the usual choice.

```python
from pyformula import FormulaCompiler, decimal_literal

compiler = ProjectionCompiler(
    columns,
    FormulaCompiler[Employee]({"salary": salary}, literal=decimal_literal),
)

report = compiler.compile(
    [
        "name",
        {"name": "monthly_salary", "label": "Monthly pay"},
        {"label": "Yearly pay", "formula": {"operator": "multiply", "expressions": ["salary", 12]}},
    ]
)

report
# Projection(name, Monthly pay, Yearly pay)

report(alice)
# {'name': 'Alice', 'Monthly pay': Decimal('3000.00'), 'Yearly pay': Decimal('36000.00')}
```

`literal=decimal_literal` keeps JSON numbers exact in money formulas.

Without a formula compiler, a computed column is rejected:

```python
ProjectionCompiler(columns).compile([{"label": "Yearly pay", "formula": "salary"}])
# InvalidProjectionDefinitionError: Invalid projection at $[0]: computed columns are not allowed: no formula compiler was given
```

## `?fields=` in one line

A bare string is a column, so a comma-separated query parameter compiles as it is:

```python
fields = "name,department"  # request.query_params["fields"]

compiler.compile(fields.split(","))(bob)
# {'name': 'Bob', 'department': 'IT'}
```

## Errors point at the JSON

Every problem is found by `compile`, before any row is exported. Errors keep their type and
get a note with their JSON path, so an API can answer `400` with exactly what is wrong.

```python
try:
    compiler.compile(["name", {"name": "monthly_salary", "args": ["two"], "kwargs": {"x": 1}}])
except TypeError as error:
    print(error, error.__notes__)
# Column 'monthly_salary' got invalid arguments: got an unexpected keyword argument 'x' ['at $[1]']
```

Errors raised by the formula compiler keep **their own** type, for example pyformula's
`FormulaNotFoundError`, with the path into the formula:

```python
from pyformula import FormulaNotFoundError

try:
    compiler.compile(
        ["name", {"label": "x", "formula": {"operator": "add", "expressions": ["salry", 1]}}]
    )
except FormulaNotFoundError as error:
    print(error.__notes__)
# ['at $[1].formula.expressions[0]']
```

Shape problems raise `InvalidProjectionDefinitionError` with the path in the message:

```python
compiler.compile([{"name": "name", "kwarg": {}}])
# InvalidProjectionDefinitionError: Invalid projection at $[0]: unknown 'kwarg'. Allowed keys: args, kwargs, label, name

compiler.compile([])
# InvalidProjectionDefinitionError: Invalid projection at $: expected at least one column

compiler.compile(["name", {"name": "name"}])
# DuplicateOutputNameError: Output name 'name' is used more than once. Give one of them another name with label=...

compiler.compile([{"name": "name", "kwargs": {"label": "Name"}}])
# InvalidProjectionDefinitionError: Invalid projection at $[0].kwargs: 'label' goes beside 'name', not in 'kwargs'
```

The full list of shape checks is in the [Definition format](../reference/definitions.md)
reference.

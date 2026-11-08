# pyprojection

Output shapes as values: which fields, under which names, computed how. Composable with `&`
and definable as JSON.

```python
export = (
    columns["name"]()
    & columns["monthly_salary"](label="Monthly pay")
    & computed("Yearly pay", salary * 12)
)

export(employee)
# {'name': 'Alice', 'Monthly pay': Decimal('3000.00'), 'Yearly pay': Decimal('36000.00')}
```

A `Projection` maps one subject to one dict. Columns come from a registry, which is the
**privacy boundary**: a field that is not registered (or is registered as hidden) can never be
selected, not from Python lookups and not from a JSON definition a user sent.

| Piece | What it does |
| --- | --- |
| [`ProjectionRegistry`](#registering-columns) | The whitelist: `@columns.column()` turns `fn(subject, ...)` into a column factory |
| [`Projection`](#composing-with-) | Ordered `(output name, callable)` pairs; callable, joined with `&` |
| [`computed`](#computed-columns) | A derived column from any `T -> R` callable, e.g. a pyformula `Formula` |
| [`ProjectionCompiler`](#from-json) | Builds a `Projection` from JSON (or `?fields=`), errors carry a JSON path |
| [`get_projection_json_schema`](#json-schema) | The JSON Schema of that JSON, generated from the registry |

**When not to use it.** If the output shape is fixed, write a dict comprehension. pyprojection
earns its place when a screen lets *users* choose their columns: an export dialog, a report
builder, a `?fields=` API parameter.

## Installation

```bash
uv add pyprojection
```

Python 3.12+. The only runtime dependency is
[pyvocabulary](https://github.com/aaltatan/pyvocabulary). [pyformula](https://github.com/aaltatan/pyformula)
is optional: `computed` takes any callable.

## Quick start

The examples in this README build on each other and are run by the test suite. A comment
directly under a line shows what it outputs or raises.

```python
from dataclasses import dataclass
from decimal import Decimal
from pyformula import variable
from pyprojection import ProjectionRegistry, computed


@dataclass(frozen=True)
class Employee:
    name: str
    department: str
    salary: Decimal
    national_id: str


alice = Employee("Alice", "Sales", Decimal("3000.00"), "123-45")

bob = Employee("Bob", "IT", Decimal("4500.50"), "678-90")

columns = ProjectionRegistry[Employee]()


@columns.column()
def name(employee: Employee) -> str:
    """Full name."""
    return employee.name


@columns.column()
def monthly_salary(employee: Employee, places: int = 2) -> Decimal:
    """Monthly salary, rounded to `places` decimals."""
    return round(employee.salary, places)


@variable()
def salary(employee: Employee) -> Decimal:
    return employee.salary


export = (
    columns["name"]()
    & columns["monthly_salary"](label="Monthly pay")
    & computed("Yearly pay", salary * 12)
)

export
# Projection(name, Monthly pay, Yearly pay)

export(alice)
# {'name': 'Alice', 'Monthly pay': Decimal('3000.00'), 'Yearly pay': Decimal('36000.00')}

[export(e)["name"] for e in (alice, bob)]
# ['Alice', 'Bob']
```

## Registering columns

A column is a function whose first parameter is the subject. Any further parameters become
arguments of its factory, bound **when the projection is built**, so a wrong argument fails
before the first row is exported.

```python
@columns.column(name="department", description="Department, optionally upper-cased.")
def dept(employee: Employee, *, upper: bool = False) -> str:
    return employee.department.upper() if upper else employee.department


columns["department"](upper=True)(alice)
# {'department': 'SALES'}

columns["monthly_salary"](0)(bob)
# {'monthly_salary': Decimal('4500')}

columns["department"](lower=True)
# InvalidColumnArgumentsError: Column 'department' got invalid arguments: got an unexpected keyword argument 'lower'
```

`label=` sets the output name. It is reserved on every factory, so a column function may not
have a `label` parameter of its own (that is rejected at registration).

```python
columns["name"](label="Full name")(alice)
# {'Full name': 'Alice'}
```

The decorator returns the factory, so it can also be used directly:

```python
name()(bob)
# {'name': 'Bob'}
```

Register a lambda or an existing function without the decorator with `register_column`:

```python
columns.register_column(lambda e: e.name[0], name="initial")

columns["initial"]()(alice)
# {'initial': 'A'}
```

### Hidden columns

`hidden=True` keeps a column usable from Python (through the factory the decorator returns)
but out of lookups, compilers and schemas. Use it for fields only internal code may export.

```python
@columns.column(hidden=True)
def national_id(employee: Employee) -> str:
    return employee.national_id


national_id()(alice)
# {'national_id': '123-45'}

list(columns.columns)
# ['name', 'monthly_salary', 'department', 'initial']

columns["national_id"]
# ColumnDoesNotExistError: Column 'national_id' does not exist. Available columns: name, monthly_salary, department, initial
```

## Composing with `&`

`&` returns a new projection with the fields of both, in order. Projections are frozen, so a
base projection can be shared and extended safely.

```python
base = columns["name"]() & columns["department"]()

payroll = base & columns["monthly_salary"](label="Pay")

base.names, payroll.names
# (('name', 'department'), ('name', 'department', 'Pay'))
```

`names` is the output header, e.g. for CSV. Two fields with the same output name are rejected
when built; give one a `label`:

```python
base & columns["name"]()
# DuplicateOutputNameError: Output name 'name' is used more than once. Give one of them another name with label=...

(base & columns["name"](label="Name again")).names
# ('name', 'department', 'Name again')
```

## Computed columns

`computed(name, fn)` adds a derived column. The output name can be any non-empty string, and
`fn` any callable: a pyformula `Formula`, a lambda, a method.

```python
bonus = computed("Bonus", (salary * Decimal("0.10")))

(base & bonus)(bob)
# {'name': 'Bob', 'department': 'IT', 'Bonus': Decimal('450.0500')}

computed("Shouting", lambda e: e.name.upper())(alice)
# {'Shouting': 'ALICE'}
```

## From JSON

`ProjectionCompiler` builds a projection from a list of columns. Each item is one of:

| Item | Meaning |
| --- | --- |
| `"name"` | A column with no arguments |
| `{"name": ..., "args": [...], "kwargs": {...}, "label": ...}` | A column call; all keys but `name` are optional |
| `{"label": ..., "formula": ...}` | A computed column; `formula` goes to the formula compiler you inject |

```python
from pyformula import FormulaCompiler, FormulaNotFoundError, decimal_literal
from pyprojection import ProjectionCompiler

compiler = ProjectionCompiler(
    columns,
    FormulaCompiler[Employee]({"salary": salary}, literal=decimal_literal),
)

report = compiler.compile(
    [
        "name",
        {"name": "department", "kwargs": {"upper": True}, "label": "Dept"},
        {"name": "monthly_salary", "args": [0], "label": "Monthly pay"},
        {"label": "Yearly pay", "formula": {"operator": "multiply", "expressions": ["salary", 12]}},
    ]
)

report
# Projection(name, Dept, Monthly pay, Yearly pay)

report(alice)
# {'name': 'Alice', 'Dept': 'SALES', 'Monthly pay': Decimal('3000'), 'Yearly pay': Decimal('36000.00')}
```

`literal=decimal_literal` keeps JSON numbers exact in money formulas. Leave the formula compiler
out to allow registered columns only: a definition with a computed column is then rejected.

### Errors point at the JSON

Every problem is found by `compile`, before any row is exported. Errors keep their type and get
a note with their JSON path, so an API can answer `400` with exactly what is wrong.

```python
try:
    compiler.compile(["name", "national_id"])
except LookupError as error:
    print(error, error.__notes__)
# Column 'national_id' does not exist. Available columns: name, monthly_salary, department, initial ['at $[1]']

try:
    compiler.compile(
        ["name", {"label": "x", "formula": {"operator": "add", "expressions": ["salry", 1]}}]
    )
except FormulaNotFoundError as error:  # pyformula's own error type is kept
    print(error.__notes__)
# ['at $[1].formula.expressions[0]']

compiler.compile([{"name": "name", "kwarg": {}}])
# InvalidProjectionDefinitionError: Invalid projection at $[0]: unknown 'kwarg'. Allowed keys: args, kwargs, label, name
```

## Recipes

### `?fields=` in an API

A bare string is a column, so a comma-separated query parameter compiles as it is. Hidden and
unregistered fields are refused, which is the point.

```python
fields = "name,department"  # request.query_params["fields"]

compiler.compile(fields.split(","))(bob)
# {'name': 'Bob', 'department': 'IT'}
```

### CSV export

```python
import csv, io

out = io.StringIO()

writer = csv.DictWriter(out, fieldnames=report.names, lineterminator="\n")

writer.writeheader()

writer.writerows(report(e) for e in (alice, bob))

print(out.getvalue())
# name,Dept,Monthly pay,Yearly pay
# Alice,SALES,3000,36000.00
# Bob,IT,4500,54006.00
```

### Saved report layouts

Store the JSON the user built (in a database row, a settings file) and compile it when the
report runs. A layout that refers to a column you have since removed fails with its path, not
with a half-written file.

## JSON Schema

`get_projection_json_schema(columns, formula_schema=None)` describes what `compile` accepts. It
is generated from the registry: column names, each column's arguments (from its signature) and
its description (from its docstring or `description=`). Hidden columns are left out.

```python
from pyprojection import get_projection_json_schema

schema = get_projection_json_schema(columns)

schema["$defs"]["column_name"]["enum"]  # what a column picker lists
# ['name', 'monthly_salary', 'department', 'initial']

department = schema["$defs"]["call"]["anyOf"][2]

department["description"]
# 'Department, optionally upper-cased.'

department["properties"]["kwargs"]["properties"]
# {'upper': {'type': 'boolean', 'default': False}}
```

Pass `formula_schema` to allow computed columns; it is embedded under its own `$id`
(`urn:pyprojection:formula`) so `$ref`s inside it keep working.

## Errors

All errors derive from `PyprojectionError` and also from the matching built-in, so
`except LookupError` / `ValueError` / `TypeError` work too.

| Exception | Also a | Raised when |
| --- | --- | --- |
| `ColumnDoesNotExistError` | `LookupError` | A column is not registered or is hidden |
| `ColumnAlreadyRegisteredError` | | A column name is registered twice |
| `InvalidColumnNameError` | `ValueError` | A column name is not a Python identifier (a lambda needs `name=`) |
| `InvalidColumnError` | `TypeError` | A function takes no subject or has a `label` parameter; a computed value is not callable |
| `InvalidColumnArgumentsError` | `TypeError` | A factory gets arguments its function does not take |
| `InvalidOutputNameError` | `ValueError` | An output name is not a non-empty string |
| `DuplicateOutputNameError` | `ValueError` | Two fields of one projection share an output name |
| `InvalidProjectionDefinitionError` | `ValueError` | A JSON definition has the wrong shape |

## The family

pyprojection is one of a set of packages that wrap a `Callable[[T], R]` in an immutable value
with an algebra: [pyspecification](https://github.com/aaltatan/pyspecification) (`T -> bool`,
`& | ~`), [pyformula](https://github.com/aaltatan/pyformula) (`T -> number`, arithmetic),
[pyflowstep](https://github.com/aaltatan/pyflowstep) (`T -> T`, `>>`),
[pyruleset](https://github.com/aaltatan/pyruleset) (`T -> V`, first match wins) and
pyprojection (`T -> dict`, `&`). They share [pyvocabulary](https://github.com/aaltatan/pyvocabulary)
for registries, JSON Schemas and JSON-path errors.

## License

GPL-3.0-only.

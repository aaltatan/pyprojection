# pyprojection

**Output shapes as values: which fields, under which names, computed how.**

A `Projection` maps one object to one dict. You build it from registered columns and
computed values, join pieces with `&`, and can define the whole thing as JSON that a user
sent you.

```py
export = (
    columns["name"]()
    & columns["monthly_salary"](label="Monthly pay")
    & computed("Yearly pay", salary * 12)
)
```

Columns come from a registry, which is the **privacy boundary**: a field that is not
registered (or is registered as hidden) can never be selected, not from Python lookups and
not from a JSON definition a user sent.

## A first taste

An HR screen exports employees. Users choose the columns; the national ID must never leave
the server.

```python
from dataclasses import dataclass
from decimal import Decimal

from pyprojection import ProjectionRegistry, computed


@dataclass(frozen=True)
class Employee:
    name: str
    department: str
    salary: Decimal
    national_id: str


alice = Employee("Alice", "Sales", Decimal("3000.00"), "123-45")

columns = ProjectionRegistry[Employee]()


@columns.column()
def name(employee: Employee) -> str:
    """Full name."""
    return employee.name


@columns.column()
def monthly_salary(employee: Employee, places: int = 2) -> Decimal:
    """Monthly salary, rounded to `places` decimals."""
    return round(employee.salary, places)


@columns.column(hidden=True)
def national_id(employee: Employee) -> str:
    return employee.national_id


export = (
    columns["name"]()
    & columns["monthly_salary"](0, label="Monthly pay")
    & computed("Yearly pay", lambda e: e.salary * 12)
)

export
# Projection(name, Monthly pay, Yearly pay)

export(alice)
# {'name': 'Alice', 'Monthly pay': Decimal('3000'), 'Yearly pay': Decimal('36000.00')}

export.names
# ('name', 'Monthly pay', 'Yearly pay')
```

A comment directly under a line shows what that line outputs or raises.

### Let users pick the columns as JSON

```python
from pyprojection import ProjectionCompiler

compiler = ProjectionCompiler(columns)

compiler.compile(["name", {"name": "monthly_salary", "label": "Pay"}])(alice)
# {'name': 'Alice', 'Pay': Decimal('3000.00')}

compiler.compile(["name", "national_id"])
# ColumnDoesNotExistError: Column 'national_id' does not exist. Available columns: name, monthly_salary
```

### Describe the choices to a column picker

```python
from pyprojection import get_projection_json_schema

get_projection_json_schema(columns)["$defs"]["column_name"]["enum"]
# ['name', 'monthly_salary']
```

## When to use it

pyprojection earns its place when **users** choose the output shape:

- **Export dialogs**: CSV or Excel exports with user-picked columns and headers.
- **Report builders**: saved report layouts stored as JSON.
- **APIs**: a `?fields=name,department` query parameter, safely whitelisted.
- **Derived values**: columns computed by a lambda or a [pyformula](https://github.com/aaltatan/pyformula) `Formula`.

If the output shape is fixed, write a dict comprehension instead.

## Where to next

<div class="grid cards" markdown>

- [**Installation**](install.md): one command.
- [**User guide**](guide/index.md): every feature, one page each.
- [**Recipes**](recipes.md): an export dialog, `?fields=`, CSV, saved layouts.
- [**Definition format**](reference/definitions.md): the JSON shapes a compiler accepts.

</div>

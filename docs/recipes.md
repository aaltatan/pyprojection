# Recipes

Complete, runnable programs for common jobs. Each one is self-contained.

## An export dialog for employees

HR users pick the columns of an employee CSV. The dialog lists the columns from the JSON
Schema, the user's choice is sent back as JSON, and the server compiles it before writing a
single row. The national ID is registered as hidden, so no definition can ever select it.

This is [`examples/employee_export.py`](https://github.com/aaltatan/pyprojection/blob/main/examples/employee_export.py)
from the repository.

```python
import csv
import io
import json
from dataclasses import dataclass
from decimal import Decimal

from pyformula import FormulaCompiler, decimal_literal, variable

from pyprojection import (
    ColumnDoesNotExistError,
    ProjectionCompiler,
    ProjectionRegistry,
    get_projection_json_schema,
)


@dataclass(frozen=True, slots=True)
class Employee:
    name: str
    department: str
    salary: Decimal
    national_id: str


EMPLOYEES = [
    Employee("Alice", "Sales", Decimal("3000.00"), "123-45"),
    Employee("Bob", "IT", Decimal("4500.50"), "678-90"),
]

columns = ProjectionRegistry[Employee]()


@columns.column()
def name(employee: Employee) -> str:
    """Full name."""
    return employee.name


@columns.column()
def department(employee: Employee, *, upper: bool = False) -> str:
    """Department, optionally upper-cased."""
    return employee.department.upper() if upper else employee.department


@columns.column()
def monthly_salary(employee: Employee, places: int = 2) -> Decimal:
    """Monthly salary, rounded to `places` decimals."""
    return round(employee.salary, places)


@columns.column(hidden=True)
def national_id(employee: Employee) -> str:
    return employee.national_id


@variable()
def salary(employee: Employee) -> Decimal:
    return employee.salary


compiler = ProjectionCompiler(
    columns, FormulaCompiler[Employee]({"salary": salary}, literal=decimal_literal)
)

# What the dialog shows: the selectable columns, straight from the registry.
schema = get_projection_json_schema(columns, {"type": ["string", "number", "object"]})
print("selectable:", schema["$defs"]["column_name"]["enum"])
assert "national_id" not in schema["$defs"]["column_name"]["enum"]

# What the dialog sent back.
CHOICE = """
[
  "name",
  {"name": "department", "kwargs": {"upper": true}, "label": "Dept"},
  {"name": "monthly_salary", "label": "Monthly pay"},
  {"label": "Yearly pay", "formula": {"operator": "multiply", "expressions": ["salary", 12]}}
]
"""
export = compiler.compile(json.loads(CHOICE))

out = io.StringIO()
writer = csv.DictWriter(out, fieldnames=export.names, lineterminator="\n")
writer.writeheader()
writer.writerows(export(employee) for employee in EMPLOYEES)
print(out.getvalue())
assert out.getvalue().splitlines()[1] == "Alice,SALES,3000.00,36000.00"

# A crafted request for the hidden field is refused before any row is written.
try:
    compiler.compile(["name", "national_id"])
except ColumnDoesNotExistError as error:
    print(f"rejected: {error} {error.__notes__}")
    assert error.__notes__ == ["at $[1]"]
else:
    msg = "the hidden column should have been rejected"
    raise AssertionError(msg)
```

It prints:

```text
selectable: ['name', 'department', 'monthly_salary']
name,Dept,Monthly pay,Yearly pay
Alice,SALES,3000.00,36000.00
Bob,IT,4500.50,54006.00

rejected: Column 'national_id' does not exist. Available columns: name, department, monthly_salary ['at $[1]']
```

The schema here takes a placeholder formula schema; in a real dialog pass pyformula's
`get_formula_json_schema({"salary": salary})` so the formula editor can check what users type.

## `?fields=` in an API

A bare string is a column, so a comma-separated query parameter compiles as it is. A bad
field becomes a `400` with the position of the offending name.

```python
from dataclasses import dataclass

from pyprojection import ProjectionCompiler, ProjectionRegistry, PyprojectionError


@dataclass(frozen=True)
class User:
    username: str
    email: str
    password_hash: str


users = ProjectionRegistry[User]()

users.register_column(lambda u: u.username, name="username")

users.register_column(lambda u: u.email, name="email")

compiler = ProjectionCompiler(users)


def get_user(user: User, fields: str = "username") -> tuple[int, dict[str, object]]:
    try:
        projection = compiler.compile(fields.split(","))
    except PyprojectionError as error:
        return 400, {"error": str(error), "at": getattr(error, "__notes__", [])}

    return 200, projection(user)


alice = User("alice", "alice@example.com", "$argon2id$...")

assert get_user(alice, "username,email") == (
    200,
    {"username": "alice", "email": "alice@example.com"},
)

status, body = get_user(alice, "username,password_hash")

assert status == 400
assert body["at"] == ["at $[1]"]
```

`password_hash` was never registered, so it cannot be selected however the request is
crafted.

## Saved report layouts

Store the JSON a user built (in a database row, a settings file) and compile it when the
report runs. A layout that refers to a column you have since removed fails with its path,
not with a half-written file.

```python
import json
from dataclasses import dataclass

from pyprojection import ColumnDoesNotExistError, ProjectionCompiler, ProjectionRegistry


@dataclass(frozen=True)
class Order:
    number: str
    customer: str
    total: int


orders = ProjectionRegistry[Order]()


@orders.column()
def number(order: Order) -> str:
    return order.number


@orders.column()
def total(order: Order, *, currency: str = "USD") -> str:
    return f"{order.total} {currency}"


saved = '["number", {"name": "total", "kwargs": {"currency": "EUR"}, "label": "Total"}]'

layout = ProjectionCompiler(orders).compile(json.loads(saved))

assert layout(Order("A-1", "Acme", 120)) == {"number": "A-1", "Total": "120 EUR"}

# a layout saved before the `customer` column was removed
old = '["number", "customer"]'

try:
    ProjectionCompiler(orders).compile(json.loads(old))
except ColumnDoesNotExistError as error:
    assert error.__notes__ == ["at $[1]"]
```

## Reusing a base layout

Projections are immutable, so one base can feed several exports:

```python
from pyprojection import computed

base = computed("ID", lambda o: o.number) & computed("Customer", lambda o: o.customer)

summary = base & computed("Total", lambda o: o.total)

audit = base & computed("Total (cents)", lambda o: o.total * 100)

assert summary.names == ("ID", "Customer", "Total")
assert audit.names == ("ID", "Customer", "Total (cents)")
assert base.names == ("ID", "Customer")
```

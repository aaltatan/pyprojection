"""An export dialog where HR users pick the columns of an employee CSV.

The dialog lists the columns from the JSON Schema, the user's choice is sent
back as JSON, and the server compiles it before writing a single row. The
national ID is registered as hidden, so no definition can ever select it.

Run with: uv run python examples/employee_export.py
"""

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

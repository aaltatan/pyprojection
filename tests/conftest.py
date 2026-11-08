from dataclasses import dataclass
from decimal import Decimal

import pytest
from pyformula import FormulaCompiler, decimal_literal, variable

from pyprojection import ProjectionCompiler, ProjectionRegistry


@dataclass(frozen=True, slots=True)
class Employee:
    name: str
    department: str
    salary: Decimal
    national_id: str


ALICE = Employee("Alice", "Sales", Decimal("3000.00"), "123-45")
BOB = Employee("Bob", "IT", Decimal("4500.50"), "678-90")


@variable()
def salary(employee: Employee) -> Decimal:
    return employee.salary


def build_registry() -> ProjectionRegistry[Employee]:
    columns = ProjectionRegistry[Employee]()

    @columns.column()
    def name(employee: Employee) -> str:
        """Return the employee's full name."""
        return employee.name

    @columns.column(name="department")
    def dept(employee: Employee, *, upper: bool = False) -> str:
        return employee.department.upper() if upper else employee.department

    @columns.column(description="Monthly salary, rounded.")
    def monthly_salary(employee: Employee, places: int = 2) -> Decimal:
        return round(employee.salary, places)

    @columns.column(hidden=True)
    def national_id(employee: Employee) -> str:
        return employee.national_id

    return columns


@pytest.fixture
def alice() -> Employee:
    return ALICE


@pytest.fixture
def bob() -> Employee:
    return BOB


@pytest.fixture
def columns() -> ProjectionRegistry[Employee]:
    return build_registry()


@pytest.fixture
def compiler(columns) -> ProjectionCompiler[Employee]:
    return ProjectionCompiler(
        columns, FormulaCompiler[Employee]({"salary": salary}, literal=decimal_literal)
    )

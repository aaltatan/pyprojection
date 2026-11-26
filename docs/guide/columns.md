# Columns and registries

A **column** is a function whose first parameter is the subject, the object being exported.
A `ProjectionRegistry` collects columns by name and is the whitelist of what may be
selected.

```python
from dataclasses import dataclass
from decimal import Decimal

from pyprojection import ProjectionRegistry


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


columns["name"]()(alice)
# {'name': 'Alice'}
```

`columns["name"]` is the column's **factory**. Calling it returns a one-field
[`Projection`](projections.md); calling that with an employee returns a dict.

## Arguments

Parameters after the subject become arguments of the factory. They are bound **when the
projection is built**, so a wrong argument fails before the first row is exported.

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

`name=` registers the column under another name than the function's; `description=`
documents it in the [JSON Schema](json-schema.md) (it defaults to the docstring).

## Output names: `label=`

A column outputs under its own name unless you pass `label=`. Labels can be any non-empty
string, spaces included.

```python
columns["name"](label="Full name")(alice)
# {'Full name': 'Alice'}

columns["monthly_salary"](0, label="Monthly pay")(alice)
# {'Monthly pay': Decimal('3000')}
```

`label` is reserved on every factory, so a column function may not have a `label` parameter
of its own. That is rejected at registration:

```python
@columns.column()
def title(employee: Employee, label: str) -> str:
    return label
# InvalidColumnError: Column 'title' has a 'label' parameter, but 'label' is reserved for the output name.
```

## Using the factory directly

The decorator returns the factory, so the decorated name can be called directly:

```python
name()(bob)
# {'name': 'Bob'}
```

## Registering without the decorator

`register_column` registers a lambda or an existing function and returns its factory. A
lambda has no usable name, so it needs `name=`.

```python
columns.register_column(lambda e: e.name[0], name="initial")

columns["initial"]()(alice)
# {'initial': 'A'}

columns.register_column(lambda e: e.name)
# InvalidColumnNameError: Invalid column name: '<lambda>', you should follow the python variable naming convention: name must start with a letter and can only contain letters, numbers and underscores
```

Names must be unique within a registry, and a column must take the subject as its first
positional parameter:

```python
columns.register_column(lambda e: e.name, name="name")
# ColumnAlreadyRegisteredError: Column 'name' is already registered.

columns.register_column(lambda: "x", name="constant")
# InvalidColumnError: Column 'constant' must take the subject as its first positional parameter.
```

## Hidden columns

`hidden=True` keeps a column usable from Python, through the factory the decorator returns,
but out of lookups, [compilers](compiling.md) and [schemas](json-schema.md). Use it for
fields only internal code may export.

```python
@columns.column(hidden=True)
def national_id(employee: Employee) -> str:
    return employee.national_id


national_id()(alice)
# {'national_id': '123-45'}

columns["national_id"]
# ColumnDoesNotExistError: Column 'national_id' does not exist. Available columns: name, monthly_salary, department, initial
```

## Listing columns

`columns.columns` is a read-only mapping of the visible columns, name to factory, in
registration order:

```python
list(columns.columns)
# ['name', 'monthly_salary', 'department', 'initial']

"national_id" in columns.columns
# False
```

# Projections and computed columns

A `Projection` is an ordered tuple of `(output name, callable)` pairs. Calling it with a
subject returns `{name: fn(subject)}` in field order. This page continues the `Employee`
example from [Columns and registries](columns.md).

## Composing with `&`

`&` returns a new projection with the fields of both sides, in order. Projections are frozen,
so a base projection can be shared and extended safely.

```python
base = columns["name"]() & columns["department"]()

payroll = base & columns["monthly_salary"](label="Pay")

base
# Projection(name, department)

payroll(bob)
# {'name': 'Bob', 'department': 'IT', 'Pay': Decimal('4500.50')}
```

## Output names

`names` is the output header in order, for example for a CSV writer:

```python
base.names, payroll.names
# (('name', 'department'), ('name', 'department', 'Pay'))
```

Two fields with the same output name are rejected when the projection is built, not when the
first row is exported. Give one of them a `label`:

```python
base & columns["name"]()
# DuplicateOutputNameError: Output name 'name' is used more than once. Give one of them another name with label=...

(base & columns["name"](label="Name again")).names
# ('name', 'department', 'Name again')
```

## Computed columns

`computed(name, fn)` is a one-field projection for a derived value. The output name can be
any non-empty string, and `fn` any `T -> R` callable: a lambda, a method, a
[pyformula](https://github.com/aaltatan/pyformula) `Formula`.

```python
from pyprojection import computed

computed("Shouting", lambda e: e.name.upper())(alice)
# {'Shouting': 'ALICE'}

(base & computed("Initials", lambda e: e.name[:2]))(bob)
# {'name': 'Bob', 'department': 'IT', 'Initials': 'Bo'}
```

Formulas compose with arithmetic, so they are a natural fit for money columns:

```python
from pyformula import variable


@variable()
def salary(employee: Employee) -> Decimal:
    return employee.salary


yearly = computed("Yearly pay", salary * 12)

bonus = computed("Bonus", salary * Decimal("0.10"))

(base & yearly & bonus)(bob)
# {'name': 'Bob', 'department': 'IT', 'Yearly pay': Decimal('54006.00'), 'Bonus': Decimal('450.0500')}
```

A computed column is checked like any other field: the name must be a non-empty string and
the value callable.

```python
computed("", lambda e: e.name)
# InvalidOutputNameError: Invalid output name: '', expected a non-empty string

computed("Bonus", 100)
# InvalidColumnError: Column 'Bonus' must be callable, received 100
```

## Building a projection by hand

`Projection(fields)` takes the field tuple directly. Registries and `computed` are the usual
way, but the constructor is public and validates the same way:

```python
from pyprojection import Projection

Projection((("name", lambda e: e.name), ("dept", lambda e: e.department)))(alice)
# {'name': 'Alice', 'dept': 'Sales'}
```

`Projection(())` is the empty projection; it outputs `{}` and is the neutral element of `&`.

!!! note "No `|`, `~` or removal operator"
    A projection only grows. "Everything except X" would contradict the whitelist: start from
    the columns you want instead.

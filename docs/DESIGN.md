# pyprojection design

Usage lives in the README; this file records the decisions and why.

## Values

- `Projection[T]` is a frozen dataclass holding `fields: tuple[tuple[str, Callable[[T], Any]], ...]`.
  Calling it returns `{name: fn(subject)}` in field order.
- `&` concatenates fields. Validation (non-empty string names, callables, no duplicate output
  names) runs in `__post_init__`, so `&`, `computed` and direct construction fail the same way,
  when built.
- No `|`, `~` or removal operator: nobody asked, and "all but X" contradicts the whitelist.

## Registry: the privacy boundary

- `ProjectionRegistry[T]` wraps `pyvocabulary.Vocabulary` with column-specific errors.
- `@columns.column()` turns `fn(subject, *args, **kwargs)` into a factory
  `(*args, label=None, **kwargs) -> Projection[T]`. Arguments are bound with
  `Signature.bind` when the factory is called, not per row.
- `label` is reserved on factories, so a column function with a `label` parameter is rejected
  at registration rather than silently shadowed.
- `hidden=True` columns stay usable from Python but are invisible to `__getitem__`, the
  compiler and the schema. This is how "never exportable from user input" is expressed.

## JSON

A definition is a list; each item is a string (column, no arguments), a call
`{"name", "args", "kwargs", "label"}` (the family's call shape plus `label`), or a computed
column `{"label", "formula"}`. Strings make `?fields=a,b` a one-liner. Formulas go to an
injected `Compiler` (pyformula's `FormulaCompiler` fits); without one, computed columns are
rejected, so an API can offer pure column picking.

Shape errors are `InvalidProjectionDefinitionError` with the path in the message. Errors
from the registry and the formula compiler keep their type and get an `at $[i]` note via
`pyvocabulary.located`. An empty list is rejected: an export with no columns is a mistake.

## Schema

`get_projection_json_schema(columns, formula_schema=None)`: an array (`minItems: 1`) of
`column_name` (enum of visible names, for pickers), `call` (one `call_json_schema` per column)
or, when `formula_schema` is given, `computed` (the formula schema embedded under its own `$id`).

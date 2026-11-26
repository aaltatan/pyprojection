# API

`T` is the type of the subject, the object a projection is called with.

## Projections

### `Projection[T]`

```py
@dataclass(frozen=True, slots=True)
class Projection[T]:
    fields: tuple[Field[T], ...]
```

Fields in output order. Validated when built: every output name is a non-empty string, every
value is callable, and no output name appears twice.

| Member | Description |
| --- | --- |
| `projection(subject) -> dict[str, Any]` | `{name: fn(subject)}` in field order |
| `a & b` | new projection with the fields of `a`, then `b` |
| `projection.names -> tuple[str, ...]` | the output names in order, e.g. a CSV header |
| `projection.fields` | the `(output name, callable)` pairs |
| `repr(projection)` | `Projection(name, Monthly pay, ...)` |

Raises, when built: `InvalidOutputNameError`, `InvalidColumnError`,
`DuplicateOutputNameError`.

Guide: [Projections and computed columns](../guide/projections.md).

### `computed`

```py
computed(name: str, value: Callable[[T], Any], /) -> Projection[T]
```

A one-field projection that outputs `value(subject)` under `name`. `name` is any non-empty
string; `value` any callable, typically a pyformula `Formula`.

### `Field`

```py
type Field[T] = tuple[str, Callable[[T], Any]]
```

One `(output name, callable)` pair of a projection.

## Registries

### `ProjectionRegistry[T]`

```py
ProjectionRegistry[T]()
```

Named columns over subjects of type `T`: the whitelist of what may be selected.

| Member | Description |
| --- | --- |
| `registry[name] -> ColumnFactory[T]` | the factory of a visible column; `ColumnDoesNotExistError` otherwise |
| `registry.columns -> Mapping[str, ColumnFactory[T]]` | read-only view of the visible columns, in registration order |
| `registry.column(*, name=None, description=None, hidden=False)` | decorator: registers the function and returns its factory |
| `registry.register_column(fn, /, *, name=None, description=None, hidden=False)` | registers `fn` and returns its factory |

- `name`: the column name, defaults to the function's `__name__`. Must be an ASCII Python
  identifier, so a lambda needs `name=`.
- `description`: documents the column in its JSON Schema, defaults to the docstring.
- `hidden`: keep the column usable through the returned factory, but out of lookups,
  compilers and schemas.

`fn` must take the subject as its first positional parameter and may not have a `label`
parameter. Its other parameters become the factory's arguments.

Raises, when registering: `InvalidColumnNameError`, `ColumnAlreadyRegisteredError` (the name
is taken, hidden or not), `InvalidColumnError`.

Guide: [Columns and registries](../guide/columns.md).

### `ColumnFactory[T]`

```py
class ColumnFactory[T](Protocol):
    def __call__(self, *args: Any, label: str | None = None, **kwargs: Any) -> Projection[T]: ...
```

Binds the column function's arguments right away (raising `InvalidColumnArgumentsError` if
they do not fit) and returns a one-field projection named `label`, or the column name. Its
`__signature__` is the function's signature without the subject, and its `__doc__` the
column's description.

## Compiling

### `ProjectionCompiler[T]`

```py
ProjectionCompiler(
    columns: ProjectionRegistry[T],
    formulas: Compiler[Callable[[T], Any]] | None = None,
    /,
)
```

| Member | Description |
| --- | --- |
| `compiler.compile(definition, /) -> Projection[T]` | compile a [definition](definitions.md) |

Only the registry's visible columns can be selected. Without `formulas`, a definition with a
computed column is rejected.

Raises, from `compile`: `InvalidProjectionDefinitionError`, `ColumnDoesNotExistError`,
`InvalidColumnArgumentsError`, `DuplicateOutputNameError`, and whatever the formula compiler
raises. Every error except `InvalidProjectionDefinitionError` (which has the path in its
message) gets a note with its JSON path, e.g. `at $[1]`.

Guide: [Compiling projections from JSON](../guide/compiling.md).

### `Compiler[F]`

```py
class Compiler[F](Protocol):
    def compile(self, definition: Any, /) -> F: ...
```

Anything with a `compile` method, e.g. pyformula's `FormulaCompiler`.

### `ColumnDefinition`, `ColumnCallDict`, `ComputedDict`

```py
class ColumnCallDict(TypedDict):
    name: str
    args: NotRequired[list[Any]]
    kwargs: NotRequired[dict[str, Any]]
    label: NotRequired[str]


class ComputedDict(TypedDict):
    label: str
    formula: Any


type ColumnDefinition = str | ColumnCallDict | ComputedDict
```

The types of one item of a definition. See [Definition format](definitions.md).

## JSON Schema

### `get_projection_json_schema`

```py
get_projection_json_schema(
    columns: ProjectionRegistry[Any],
    formula_schema: Mapping[str, Any] | None = None,
    /,
) -> dict[str, Any]
```

The draft 2020-12 JSON Schema of the definitions a compiler over `columns` accepts. Hidden
columns are left out. Without `formula_schema`, computed columns are not allowed.

| Key | Content |
| --- | --- |
| `$defs.column_name` | `{"type": "string", "enum": [visible column names]}` |
| `$defs.call` | `{"anyOf": [one schema per column]}`, each with `args`, `kwargs`, `label` and a `description`; `false` if there are no columns |
| `$defs.computed` | only with `formula_schema`: `{"label", "formula"}`, both required |
| `$defs.formula` | only with `formula_schema`: that schema, with `$id` set to `FORMULA_SCHEMA_ID` |

Guide: [JSON Schema](../guide/json-schema.md).

### `FORMULA_SCHEMA_ID`

```py
FORMULA_SCHEMA_ID = "urn:pyprojection:formula"
```

The `$id` under which a formula schema is embedded.

## Exceptions

See [Exceptions](exceptions.md).

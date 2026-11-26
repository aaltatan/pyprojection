# Reference

- [API](api.md): every public name of `pyprojection`.
- [Definition format](definitions.md): the JSON shapes `ProjectionCompiler` accepts.
- [Exceptions](exceptions.md): the exception hierarchy and when each one is raised.

Everything is importable from the package root:

```python
import pyprojection

sorted(pyprojection.__all__)
# ['ColumnAlreadyRegisteredError', 'ColumnCallDict', 'ColumnDefinition', 'ColumnDoesNotExistError', 'ColumnFactory', 'Compiler', 'ComputedDict', 'DuplicateOutputNameError', 'FORMULA_SCHEMA_ID', 'Field', 'InvalidColumnArgumentsError', 'InvalidColumnError', 'InvalidColumnNameError', 'InvalidOutputNameError', 'InvalidProjectionDefinitionError', 'Projection', 'ProjectionCompiler', 'ProjectionRegistry', 'PyprojectionError', 'computed', 'get_projection_json_schema']
```

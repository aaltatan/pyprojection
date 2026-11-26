# Installation

pyprojection needs **Python 3.12 or newer**.

=== "uv"

    ```bash
    uv add pyprojection
    ```

=== "pip"

    ```bash
    pip install pyprojection
    ```

Its only dependency is [pyvocabulary](https://pypi.org/project/pyvocabulary/), a small
package by the same author that provides the registry, JSON Schema and JSON-path helpers.

[pyformula](https://pypi.org/project/pyformula/) is optional. `computed` takes any callable,
and `ProjectionCompiler` takes any object with a `compile` method for formulas. Install it
when you want computed columns written as formulas, in Python or in JSON:

```bash
uv add pyformula
```

## Check it works

```python
from pyprojection import computed

computed("Initial", lambda word: word[0])("Alice")
# {'Initial': 'A'}
```

from decimal import Decimal

import pytest
from conftest import salary
from pyformula import FormulaNotFoundError

from pyprojection import (
    ColumnDoesNotExistError,
    DuplicateOutputNameError,
    InvalidColumnArgumentsError,
    InvalidProjectionDefinitionError,
    ProjectionCompiler,
    computed,
)

DEFINITION = [
    "name",
    {"name": "department", "kwargs": {"upper": True}, "label": "Dept"},
    {"name": "monthly_salary", "args": [0], "label": "Monthly pay"},
    {"label": "Yearly pay", "formula": {"operator": "multiply", "expressions": ["salary", 12]}},
]


class TestCompiling:
    def test_matches_the_python_projection(self, compiler, columns, alice, bob):
        python = (
            columns["name"]()
            & columns["department"](upper=True, label="Dept")
            & columns["monthly_salary"](0, label="Monthly pay")
            & computed("Yearly pay", salary * 12)
        )
        compiled = compiler.compile(DEFINITION)

        assert repr(compiled) == repr(python)
        assert [compiled(e) for e in (alice, bob)] == [python(e) for e in (alice, bob)]

    def test_values(self, compiler, alice):
        assert compiler.compile(DEFINITION)(alice) == {
            "name": "Alice",
            "Dept": "SALES",
            "Monthly pay": Decimal(3000),
            "Yearly pay": Decimal("36000.00"),
        }

    def test_query_string_fields(self, compiler, alice):
        fields = "name,department"  # from ?fields=name,department
        assert compiler.compile(fields.split(","))(alice) == {
            "name": "Alice",
            "department": "Sales",
        }

    def test_args_kwargs_and_label_are_optional(self, compiler, alice):
        assert compiler.compile([{"name": "name"}])(alice) == {"name": "Alice"}

    def test_formulas_are_optional(self, columns, alice):
        assert ProjectionCompiler(columns).compile(["name"])(alice) == {"name": "Alice"}


class TestErrors:
    def test_unknown_column_keeps_its_type_and_gets_the_path(self, compiler):
        with pytest.raises(ColumnDoesNotExistError, match="Available columns") as info:
            compiler.compile(["name", "salary"])

        assert info.value.__notes__ == ["at $[1]"]

    def test_hidden_column_cannot_be_selected(self, compiler):
        with pytest.raises(ColumnDoesNotExistError) as info:
            compiler.compile([{"name": "national_id"}])

        assert info.value.__notes__ == ["at $[0]"]

    def test_bad_arguments_get_the_path(self, compiler):
        with pytest.raises(InvalidColumnArgumentsError) as info:
            compiler.compile(["name", {"name": "department", "kwargs": {"lower": True}}])

        assert info.value.__notes__ == ["at $[1]"]

    def test_duplicate_output_name_gets_the_path(self, compiler):
        with pytest.raises(DuplicateOutputNameError) as info:
            compiler.compile(["name", "department", {"name": "department"}])

        assert info.value.__notes__ == ["at $[2]"]

    def test_formula_errors_keep_their_type_and_get_the_path(self, compiler):
        bad = {"label": "x", "formula": {"operator": "add", "expressions": ["salry", 1]}}

        with pytest.raises(FormulaNotFoundError) as info:
            compiler.compile(["name", bad])

        # pyformula reports the path inside the formula; pyprojection prefixes its own
        assert info.value.__notes__ == ["at $[1].formula.expressions[0]"]

    def test_formula_without_a_formula_compiler(self, columns):
        with pytest.raises(InvalidProjectionDefinitionError, match=r"\$\[0\].*no formula compiler"):
            ProjectionCompiler(columns).compile([{"label": "x", "formula": "salary"}])

    @pytest.mark.parametrize(
        ("definition", "message"),
        [
            ({"name": "name"}, r"Invalid projection at \$: expected a list"),
            ("name", r"Invalid projection at \$: expected a list"),
            ([], r"Invalid projection at \$: expected at least one column"),
            ([3], r"Invalid projection at \$\[0\]: expected a column name or an object"),
            ([{"args": []}], r"at \$\[0\]: missing 'name' or 'formula'"),
            ([{"name": "name", "formula": 1}], r"at \$\[0\]: use either 'name' or 'formula'"),
            ([{"name": "name", "kwarg": {}}], r"at \$\[0\]: unknown 'kwarg'. Allowed keys: args"),
            ([{"formula": "salary"}], r"at \$\[0\]: missing 'label'"),
            ([{"formula": "salary", "label": "x", "args": []}], r"unknown 'args'"),
            ([{"name": 3}], r"at \$\[0\]\.name: expected a string, received 3"),
            ([{"name": "name", "args": {}}], r"at \$\[0\]\.args: expected a list"),
            ([{"name": "name", "kwargs": []}], r"at \$\[0\]\.kwargs: expected an object"),
            ([{"name": "name", "label": ""}], r"at \$\[0\]\.label: expected a non-empty string"),
            ([{"name": "name", "kwargs": {"label": "x"}}], r"'label' goes beside 'name'"),
        ],
    )
    def test_shape_errors_say_where_and_what(self, compiler, definition, message):
        with pytest.raises(InvalidProjectionDefinitionError, match=message):
            compiler.compile(definition)

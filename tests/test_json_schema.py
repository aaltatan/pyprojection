import pytest
from jsonschema import Draft202012Validator
from test_compilers import DEFINITION

from pyprojection import get_projection_json_schema

FORMULA_SCHEMA = {"anyOf": [{"type": "string"}, {"type": "number"}, {"type": "object"}]}


@pytest.fixture
def schema(columns):
    return get_projection_json_schema(columns, FORMULA_SCHEMA)


@pytest.fixture
def validator(schema):
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


class TestSchema:
    def test_accepts_what_the_compiler_accepts(self, validator):
        assert validator.is_valid(DEFINITION)
        assert validator.is_valid(["name", "department"])

    @pytest.mark.parametrize(
        "definition",
        [
            [],
            ["salary"],
            ["national_id"],  # hidden
            [{"name": "national_id"}],
            [{"name": "name", "args": [1]}],
            [{"name": "department", "kwargs": {"lower": True}}],
            [{"name": "department", "kwargs": {"upper": "yes"}}],
            [{"name": "name", "label": ""}],
            [{"formula": "salary"}],
            {"name": "name"},
        ],
    )
    def test_rejects_what_the_compiler_rejects(self, validator, definition):
        assert not validator.is_valid(definition)

    def test_column_names_are_listed_for_pickers(self, schema):
        assert schema["$defs"]["column_name"]["enum"] == ["name", "department", "monthly_salary"]

    def test_descriptions_come_from_docstrings(self, schema):
        calls = {
            call["properties"]["name"]["const"]: call for call in schema["$defs"]["call"]["anyOf"]
        }
        assert calls["name"]["description"] == "Return the employee's full name."
        assert calls["monthly_salary"]["properties"]["args"]["prefixItems"] == [
            {"type": "integer", "default": 2}
        ]

    def test_without_a_formula_schema_formulas_are_not_allowed(self, columns):
        validator = Draft202012Validator(get_projection_json_schema(columns))
        assert not validator.is_valid([{"label": "x", "formula": "salary"}])
        assert validator.is_valid(["name"])

from decimal import Decimal

import pytest

from pyprojection import (
    ColumnAlreadyRegisteredError,
    ColumnDoesNotExistError,
    InvalidColumnArgumentsError,
    InvalidColumnError,
    InvalidColumnNameError,
    ProjectionRegistry,
)


class TestLookup:
    def test_visible_columns_are_listed(self, columns):
        assert list(columns.columns) == ["name", "department", "monthly_salary"]

    def test_unknown_column_says_what_is_available(self, columns):
        with pytest.raises(
            ColumnDoesNotExistError,
            match=r"Column 'salary' does not exist. Available columns: name, department, monthly_salary",
        ):
            columns["salary"]

    def test_unknown_column_is_a_lookup_error(self, columns):
        with pytest.raises(LookupError):
            columns["nope"]

    def test_hidden_column_cannot_be_looked_up(self, columns):
        # the privacy boundary: hidden columns are invisible to lookups and compilers
        with pytest.raises(ColumnDoesNotExistError):
            columns["national_id"]

    def test_hidden_column_is_still_usable_from_python(self, alice):
        registry = ProjectionRegistry()

        @registry.column(hidden=True)
        def secret(employee) -> str:
            return employee.national_id

        assert secret()(alice) == {"secret": "123-45"}


class TestFactories:
    def test_name_override(self, columns, alice):
        assert columns["department"]()(alice) == {"department": "Sales"}

    def test_arguments_are_passed_after_the_subject(self, columns, alice, bob):
        assert columns["department"](upper=True)(alice) == {"department": "SALES"}
        assert columns["monthly_salary"](0)(bob) == {"monthly_salary": Decimal(4500)}

    def test_label_renames_the_output(self, columns, alice):
        assert columns["name"](label="Full name")(alice) == {"Full name": "Alice"}

    def test_decorator_returns_the_factory(self, alice):
        registry = ProjectionRegistry()

        @registry.column()
        def name(employee) -> str:
            return employee.name

        assert name is registry["name"]
        assert name()(alice) == {"name": "Alice"}

    def test_description_and_docstring(self, columns):
        assert columns["name"].__doc__ == "Return the employee's full name."
        assert columns["monthly_salary"].__doc__ == "Monthly salary, rounded."

    def test_register_column_without_a_decorator(self, alice):
        registry = ProjectionRegistry()
        registry.register_column(lambda e: e.name.upper(), name="shout")
        assert registry["shout"]()(alice) == {"shout": "ALICE"}


class TestArgumentsBoundWhenBuilt:
    def test_too_many_arguments(self, columns):
        with pytest.raises(InvalidColumnArgumentsError, match=r"Column 'name'.*too many"):
            columns["name"](1)

    def test_unexpected_keyword(self, columns):
        with pytest.raises(InvalidColumnArgumentsError, match=r"'department'.*unexpected keyword"):
            columns["department"](lower=True)

    def test_missing_argument(self):
        registry = ProjectionRegistry()

        @registry.column()
        def price_in(product, currency: str) -> str:
            return f"{product} {currency}"

        with pytest.raises(InvalidColumnArgumentsError, match=r"missing"):
            price_in()

    def test_is_a_type_error(self, columns):
        with pytest.raises(TypeError):
            columns["name"](1)

    def test_label_must_be_a_non_empty_string(self, columns):
        with pytest.raises(ValueError, match=r"non-empty string"):
            columns["name"](label="")


class TestRegistrationFailsEarly:
    def test_duplicate_name(self, columns):
        with pytest.raises(ColumnAlreadyRegisteredError, match=r"'name' is already registered"):
            columns.register_column(lambda e: e, name="name")

    def test_duplicate_of_a_hidden_name(self, columns):
        with pytest.raises(ColumnAlreadyRegisteredError):
            columns.register_column(lambda e: e, name="national_id")

    def test_invalid_name(self):
        with pytest.raises(InvalidColumnNameError, match=r"Invalid column name: 'monthly-pay'"):
            ProjectionRegistry().register_column(lambda e: e, name="monthly-pay")

    def test_lambda_needs_a_name(self):
        with pytest.raises(InvalidColumnNameError, match=r"'<lambda>'"):
            ProjectionRegistry().register_column(lambda e: e)

    def test_function_must_take_the_subject(self):
        with pytest.raises(InvalidColumnError, match=r"'now'.*subject"):
            ProjectionRegistry().register_column(lambda: 1, name="now")

    def test_function_must_not_take_label(self):
        def tagged(employee, label: str) -> str:
            return label

        with pytest.raises(InvalidColumnError, match=r"'label' is reserved"):
            ProjectionRegistry().register_column(tagged)

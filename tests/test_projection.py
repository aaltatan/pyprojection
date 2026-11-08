from decimal import Decimal

import pytest
from conftest import salary

from pyprojection import (
    DuplicateOutputNameError,
    InvalidOutputNameError,
    Projection,
    computed,
)


class TestCalling:
    def test_maps_a_subject_to_a_dict_in_order(self, columns, alice):
        projection = (
            columns["name"]()
            & columns["monthly_salary"](label="Monthly pay")
            & computed("Yearly pay", salary * 12)
        )

        assert projection(alice) == {
            "name": "Alice",
            "Monthly pay": Decimal("3000.00"),
            "Yearly pay": Decimal("36000.00"),
        }
        assert list(projection(alice)) == ["name", "Monthly pay", "Yearly pay"]

    def test_names_are_the_output_keys(self, columns):
        projection = columns["name"]() & computed("Yearly pay", salary * 12)
        assert projection.names == ("name", "Yearly pay")

    def test_repr_lists_the_output_names(self, columns):
        projection = columns["name"]() & columns["department"](label="Dept")
        assert repr(projection) == "Projection(name, Dept)"

    def test_is_reusable_across_subjects(self, columns, alice, bob):
        projection = columns["name"]()
        assert [projection(e) for e in (alice, bob)] == [{"name": "Alice"}, {"name": "Bob"}]


class TestComposition:
    def test_and_returns_a_new_projection(self, columns):
        left = columns["name"]()
        right = columns["department"]()
        combined = left & right

        assert combined is not left
        assert left.names == ("name",)
        assert combined.names == ("name", "department")

    def test_and_is_associative(self, columns, alice):
        a, b, c = columns["name"](), columns["department"](), computed("x", salary)
        assert ((a & b) & c)(alice) == (a & (b & c))(alice)

    def test_duplicate_output_names_are_rejected_when_built(self, columns):
        with pytest.raises(DuplicateOutputNameError, match=r"'name'.*more than once"):
            columns["name"]() & columns["name"]()

    def test_a_label_resolves_a_duplicate(self, columns):
        projection = columns["name"]() & columns["name"](label="Full name")
        assert projection.names == ("name", "Full name")

    def test_and_with_something_else_is_not_supported(self, columns):
        with pytest.raises(TypeError):
            columns["name"]() & (lambda e: e)  # type: ignore[operator]


class TestComputed:
    def test_takes_any_callable(self, alice):
        assert computed("Initial", lambda e: e.name[0])(alice) == {"Initial": "A"}

    @pytest.mark.parametrize("name", ["", 3, None])
    def test_rejects_an_invalid_output_name(self, name):
        with pytest.raises(InvalidOutputNameError, match=r"non-empty string"):
            computed(name, salary)

    def test_rejects_a_non_callable(self):
        with pytest.raises(TypeError, match=r"callable"):
            computed("x", 12)  # type: ignore[arg-type]


class TestDirectConstruction:
    def test_validates_like_the_operators_do(self, alice):
        with pytest.raises(DuplicateOutputNameError):
            Projection((("a", str), ("a", repr)))

    def test_empty_projection_maps_to_an_empty_dict(self, alice):
        assert Projection(())(alice) == {}

    def test_is_immutable(self, columns):
        projection = columns["name"]()
        with pytest.raises(AttributeError):
            projection.fields = ()  # type: ignore[misc]

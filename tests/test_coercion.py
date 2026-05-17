"""Tests for type coercion (FR-12, FR-13, FR-14, FR-41).

Tests verify coercion of string values to typed values, including
primitive types, bool semantics, and enum types. Tests are black-box
and import only from the configsloader public API.
"""

import enum
import pytest

from configsloader.coercion import coerce

from conftest import Color, Priority, Mode


@pytest.mark.unit
class TestStringToIntCoercion:
    """FR-12: str to int coercion (AC-12.1)."""

    def test_coerces_string_to_int(self):
        result = coerce("42", int, "port")
        assert result == 42

    def test_coerces_negative_string_to_int(self):
        result = coerce("-10", int, "offset")
        assert result == -10

    def test_coerces_zero_string_to_int(self):
        result = coerce("0", int, "count")
        assert result == 0


@pytest.mark.unit
class TestStringToFloatCoercion:
    """FR-12: str to float coercion."""

    def test_coerces_string_to_float(self):
        result = coerce("3.14", float, "rate")
        assert result == 3.14

    def test_coerces_integer_string_to_float(self):
        result = coerce("7", float, "factor")
        assert result == 7.0

    def test_coerces_negative_float_string(self):
        result = coerce("-2.5", float, "threshold")
        assert result == -2.5


@pytest.mark.unit
class TestStringToBoolCoercion:
    """FR-13: str to bool coercion with extended semantics (AC-13.1 - AC-13.4)."""

    def test_coerces_true_string_to_true(self):
        result = coerce("true", bool, "verbose")
        assert result is True

    def test_coerces_one_string_to_true(self):
        result = coerce("1", bool, "verbose")
        assert result is True

    def test_coerces_yes_string_to_true(self):
        result = coerce("yes", bool, "verbose")
        assert result is True

    def test_coerces_TRUE_uppercase_to_true(self):
        result = coerce("TRUE", bool, "verbose")
        assert result is True

    def test_coerces_Yes_mixed_case_to_true(self):
        result = coerce("Yes", bool, "verbose")
        assert result is True

    def test_coerces_false_string_to_false(self):
        result = coerce("false", bool, "verbose")
        assert result is False

    def test_coerces_zero_string_to_false(self):
        result = coerce("0", bool, "verbose")
        assert result is False

    def test_coerces_no_string_to_false(self):
        result = coerce("no", bool, "verbose")
        assert result is False

    def test_coerces_arbitrary_string_to_false(self):
        """AC-13.4: non-truthy strings resolve to False."""
        result = coerce("nope", bool, "verbose")
        assert result is False

    def test_coerces_empty_string_to_false(self):
        result = coerce("", bool, "verbose")
        assert result is False


@pytest.mark.unit
class TestStringToEnumCoercion:
    """FR-14: str to Enum coercion (AC-14.1 - AC-14.4)."""

    def test_coerces_enum_by_value(self):
        """AC-14.3: coercion by value."""
        result = coerce("red", Color, "color")
        assert result is Color.RED

    def test_coerces_enum_by_name_case_insensitive(self):
        """AC-14.1: coercion by name, case-insensitive."""
        result = coerce("RED", Color, "color")
        assert result is Color.RED

    def test_coerces_enum_by_name_mixed_case(self):
        """AC-14.2: case-insensitive name matching."""
        result = coerce("Green", Color, "color")
        assert result is Color.GREEN

    def test_raises_on_invalid_enum_string(self):
        """AC-14.4: invalid enum string raises ValueError."""
        with pytest.raises(ValueError):
            coerce("purple", Color, "color")


@pytest.mark.unit
class TestStringToStrEnumCoercion:
    """FR-14: str to StrEnum coercion."""

    def test_coerces_strenum_by_value(self):
        result = coerce("fast", Mode, "mode")
        assert result is Mode.FAST

    def test_coerces_strenum_by_name_case_insensitive(self):
        result = coerce("SLOW", Mode, "mode")
        assert result is Mode.SLOW


@pytest.mark.unit
class TestStringToIntEnumCoercion:
    """FR-14: str to IntEnum coercion."""

    def test_coerces_intenum_by_name(self):
        result = coerce("HIGH", Priority, "priority")
        assert result is Priority.HIGH

    def test_coerces_intenum_by_name_case_insensitive(self):
        result = coerce("low", Priority, "priority")
        assert result is Priority.LOW

    def test_coerces_intenum_by_value_string(self):
        """IntEnum can be coerced by numeric string value."""
        result = coerce("3", Priority, "priority")
        assert result is Priority.HIGH


@pytest.mark.unit
class TestCoercionFailure:
    """FR-41: Coercion failure raises ValueError (AC-40.1)."""

    def test_raises_on_non_numeric_to_int(self):
        with pytest.raises(ValueError):
            coerce("abc", int, "port")

    def test_raises_on_non_numeric_to_float(self):
        with pytest.raises(ValueError):
            coerce("not_a_number", float, "rate")

    def test_error_identifies_field_name(self):
        with pytest.raises(ValueError, match="port"):
            coerce("abc", int, "port")

    def test_error_identifies_invalid_value(self):
        with pytest.raises(ValueError, match="abc"):
            coerce("abc", int, "port")


@pytest.mark.unit
class TestValuePassthrough:
    """Value already correct type passes through unchanged."""

    def test_int_passes_through_as_int(self):
        result = coerce(42, int, "port")
        assert result == 42
        assert isinstance(result, int)

    def test_float_passes_through_as_float(self):
        result = coerce(3.14, float, "rate")
        assert result == 3.14
        assert isinstance(result, float)

    def test_bool_passes_through_as_bool(self):
        result = coerce(True, bool, "verbose")
        assert result is True

    def test_str_passes_through_as_str(self):
        result = coerce("hello", str, "name")
        assert result == "hello"

    def test_enum_passes_through_as_enum(self):
        result = coerce(Color.RED, Color, "color")
        assert result is Color.RED

    def test_none_passes_through_as_none(self):
        result = coerce(None, int, "port")
        assert result is None

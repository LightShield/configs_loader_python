"""Tests for the ConfigsLoader metaclass (FR-01, FR-38, FR-42).

Tests verify that the metaclass collects Field declarations, detects
reserved flag conflicts, and detects duplicate flag declarations at
class definition time.
"""

import pytest

from configsloader import ConfigsLoader, Field


@pytest.mark.unit
class TestMetaclassFieldCollection:
    """Metaclass collects Field declarations from class body."""

    def test_collects_field_with_descriptor(self):
        class MyConfig(ConfigsLoader):
            host: str = Field(default="localhost", flags=["--host"])

        assert "host" in MyConfig._fields

    def test_collected_field_preserves_default(self):
        class MyConfig(ConfigsLoader):
            port: int = Field(default=8080, flags=["--port"])

        assert MyConfig._fields["port"].default == 8080

    def test_collected_field_preserves_flags(self):
        class MyConfig(ConfigsLoader):
            model: str = Field(default="gpt4", flags=["--model", "-m"])

        assert MyConfig._fields["model"].flags == ["--model", "-m"]

    def test_collects_multiple_fields(self):
        class MyConfig(ConfigsLoader):
            host: str = Field(default="localhost", flags=["--host"])
            port: int = Field(default=8080, flags=["--port"])
            debug: bool = Field(default=False, flags=["--debug"])

        assert len(MyConfig._fields) == 3

    def test_field_without_descriptor_gets_default_field(self):
        """Fields with type annotations but no Field() get a default FieldDescriptor."""
        class MyConfig(ConfigsLoader):
            name: str = "default_name"

        assert "name" in MyConfig._fields
        assert MyConfig._fields["name"].default == "default_name"


@pytest.mark.unit
class TestMetaclassTypeAnnotations:
    """Type annotations are captured by the metaclass."""

    def test_captures_str_annotation(self):
        class MyConfig(ConfigsLoader):
            host: str = Field(default="localhost")

        # The metaclass should store type information accessible for coercion
        import typing
        hints = typing.get_type_hints(MyConfig)
        assert hints["host"] is str

    def test_captures_int_annotation(self):
        class MyConfig(ConfigsLoader):
            port: int = Field(default=8080)

        import typing
        hints = typing.get_type_hints(MyConfig)
        assert hints["port"] is int

    def test_captures_bool_annotation(self):
        class MyConfig(ConfigsLoader):
            debug: bool = Field(default=False)

        import typing
        hints = typing.get_type_hints(MyConfig)
        assert hints["debug"] is bool


@pytest.mark.unit
class TestReservedFlagDetection:
    """FR-38: Reserved flag detection at class definition time."""

    def test_raises_on_help_flag(self):
        with pytest.raises((ValueError, TypeError)):
            class BadConfig(ConfigsLoader):
                my_field: str = Field(flags=["--help"])

    def test_raises_on_short_help_flag(self):
        with pytest.raises((ValueError, TypeError)):
            class BadConfig(ConfigsLoader):
                my_field: str = Field(flags=["-h"])

    def test_raises_on_preset_flag(self):
        with pytest.raises((ValueError, TypeError)):
            class BadConfig(ConfigsLoader):
                my_field: str = Field(flags=["--preset"])

    def test_raises_on_print_config_flag(self):
        with pytest.raises((ValueError, TypeError)):
            class BadConfig(ConfigsLoader):
                my_field: str = Field(flags=["--print-config"])

    def test_raises_on_print_config_verbose_flag(self):
        with pytest.raises((ValueError, TypeError)):
            class BadConfig(ConfigsLoader):
                my_field: str = Field(flags=["--print-config-verbose"])

    def test_no_error_for_non_reserved_flags(self):
        # Should not raise
        class GoodConfig(ConfigsLoader):
            host: str = Field(flags=["--host", "-H"])

        assert "host" in GoodConfig._fields


@pytest.mark.unit
class TestDuplicateFlagDetection:
    """FR-42: Duplicate flag detection at class definition time."""

    def test_raises_on_duplicate_long_flag(self):
        with pytest.raises((ValueError, TypeError)):
            class BadConfig(ConfigsLoader):
                host: str = Field(flags=["--host"])
                server: str = Field(flags=["--host"])

    def test_raises_on_duplicate_short_flag(self):
        with pytest.raises((ValueError, TypeError)):
            class BadConfig(ConfigsLoader):
                host: str = Field(flags=["--host", "-H"])
                server: str = Field(flags=["--server", "-H"])

    def test_error_identifies_conflicting_fields(self):
        """The error message should identify which fields conflict."""
        with pytest.raises((ValueError, TypeError), match=r"(host|server)"):
            class BadConfig(ConfigsLoader):
                host: str = Field(flags=["--addr"])
                server: str = Field(flags=["--addr"])

    def test_no_error_for_unique_flags(self):
        # Should not raise
        class GoodConfig(ConfigsLoader):
            host: str = Field(flags=["--host", "-H"])
            port: int = Field(flags=["--port", "-p"])

        assert "host" in GoodConfig._fields
        assert "port" in GoodConfig._fields

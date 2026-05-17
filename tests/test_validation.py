"""Tests for validation — FR-15 through FR-19, FR-41.

Covers: required fields, custom validators, validation error collection,
validation timing, cross-field validators, type coercion failure handling.
"""

import os
from pathlib import Path

import pytest

from configsloader import ConfigsLoader, Field


# ---------------------------------------------------------------------------
# Config classes used across validation tests
# ---------------------------------------------------------------------------


class RequiredFieldConfig(ConfigsLoader):
    host: str = Field(required=True, flags=["--host"], env="VAL_HOST", description="Server host")
    port: int = Field(default=8080, flags=["--port"], description="Server port")


class ValidatorConfig(ConfigsLoader):
    port: int = Field(
        default=8080,
        flags=["--port"],
        description="Port number",
        validator=lambda v: v > 0,
    )
    name: str = Field(default="app", flags=["--name"], description="App name")


class MultiErrorConfig(ConfigsLoader):
    host: str = Field(required=True, flags=["--host"], description="Server host")
    port: int = Field(
        default=8080,
        flags=["--port"],
        description="Port number",
        validator=lambda v: 1 <= v <= 65535,
    )
    name: str = Field(default="app", flags=["--name"], description="App name")


class CrossFieldConfig(ConfigsLoader):
    min_val: int = Field(default=0, flags=["--min"], description="Minimum value")
    max_val: int = Field(
        default=100,
        flags=["--max"],
        description="Maximum value",
        validator=lambda value, config: value > config.min_val,
    )


class CoercionFailureConfig(ConfigsLoader):
    port: int = Field(default=8080, flags=["--port"], description="Port number")
    retries: int = Field(default=3, flags=["--retries"], description="Retry count")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequiredFieldValidation:
    """AC-15.1, AC-15.2: Required field missing raises ValueError; satisfied by any source."""

    def test_required_field_missing_raises_value_error(self):
        """AC-15.1: Required field with no value from any source raises ValueError."""
        with pytest.raises(ValueError, match="host"):
            RequiredFieldConfig.load(args=[])

    def test_required_field_satisfied_by_cli(self):
        """AC-15.2: Required field satisfied by CLI does not raise."""
        config = RequiredFieldConfig.load(args=["--host", "localhost"])
        assert config.host == "localhost"

    def test_required_field_satisfied_by_env(self, monkeypatch):
        """AC-15.2: Required field satisfied by env var does not raise."""
        monkeypatch.setenv("VAL_HOST", "env-host")
        config = RequiredFieldConfig.load(args=[])
        assert config.host == "env-host"

    def test_required_field_satisfied_by_config_file(self, tmp_path):
        """AC-15.2: Required field satisfied by config file does not raise."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('host = "file-host"\n')
        config = RequiredFieldConfig.load(args=[], files=[str(config_file)])
        assert config.host == "file-host"


@pytest.mark.unit
class TestCustomValidators:
    """AC-16.1, AC-16.2: Simple validator receives value, returns bool."""

    def test_validator_receives_value_and_returns_bool(self):
        """AC-16.1: Validator(value) -> bool; False means failure."""
        with pytest.raises(ValueError, match="port"):
            ValidatorConfig.load(args=["--port", "-1"])

    def test_validator_passing_succeeds(self):
        """AC-16.2: Validator returning True allows loading to succeed."""
        config = ValidatorConfig.load(args=["--port", "8080"])
        assert config.port == 8080


@pytest.mark.unit
class TestValidationErrorCollection:
    """AC-17.1: Multiple validation errors collected and reported together."""

    def test_multiple_errors_reported_together(self):
        """AC-17.1: Required missing + validator failure reported in single error."""
        with pytest.raises(ValueError) as exc_info:
            # host is required (missing), port has validator (port=0 fails 1 <= v <= 65535)
            MultiErrorConfig.load(args=["--port", "0"])

        error_message = str(exc_info.value)
        # Should report 2 errors together
        assert "2 error" in error_message
        assert "host" in error_message
        assert "port" in error_message

    def test_error_format_matches_spec(self):
        """AC-17.1: Error format is 'Configuration validation failed with N error(s):\\n  * ...'."""
        with pytest.raises(ValueError) as exc_info:
            MultiErrorConfig.load(args=["--port", "0"])

        error_message = str(exc_info.value)
        assert "Configuration validation failed with" in error_message
        assert "error(s):" in error_message
        assert "  * " in error_message


@pytest.mark.unit
class TestValidationTiming:
    """AC-18.1: Validation runs after all sources applied."""

    def test_validator_sees_final_resolved_value(self, tmp_path):
        """AC-18.1: Validator sees CLI value (final resolved), not config file value."""
        config_file = tmp_path / "config.toml"
        # File has invalid value (port = -1), but CLI overrides with valid value
        config_file.write_text("port = -1\n")
        # CLI provides a valid value; validator should see the CLI value (100), not file value (-1)
        config = ValidatorConfig.load(args=["--port", "100"], files=[str(config_file)])
        assert config.port == 100


@pytest.mark.unit
class TestCrossFieldValidation:
    """AC-19.1, AC-19.2: Cross-field validator receives (value, config)."""

    def test_cross_field_validator_failure(self):
        """AC-19.1: max_val=5, min_val=10 fails cross-field validation."""
        with pytest.raises(ValueError, match="max_val"):
            CrossFieldConfig.load(args=["--min", "10", "--max", "5"])

    def test_cross_field_validator_success(self):
        """AC-19.2: max_val=10, min_val=5 passes cross-field validation."""
        config = CrossFieldConfig.load(args=["--min", "5", "--max", "10"])
        assert config.max_val == 10
        assert config.min_val == 5


@pytest.mark.unit
class TestTypeCoercionFailure:
    """FR-41: Type coercion failure collected with other validation errors."""

    def test_coercion_failure_raises_value_error(self):
        """AC-40.1: Non-numeric string for int field raises ValueError."""
        with pytest.raises(ValueError, match="port"):
            CoercionFailureConfig.load(args=["--port", "abc"])

    def test_coercion_failure_collected_with_validation_errors(self):
        """AC-40.2: Coercion error + other validation error reported together."""

        class MixedErrorConfig(ConfigsLoader):
            host: str = Field(required=True, flags=["--host"], description="Host")
            port: int = Field(default=8080, flags=["--port"], description="Port")

        with pytest.raises(ValueError) as exc_info:
            # host is required (missing), port gets non-numeric "abc"
            MixedErrorConfig.load(args=["--port", "abc"])

        error_message = str(exc_info.value)
        assert "2 error" in error_message
        assert "host" in error_message
        assert "port" in error_message

"""Tests for serialization — FR-37.

Covers: --print-config (non-default only), --print-config-verbose (all), TOML format.
"""

import pytest

from configsloader import ConfigsLoader, Field


# ---------------------------------------------------------------------------
# Config class for serialization tests
# ---------------------------------------------------------------------------


class SerializationConfig(ConfigsLoader):
    host: str = Field(
        default="localhost",
        flags=["--host"],
        env="SER_HOST",
        description="Server host",
    )
    port: int = Field(
        default=8080,
        flags=["--port"],
        description="Server port",
    )
    debug: bool = Field(
        default=False,
        flags=["--debug"],
        description="Debug mode",
    )
    name: str = Field(
        default="myapp",
        flags=["--name"],
        description="Application name",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrintConfig:
    """AC-36.1: --print-config outputs only non-default values."""

    def test_print_config_only_non_default_values(self, capsys):
        """AC-36.1: --print-config shows only fields changed from default."""
        with pytest.raises(SystemExit):
            SerializationConfig.load(args=["--host", "prod-server", "--print-config"])

        captured = capsys.readouterr()
        output = captured.out
        # host was changed — should appear
        assert "host" in output
        assert "prod-server" in output
        # port, debug, name were not changed — should NOT appear
        assert "port" not in output
        assert "debug" not in output
        assert "name" not in output

    def test_print_config_raises_system_exit(self):
        """AC-36.1: --print-config exits after printing."""
        with pytest.raises(SystemExit):
            SerializationConfig.load(args=["--print-config"])


@pytest.mark.unit
class TestPrintConfigVerbose:
    """AC-36.2: --print-config-verbose outputs all values."""

    def test_print_config_verbose_shows_all_values(self, capsys):
        """AC-36.2: --print-config-verbose shows all field values."""
        with pytest.raises(SystemExit):
            SerializationConfig.load(args=["--host", "prod-server", "--print-config-verbose"])

        captured = capsys.readouterr()
        output = captured.out
        # All fields should appear
        assert "host" in output
        assert "prod-server" in output
        assert "port" in output
        assert "8080" in output
        assert "debug" in output
        assert "name" in output
        assert "myapp" in output

    def test_print_config_verbose_raises_system_exit(self):
        """AC-36.2: --print-config-verbose exits after printing."""
        with pytest.raises(SystemExit):
            SerializationConfig.load(args=["--print-config-verbose"])


@pytest.mark.unit
class TestPrintConfigTomlFormat:
    """Output is valid TOML format."""

    def test_output_is_valid_toml(self, capsys):
        """Output from --print-config-verbose is parseable as TOML."""
        import tomllib

        with pytest.raises(SystemExit):
            SerializationConfig.load(args=["--host", "prod-server", "--print-config-verbose"])

        captured = capsys.readouterr()
        output = captured.out
        # Should be parseable as valid TOML
        parsed = tomllib.loads(output)
        assert parsed["host"] == "prod-server"
        assert parsed["port"] == 8080

    def test_string_values_are_quoted_in_toml(self, capsys):
        """String values in TOML output are properly quoted."""
        with pytest.raises(SystemExit):
            SerializationConfig.load(args=["--host", "prod-server", "--print-config-verbose"])

        captured = capsys.readouterr()
        output = captured.out
        # TOML string values should be quoted
        assert '"prod-server"' in output or "'prod-server'" in output

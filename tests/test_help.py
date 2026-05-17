"""Tests for help output — FR-20 through FR-26.

Covers: --help modes, colored output, per-field format, section grouping.
"""

import os
import sys

import pytest

from configsloader import ConfigsLoader, Field


# ---------------------------------------------------------------------------
# Config classes used across help tests
# ---------------------------------------------------------------------------


class HelpConfig(ConfigsLoader):
    host: str = Field(
        default="localhost",
        flags=["--host", "-H"],
        description="Server host",
        required=True,
        section="server",
    )
    port: int = Field(
        default=8080,
        flags=["--port", "-p"],
        description="Server port",
        section="server",
    )
    model: str = Field(
        default="gemma4",
        flags=["--model", "-m"],
        description="LLM model to use",
        section="provider",
    )
    verbose: bool = Field(
        default=False,
        flags=["--verbose", "-v"],
        description="Enable verbose output",
        section="logging",
    )


class NestedHelpConfig(ConfigsLoader):
    """Config with nested groups for hierarchy tree test."""

    db_host: str = Field(
        default="localhost",
        flags=["--backend.db.host"],
        description="Database host",
        section="backend.db",
    )
    db_port: int = Field(
        default=5432,
        flags=["--backend.db.port"],
        description="Database port",
        section="backend.db",
    )
    cache_host: str = Field(
        default="localhost",
        flags=["--backend.cache.host"],
        description="Cache host",
        section="backend.cache",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHelpExitBehavior:
    """AC-20.1: --help exits with SystemExit(0)."""

    def test_help_flag_exits_with_code_zero(self):
        """AC-20.1: --help raises SystemExit(0)."""
        with pytest.raises(SystemExit) as exc_info:
            HelpConfig.load(args=["--help"])
        assert exc_info.value.code == 0

    def test_short_help_flag_exits_with_code_zero(self):
        """AC-20.1: -h raises SystemExit(0)."""
        with pytest.raises(SystemExit) as exc_info:
            HelpConfig.load(args=["-h"])
        assert exc_info.value.code == 0


@pytest.mark.unit
class TestHelpAllMode:
    """AC-20.2: --help all shows all fields."""

    def test_help_all_shows_all_fields(self, capsys):
        """AC-20.2: --help all displays every declared field."""
        with pytest.raises(SystemExit):
            HelpConfig.load(args=["--help", "all"])

        captured = capsys.readouterr()
        output = captured.out
        assert "--host" in output
        assert "--port" in output
        assert "--model" in output
        assert "--verbose" in output


@pytest.mark.unit
class TestHelpRequiredMode:
    """AC-20.3: --help required shows only required fields."""

    def test_help_required_shows_only_required(self, capsys):
        """AC-20.3: --help required displays only fields with required=True."""
        with pytest.raises(SystemExit):
            HelpConfig.load(args=["--help", "required"])

        captured = capsys.readouterr()
        output = captured.out
        # host is required
        assert "--host" in output
        # port, model, verbose are not required - should not appear
        assert "--port" not in output
        assert "--model" not in output
        assert "--verbose" not in output


@pytest.mark.unit
class TestHelpGroupMode:
    """AC-20.4: --help <group> shows only that group."""

    def test_help_group_shows_only_group_fields(self, capsys):
        """AC-20.4: --help server shows only server section fields."""
        with pytest.raises(SystemExit):
            HelpConfig.load(args=["--help", "server"])

        captured = capsys.readouterr()
        output = captured.out
        assert "--host" in output
        assert "--port" in output
        # Fields from other groups should not appear
        assert "--model" not in output
        assert "--verbose" not in output


@pytest.mark.unit
class TestHelpGroupsMode:
    """AC-20.6: --help groups shows hierarchy tree."""

    def test_help_groups_shows_hierarchy_tree(self, capsys):
        """AC-20.6: --help groups displays group hierarchy tree."""
        with pytest.raises(SystemExit):
            NestedHelpConfig.load(args=["--help", "groups"])

        captured = capsys.readouterr()
        output = captured.out
        # Should show group hierarchy
        assert "backend" in output
        assert "db" in output
        assert "cache" in output


@pytest.mark.unit
class TestHelpColoredOutput:
    """AC-21.1, AC-21.2: ANSI codes when enabled, none when disabled."""

    def test_colored_output_contains_ansi_codes(self, capsys, monkeypatch):
        """AC-21.1: When colors enabled, output contains ANSI escape codes."""
        # Ensure colors are enabled (remove NO_COLOR if set)
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")

        with pytest.raises(SystemExit):
            HelpConfig.load(args=["--help", "all"])

        captured = capsys.readouterr()
        output = captured.out
        # ANSI escape codes start with \033[ or \x1b[
        assert "\033[" in output or "\x1b[" in output

    def test_no_ansi_codes_when_colors_disabled(self, capsys, monkeypatch):
        """AC-21.2: When NO_COLOR=1, no ANSI escape codes in output."""
        monkeypatch.setenv("NO_COLOR", "1")

        with pytest.raises(SystemExit):
            HelpConfig.load(args=["--help", "all"])

        captured = capsys.readouterr()
        output = captured.out
        assert "\033[" not in output
        assert "\x1b[" not in output


@pytest.mark.unit
class TestHelpFieldFormat:
    """AC-22.1, AC-22.2: Per-field format shows flags, type, description, default."""

    def test_field_displays_flags_type_description_default(self, capsys, monkeypatch):
        """AC-22.1: Each field shows flags, type, description, default."""
        monkeypatch.setenv("NO_COLOR", "1")

        with pytest.raises(SystemExit):
            HelpConfig.load(args=["--help", "all"])

        captured = capsys.readouterr()
        output = captured.out
        # Check host field format components
        assert "--host" in output
        assert "-H" in output
        assert "string" in output
        assert "Server host" in output
        assert 'default: "localhost"' in output

    def test_required_fields_show_required_tag(self, capsys, monkeypatch):
        """AC-22.2: Required fields show [Required] tag in output."""
        monkeypatch.setenv("NO_COLOR", "1")

        with pytest.raises(SystemExit):
            HelpConfig.load(args=["--help", "all"])

        captured = capsys.readouterr()
        output = captured.out
        # The host field is required — should show [Required] marker
        assert "[Required]" in output


@pytest.mark.unit
class TestHelpSectionGrouping:
    """AC-25.1: Section grouping in output."""

    def test_fields_grouped_by_section(self, capsys, monkeypatch):
        """AC-25.1: Help output groups fields by section with headers."""
        monkeypatch.setenv("NO_COLOR", "1")

        with pytest.raises(SystemExit):
            HelpConfig.load(args=["--help", "all"])

        captured = capsys.readouterr()
        output = captured.out
        # Section headers should appear
        assert "server" in output.lower() or "Server" in output
        assert "provider" in output.lower() or "Provider" in output
        assert "logging" in output.lower() or "Logging" in output


@pytest.mark.unit
class TestHelpFormatTypeName:
    """Tests for _format_type_name edge cases."""

    def test_format_type_name_without_name_attr(self):
        """help.py:61 — type without __name__ uses str() fallback."""
        from configsloader.help import _format_type_name

        class FakeType:
            """Object without __name__ attribute."""
            def __str__(self):
                return "custom_type"

        # Remove __name__ if it has one (classes get __name__ from type)
        obj = FakeType()
        # Instances don't have __name__ by default
        assert not hasattr(obj, "__name__")
        result = _format_type_name(obj)
        assert "custom_type" in result

    def test_format_default_none_returns_empty(self):
        """help.py:67 — None default returns empty string."""
        from configsloader.help import _format_default
        result = _format_default(None, str)
        assert result == ""


@pytest.mark.unit
class TestHelpAutoColors:
    """Tests for color auto-detection."""

    def test_colors_auto_detect_non_tty(self, monkeypatch):
        """help.py:191->194 — use_colors=None triggers auto-detect."""
        from configsloader.help import generate_help
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        # generate_help with use_colors=None triggers _should_use_colors()
        result = generate_help(HelpConfig._fields, {"host": str, "port": int, "model": str, "verbose": bool}, mode="navigation", use_colors=None)
        assert "Usage:" in result


@pytest.mark.unit
class TestHelpFieldWithNoneDefault:
    """Tests for field with default=None in help output (no default string)."""

    def test_field_with_none_default_omits_default_str(self, monkeypatch):
        """help.py:127->130 — field with default=None skips default_str formatting."""
        from configsloader.help import generate_help
        from configsloader import ConfigsLoader, Field

        class NoneDefaultConfig(ConfigsLoader):
            token: str = Field(required=True, flags=["--token"], description="Auth token")

        monkeypatch.setenv("NO_COLOR", "1")
        result = generate_help(
            NoneDefaultConfig._fields,
            {"token": str},
            mode="all",
            use_colors=False,
        )
        assert "--token" in result
        assert "default:" not in result


@pytest.mark.unit
class TestHelpGroupNoMatch:
    """Tests for --help <group> when group has no matching fields."""

    def test_help_group_with_no_matching_fields(self, monkeypatch):
        """help.py:308->314 — group name with no matching fields produces no field lines."""
        from configsloader.help import generate_help
        monkeypatch.setenv("NO_COLOR", "1")
        result = generate_help(
            HelpConfig._fields,
            {"host": str, "port": int, "model": str, "verbose": bool},
            mode="nonexistent_group",
            use_colors=False,
        )
        # Should have usage line but no field lines (no matching group)
        assert "Usage:" in result
        assert "--host" not in result

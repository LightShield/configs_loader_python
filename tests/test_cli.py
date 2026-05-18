"""Unit tests for CLI source module (sources/cli.py).

Covers: FR-03, FR-33-36, FR-43, FR-45.
"""

from __future__ import annotations

import pytest

from configsloader.sources.cli import parse_cli

# ---------------------------------------------------------------------------
# Helpers — minimal field descriptors for driving parse_cli
# ---------------------------------------------------------------------------


def _make_field(name, flags, field_type=str, is_bool=False):
    """Create a minimal field-info dict expected by parse_cli."""
    return {
        "name": name,
        "flags": flags,
        "type": field_type,
        "is_bool": is_bool,
    }


# ---------------------------------------------------------------------------
# FR-03: CLI Flag Parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCLIFlagParsing:
    """Tests for basic CLI flag parsing (AC-03.1, AC-03.2)."""

    def test_long_flag_parsed(self):
        """AC-03.1: Long flag --model gemma4 is parsed correctly."""
        fields = [_make_field("model", ["--model", "-m"])]
        result = parse_cli(["--model", "gemma4"], fields)
        assert result["model"] == "gemma4"

    def test_short_flag_parsed(self):
        """AC-03.2: Short flag -m gemma4 is parsed correctly."""
        fields = [_make_field("model", ["--model", "-m"])]
        result = parse_cli(["-m", "gemma4"], fields)
        assert result["model"] == "gemma4"


# ---------------------------------------------------------------------------
# FR-45: Boolean Switch Behavior
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBooleanSwitchBehavior:
    """Tests for bool flags acting as switches (AC-44.1, AC-44.2, AC-44.3)."""

    def test_bool_flag_as_switch_no_value(self):
        """AC-44.1: --verbose alone (no following value) resolves to True."""
        fields = [_make_field("verbose", ["--verbose"], field_type=bool, is_bool=True)]
        result = parse_cli(["--verbose"], fields)
        assert result["verbose"] is True

    def test_bool_flag_with_explicit_false(self):
        """AC-44.2: --verbose false resolves to False."""
        fields = [_make_field("verbose", ["--verbose"], field_type=bool, is_bool=True)]
        result = parse_cli(["--verbose", "false"], fields)
        assert result["verbose"] is False

    def test_bool_flag_followed_by_another_flag(self):
        """AC-44.3: --verbose --port 8080 treats --verbose as bare switch (True)."""
        fields = [
            _make_field("verbose", ["--verbose"], field_type=bool, is_bool=True),
            _make_field("port", ["--port"], field_type=int),
        ]
        result = parse_cli(["--verbose", "--port", "8080"], fields)
        assert result["verbose"] is True
        assert result["port"] == "8080"


# ---------------------------------------------------------------------------
# FR-43: Repeated CLI Flag Behavior
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRepeatedFlags:
    """Tests for repeated flags — last wins (AC-42.1)."""

    def test_repeated_flag_last_wins(self):
        """AC-42.1: --host first --host second => 'second' wins."""
        fields = [_make_field("host", ["--host"])]
        result = parse_cli(["--host", "first", "--host", "second"], fields)
        assert result["host"] == "second"


# ---------------------------------------------------------------------------
# FR-33: Unknown Flag Handling — Error Mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnknownFlagsErrorMode:
    """Tests for unknown flags in Error mode (AC-33.1, AC-33.3)."""

    def test_unknown_flag_raises_error(self):
        """AC-33.1: Unknown flag in Error mode raises an exception."""
        fields = [_make_field("host", ["--host"])]
        with pytest.raises(Exception) as exc_info:
            parse_cli(["--unknown-flag", "val"], fields, unknown_flags="error")
        assert "--unknown-flag" in str(exc_info.value)

    def test_multiple_unknown_flags_listed_in_error(self):
        """AC-33.3: Multiple unknown flags are all listed in the error message."""
        fields = [_make_field("host", ["--host"])]
        with pytest.raises(Exception) as exc_info:
            parse_cli(
                ["--unknown-one", "val1", "--unknown-two", "val2"],
                fields,
                unknown_flags="error",
            )
        error_msg = str(exc_info.value)
        assert "--unknown-one" in error_msg
        assert "--unknown-two" in error_msg


# ---------------------------------------------------------------------------
# FR-35: Unknown Flag Handling — Warn Mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnknownFlagsWarnMode:
    """Tests for unknown flags in Warn mode (AC-34.1)."""

    def test_unknown_flag_warns_but_succeeds(self, capsys):
        """AC-34.1: Unknown flag in Warn mode prints warning and continues."""
        fields = [_make_field("host", ["--host"])]
        result = parse_cli(["--host", "localhost", "--unknown-flag"], fields, unknown_flags="warn")
        assert result["host"] == "localhost"
        captured = capsys.readouterr()
        assert "--unknown-flag" in captured.err or "--unknown-flag" in captured.out


# ---------------------------------------------------------------------------
# FR-36: Unknown Flag Handling — Ignore Mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnknownFlagsIgnoreMode:
    """Tests for unknown flags in Ignore mode (AC-35.1)."""

    def test_unknown_flag_silently_discarded(self, capsys):
        """AC-35.1: Unknown flag in Ignore mode is silently discarded."""
        fields = [_make_field("host", ["--host"])]
        result = parse_cli(
            ["--host", "localhost", "--unknown-flag"], fields, unknown_flags="ignore"
        )
        assert result["host"] == "localhost"
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


# ---------------------------------------------------------------------------
# FR-38: Reserved Flag Validation (detection at parse time)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReservedFlags:
    """Tests for reserved flag detection."""

    def test_reserved_flag_help_detected(self):
        """Reserved flag --help is detected and rejected if declared by user field."""
        fields = [_make_field("myhelp", ["--help"])]
        with pytest.raises(Exception) as exc_info:
            parse_cli([], fields)
        assert "--help" in str(exc_info.value) or "reserved" in str(exc_info.value).lower()

    def test_reserved_flag_preset_detected(self):
        """Reserved flag --preset is detected and rejected if declared by user field."""
        fields = [_make_field("mypreset", ["--preset"])]
        with pytest.raises(Exception) as exc_info:
            parse_cli([], fields)
        assert "--preset" in str(exc_info.value) or "reserved" in str(exc_info.value).lower()


@pytest.mark.unit
class TestCLIPositionalArgSkipped:
    """Tests for positional arguments (non-flag tokens)."""

    def test_positional_arg_not_a_flag_skipped(self):
        """cli.py:164 — non-flag token that isn't a value for known flag is skipped."""
        fields = [_make_field("host", ["--host"])]
        result = parse_cli(["positional_arg", "--host", "localhost"], fields)
        assert result["host"] == "localhost"


@pytest.mark.unit
class TestCLIBoolFlagExplicitTrueValue:
    """Tests for boolean flag with explicit true value."""

    def test_bool_flag_with_explicit_true(self):
        """cli.py:180 — bool flag with 'true' as next token returns True via BOOL_TRUE_VALUES."""
        fields = [_make_field("verbose", ["--verbose"], field_type=bool, is_bool=True)]
        result = parse_cli(["--verbose", "true"], fields)
        assert result["verbose"] is True

    def test_bool_flag_with_explicit_yes(self):
        """cli.py:180 — bool flag with 'yes' as next token returns True."""
        fields = [_make_field("verbose", ["--verbose"], field_type=bool, is_bool=True)]
        result = parse_cli(["--verbose", "yes"], fields)
        assert result["verbose"] is True

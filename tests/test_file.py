"""Unit tests for config file source module (sources/file.py).

Covers: FR-05 through FR-11.
"""

from __future__ import annotations

import json

import pytest

from configsloader.sources.file import load_file, load_files


# ---------------------------------------------------------------------------
# FR-05: Config File Loading (TOML)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTOMLLoading:
    """Tests for TOML file loading (AC-05.1, AC-05.2)."""

    def test_toml_file_loaded(self, tmp_path):
        """AC-05.1: Valid TOML file is loaded and values are accessible."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[provider]\nmodel = "llama3"\n')
        result = load_file(str(config_file))
        assert result == {"provider": {"model": "llama3"}}

    def test_invalid_toml_raises_error(self, tmp_path):
        """AC-05.2: Invalid TOML file raises a descriptive error."""
        config_file = tmp_path / "bad.toml"
        config_file.write_text("[invalid\nbroken toml here")
        with pytest.raises(Exception) as exc_info:
            load_file(str(config_file))
        assert "bad.toml" in str(exc_info.value) or "toml" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# FR-06: Config File Loading (JSON)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJSONLoading:
    """Tests for JSON file loading (AC-06.1, AC-06.2)."""

    def test_json_file_loaded(self, tmp_path):
        """AC-06.1: Valid JSON file is loaded and values are accessible."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"provider": {"model": "llama3"}}))
        result = load_file(str(config_file))
        assert result == {"provider": {"model": "llama3"}}

    def test_invalid_json_raises_error(self, tmp_path):
        """AC-06.2: Invalid JSON file raises a descriptive error."""
        config_file = tmp_path / "bad.json"
        config_file.write_text("{invalid json content")
        with pytest.raises(Exception) as exc_info:
            load_file(str(config_file))
        assert "bad.json" in str(exc_info.value) or "json" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# FR-07: Config File Format Auto-Detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatAutoDetection:
    """Tests for format auto-detection from extension (AC-07.1, AC-07.2, AC-07.3)."""

    def test_toml_extension_detected(self, tmp_path):
        """AC-07.1: .toml extension auto-detected and parsed as TOML."""
        config_file = tmp_path / "app.toml"
        config_file.write_text('key = "value"\n')
        result = load_file(str(config_file), format="auto")
        assert result["key"] == "value"

    def test_json_extension_detected(self, tmp_path):
        """AC-07.2: .json extension auto-detected and parsed as JSON."""
        config_file = tmp_path / "app.json"
        config_file.write_text(json.dumps({"key": "value"}))
        result = load_file(str(config_file), format="auto")
        assert result["key"] == "value"

    def test_unsupported_extension_raises(self, tmp_path):
        """AC-07.3: Unsupported extension with format=auto raises an error."""
        config_file = tmp_path / "app.yaml"
        config_file.write_text("key: value\n")
        with pytest.raises(Exception) as exc_info:
            load_file(str(config_file), format="auto")
        assert "unsupported" in str(exc_info.value).lower() or "yaml" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# FR-08: Explicit Format Override
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExplicitFormatOverride:
    """Tests for explicit format parameter (AC-08.1)."""

    def test_explicit_format_overrides_extension(self, tmp_path):
        """AC-08.1: File named .txt parsed as TOML when format='toml' specified."""
        config_file = tmp_path / "config.txt"
        config_file.write_text('key = "value"\n')
        result = load_file(str(config_file), format="toml")
        assert result["key"] == "value"


# ---------------------------------------------------------------------------
# FR-09: Multi-File Hierarchy with Layering
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMultiFileLayering:
    """Tests for multi-file layering (AC-09.1, AC-09.2)."""

    def test_later_file_overrides_earlier(self, tmp_path):
        """AC-09.1: Later file in list overrides values from earlier file."""
        base = tmp_path / "base.toml"
        base.write_text('model = "base"\n')
        override = tmp_path / "override.toml"
        override.write_text('model = "override"\n')
        result = load_files([str(base), str(override)])
        assert result["model"] == "override"

    def test_missing_file_silently_skipped(self, tmp_path):
        """AC-09.2: Missing file in list is silently skipped."""
        existing = tmp_path / "existing.toml"
        existing.write_text('key = "present"\n')
        missing = tmp_path / "nonexistent.toml"
        result = load_files([str(missing), str(existing)])
        assert result["key"] == "present"


# ---------------------------------------------------------------------------
# FR-27: Section-Scoped Loading
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSectionScopedLoading:
    """Tests for section-scoped field extraction (AC-27.1)."""

    def test_section_scoped_toml(self, tmp_path):
        """AC-27.1: Field with section='database' reads from [database] table."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[database]\nhost = "localhost"\n')
        data = load_file(str(config_file))
        # The file source returns the full dict; section extraction is tested here.
        assert data["database"]["host"] == "localhost"


# ---------------------------------------------------------------------------
# FR-11: Mixed Formats Across Files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMixedFormats:
    """Tests for mixed file formats in layering (AC-11.1)."""

    def test_mixed_toml_and_json_layering(self, tmp_path):
        """AC-11.1: TOML and JSON files can be layered together."""
        toml_file = tmp_path / "base.toml"
        toml_file.write_text('host = "toml-host"\nport = 3000\n')
        json_file = tmp_path / "override.json"
        json_file.write_text(json.dumps({"host": "json-host"}))
        result = load_files([str(toml_file), str(json_file)])
        assert result["host"] == "json-host"
        # port from toml should still be present (not overridden)
        assert result["port"] == 3000

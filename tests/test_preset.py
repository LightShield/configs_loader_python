"""Unit tests for preset source module (sources/preset.py).

Covers: FR-30, FR-31.
"""

from __future__ import annotations

import json

import pytest

from configsloader.sources.preset import load_preset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_field(name, flags, field_type=str):
    """Create a minimal field-info dict expected by load_preset."""
    return {
        "name": name,
        "flags": flags,
        "type": field_type,
    }


# ---------------------------------------------------------------------------
# FR-30: Preset File — Reserved Flag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPresetLoading:
    """Tests for preset file loading (AC-30.1, AC-30.3, AC-30.4, AC-30.5)."""

    def test_preset_file_loaded(self, tmp_path):
        """AC-30.1: Preset file loaded via --preset flag provides values."""
        preset_file = tmp_path / "production.toml"
        preset_file.write_text('host = "prod-server"\n')
        fields = [_make_field("host", ["--host"])]
        result = load_preset(str(preset_file), fields)
        assert result["host"] == "prod-server"

    def test_preset_overridden_by_cli(self, tmp_path):
        """AC-30.2: CLI values override preset values (tested at integration level,
        but preset source itself just returns its values)."""
        preset_file = tmp_path / "production.toml"
        preset_file.write_text('host = "prod-server"\n')
        fields = [_make_field("host", ["--host"])]
        result = load_preset(str(preset_file), fields)
        # Preset returns its value; CLI override is handled by resolution order
        assert result["host"] == "prod-server"

    def test_missing_preset_file_raises_error(self, tmp_path):
        """AC-30.3: Missing preset file raises an error."""
        missing_path = str(tmp_path / "nonexistent.toml")
        fields = [_make_field("host", ["--host"])]
        with pytest.raises(Exception) as exc_info:
            load_preset(missing_path, fields)
        assert (
            "nonexistent" in str(exc_info.value).lower()
            or "not found" in str(exc_info.value).lower()
        )

    def test_preset_auto_detects_json_format(self, tmp_path):
        """AC-30.4: Preset file format auto-detected from extension (.json)."""
        preset_file = tmp_path / "dev.json"
        preset_file.write_text(json.dumps({"host": "dev-host"}))
        fields = [_make_field("host", ["--host"])]
        result = load_preset(str(preset_file), fields)
        assert result["host"] == "dev-host"

    def test_preset_key_uses_first_flag_stripped(self, tmp_path):
        """AC-30.5: Preset key lookup uses first flag stripped of dashes.

        Field with flags=['--backend.db.host', '-H'] maps to preset key 'backend.db.host'.
        """
        preset_file = tmp_path / "preset.toml"
        # Dotted key in TOML: backend.db.host = "preset-db"
        preset_file.write_text('"backend.db.host" = "preset-db"\n')
        fields = [_make_field("db_host", ["--backend.db.host", "-H"])]
        result = load_preset(str(preset_file), fields)
        assert result["db_host"] == "preset-db"


# ---------------------------------------------------------------------------
# FR-31: Preset File Resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPresetResolution:
    """Tests for preset directory resolution."""

    def test_preset_resolved_from_directory(self, tmp_path):
        """Preset name resolved by appending to preset_dir with extension."""
        preset_dir = tmp_path / "presets"
        preset_dir.mkdir()
        preset_file = preset_dir / "dev.toml"
        preset_file.write_text('host = "dev-host"\n')
        fields = [_make_field("host", ["--host"])]
        result = load_preset("dev", fields, preset_dir=str(preset_dir))
        assert result["host"] == "dev-host"

    def test_preset_resolved_from_directory_json(self, tmp_path):
        """preset.py:49-56 — preset name resolved with .json extension."""
        preset_dir = tmp_path / "presets"
        preset_dir.mkdir()
        preset_file = preset_dir / "staging.json"
        preset_file.write_text('{"host": "staging-host"}')
        fields = [_make_field("host", ["--host"])]
        result = load_preset("staging", fields, preset_dir=str(preset_dir))
        assert result["host"] == "staging-host"

    def test_preset_resolved_from_directory_bare_name(self, tmp_path):
        """preset.py:55-56 — preset resolved as bare file in directory (no extension)."""
        from configsloader.sources.preset import _resolve_preset_path

        preset_dir = tmp_path / "presets"
        preset_dir.mkdir()
        # Create a file named "custom.toml" to NOT match, and a bare file "custom"
        # The code tries .toml, .json, then bare name in order
        # So we need the bare name to be the only match
        bare_file = preset_dir / "custom"
        bare_file.write_text('key = "value"\n')
        # Calling _resolve_preset_path directly to test the bare path resolution
        result = _resolve_preset_path("custom", preset_dir=str(preset_dir))
        assert result == str(bare_file)

    def test_preset_path_traversal_raises(self, tmp_path):
        """preset.py:77 — path traversal attempt raises ValueError."""

        from configsloader.sources.preset import _check_path_traversal

        preset_dir = tmp_path / "presets"
        preset_dir.mkdir()
        outside = tmp_path / "outside.toml"
        outside.write_text('host = "evil"\n')
        with pytest.raises(ValueError, match="escapes preset directory"):
            _check_path_traversal(outside, preset_dir.resolve(), "../outside")

    def test_preset_not_found_with_preset_dir(self, tmp_path):
        """preset.py:49-56 — preset not found in directory raises FileNotFoundError."""
        preset_dir = tmp_path / "presets"
        preset_dir.mkdir()
        fields = [_make_field("host", ["--host"])]
        with pytest.raises(FileNotFoundError, match="searched in"):
            load_preset("nonexistent", fields, preset_dir=str(preset_dir))


@pytest.mark.unit
class TestPresetKeyMatchByFlag:
    """Tests for preset key matching via flags."""

    def test_preset_key_matched_by_flag_stripped(self, tmp_path):
        """preset.py:112->106 — field key not in data, but flag-stripped key is."""
        preset_file = tmp_path / "prod.toml"
        preset_file.write_text('model = "from-preset"\n')
        fields = [_make_field("model_name", ["--model"])]
        result = load_preset(str(preset_file), fields)
        assert result["model_name"] == "from-preset"

    def test_preset_key_not_matched_skipped(self, tmp_path):
        """preset.py:112->106 — field with no matching key in preset data is skipped."""
        preset_file = tmp_path / "prod.toml"
        preset_file.write_text('other_key = "value"\n')
        fields = [_make_field("host", ["--host"])]
        result = load_preset(str(preset_file), fields)
        assert "host" not in result

    def test_field_with_no_flags_skips_flag_lookup(self, tmp_path):
        """preset.py:112->106 — field with empty flags list skips flag-based lookup."""
        preset_file = tmp_path / "prod.toml"
        preset_file.write_text('other = "value"\n')
        fields = [{"name": "host", "flags": [], "type": str}]
        result = load_preset(str(preset_file), fields)
        assert "host" not in result

"""Unit tests for environment variable source module (sources/env.py).

Covers: FR-04.
"""

from __future__ import annotations

import pytest

from configsloader.sources.env import load_env

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_field(name, env_var, field_type=str):
    """Create a minimal field-info dict expected by load_env."""
    return {
        "name": name,
        "env": env_var,
        "type": field_type,
    }


# ---------------------------------------------------------------------------
# FR-04: Environment Variable Lookup
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnvSource:
    """Tests for env var lookup (AC-04.1, AC-04.2)."""

    def test_env_var_overrides_default(self, monkeypatch):
        """AC-04.1: Present env var provides value for the field."""
        monkeypatch.setenv("APP_HOST", "envhost")
        fields = [_make_field("host", "APP_HOST")]
        result = load_env(fields)
        assert result["host"] == "envhost"

    def test_missing_env_var_no_value(self, monkeypatch):
        """AC-04.2: Missing env var produces no entry from this source."""
        monkeypatch.delenv("APP_HOST", raising=False)
        fields = [_make_field("host", "APP_HOST")]
        result = load_env(fields)
        assert "host" not in result

    def test_env_var_returns_string_for_int_field(self, monkeypatch):
        """Env var returns raw string '42' (coercion handled elsewhere)."""
        monkeypatch.setenv("APP_PORT", "42")
        fields = [_make_field("port", "APP_PORT", field_type=int)]
        result = load_env(fields)
        # The env source should return the raw string; type coercion is separate.
        assert result["port"] == "42"

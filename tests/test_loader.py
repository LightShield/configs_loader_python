"""Tests for E2E loader — FR-02, FR-39, FR-40.

Covers: resolution order (CLI > env > preset > file > default), is_set tracking,
zero-config usage, full priority chain.
"""

import os
from pathlib import Path

import pytest

from configsloader import ConfigsLoader, Field


# ---------------------------------------------------------------------------
# Config classes for loader tests
# ---------------------------------------------------------------------------


class FullResolutionConfig(ConfigsLoader):
    model: str = Field(
        default="def_val",
        flags=["--model", "-m"],
        env="LOADER_MODEL",
        section="provider",
        description="Model to use",
    )
    host: str = Field(
        default="def_host",
        flags=["--host"],
        env="LOADER_HOST",
        description="Server host",
    )


class IsSetConfig(ConfigsLoader):
    host: str = Field(
        default="localhost",
        flags=["--host"],
        env="ISSET_HOST",
        description="Server host",
    )
    port: int = Field(
        default=8080,
        flags=["--port"],
        description="Server port",
    )
    name: str = Field(
        default="myapp",
        flags=["--name"],
        description="Application name",
    )


class ZeroConfig(ConfigsLoader):
    host: str = Field(default="localhost", flags=["--host"], description="Host")
    port: int = Field(default=8080, flags=["--port"], description="Port")
    debug: bool = Field(default=False, flags=["--debug"], description="Debug mode")


class PresetConfig(ConfigsLoader):
    model: str = Field(
        default="def_val",
        flags=["--model"],
        env="PRESET_MODEL",
        description="Model",
    )
    host: str = Field(
        default="def_host",
        flags=["--host"],
        env="PRESET_HOST",
        description="Host",
    )

    class Meta:
        preset_dir = "./presets"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestResolutionOrder:
    """AC-02.1 through AC-02.4: CLI > env > preset > file > default."""

    def test_cli_wins_over_all(self, tmp_path, monkeypatch):
        """AC-02.1: CLI value has highest precedence."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[provider]\nmodel = "file_val"\n')
        monkeypatch.setenv("LOADER_MODEL", "env_val")

        config = FullResolutionConfig.load(
            args=["--model", "cli_val"],
            files=[str(config_file)],
        )
        assert config.model == "cli_val"

    def test_env_wins_over_file_and_default(self, tmp_path, monkeypatch):
        """AC-02.2: Env var wins when no CLI flag present."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[provider]\nmodel = "file_val"\n')
        monkeypatch.setenv("LOADER_MODEL", "env_val")

        config = FullResolutionConfig.load(args=[], files=[str(config_file)])
        assert config.model == "env_val"

    def test_preset_wins_over_file_and_default(self, tmp_path, monkeypatch):
        """AC-02.3: Preset wins when no CLI or env present."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[provider]\nmodel = "file_val"\n')
        preset_file = tmp_path / "prod.toml"
        preset_file.write_text('model = "preset_val"\n')
        monkeypatch.delenv("LOADER_MODEL", raising=False)

        config = FullResolutionConfig.load(
            args=["--preset", str(preset_file)],
            files=[str(config_file)],
        )
        assert config.model == "preset_val"

    def test_file_wins_over_default(self, tmp_path, monkeypatch):
        """AC-02.4: Config file wins when no CLI, env, or preset present."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[provider]\nmodel = "file_val"\n')
        monkeypatch.delenv("LOADER_MODEL", raising=False)

        config = FullResolutionConfig.load(args=[], files=[str(config_file)])
        assert config.model == "file_val"

    def test_default_used_when_no_other_source(self, monkeypatch):
        """AC-02.4: Default is used when no source provides a value."""
        monkeypatch.delenv("LOADER_MODEL", raising=False)
        monkeypatch.delenv("LOADER_HOST", raising=False)

        config = FullResolutionConfig.load(args=[])
        assert config.model == "def_val"
        assert config.host == "def_host"

    def test_full_priority_chain(self, tmp_path, monkeypatch):
        """Full chain: multiple sources, CLI always wins."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[provider]\nmodel = "file_val"\n')
        preset_file = tmp_path / "preset.toml"
        preset_file.write_text('model = "preset_val"\nhost = "preset_host"\n')
        monkeypatch.setenv("LOADER_MODEL", "env_val")
        monkeypatch.setenv("LOADER_HOST", "env_host")

        config = FullResolutionConfig.load(
            args=["--model", "cli_val", "--preset", str(preset_file)],
            files=[str(config_file)],
        )
        # CLI wins for model
        assert config.model == "cli_val"
        # env wins for host (no CLI for host)
        assert config.host == "env_host"


@pytest.mark.integration
class TestIsSet:
    """AC-38.1, AC-38.2: is_set tracking."""

    def test_is_set_false_when_using_default(self):
        """AC-38.1: is_set returns False when field uses its default value."""
        config = IsSetConfig.load(args=[])
        assert config.is_set("host") is False
        assert config.is_set("port") is False
        assert config.is_set("name") is False

    def test_is_set_true_when_explicitly_set_by_cli(self):
        """AC-38.2: is_set returns True when field explicitly set via CLI."""
        config = IsSetConfig.load(args=["--host", "myhost"])
        assert config.is_set("host") is True
        assert config.is_set("port") is False

    def test_is_set_true_when_set_by_env(self, monkeypatch):
        """AC-38.2: is_set returns True when field explicitly set via env var."""
        monkeypatch.setenv("ISSET_HOST", "env-host")
        config = IsSetConfig.load(args=[])
        assert config.is_set("host") is True

    def test_is_set_true_even_when_value_matches_default(self, tmp_path):
        """AC-38.2: is_set is True even when explicitly set value matches default."""
        config_file = tmp_path / "config.toml"
        # Explicitly set to same value as default
        config_file.write_text('host = "localhost"\n')
        config = IsSetConfig.load(args=[], files=[str(config_file)])
        assert config.is_set("host") is True

    def test_is_set_true_when_set_by_config_file(self, tmp_path):
        """AC-38.2: is_set returns True when field set via config file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('host = "file-host"\n')
        config = IsSetConfig.load(args=[], files=[str(config_file)])
        assert config.is_set("host") is True
        assert config.is_set("port") is False


@pytest.mark.e2e
class TestZeroConfig:
    """AC-39.1: Zero-config usage — .load() with no args uses defaults."""

    def test_load_with_no_args_uses_defaults(self):
        """AC-39.1: .load() with no arguments resolves all fields to defaults."""
        config = ZeroConfig.load(args=[])
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.debug is False

    def test_zero_config_no_files_no_env(self, monkeypatch):
        """AC-39.1: No config files needed; loading succeeds with just defaults."""
        # Ensure no relevant env vars are set
        monkeypatch.delenv("LOADER_MODEL", raising=False)
        monkeypatch.delenv("LOADER_HOST", raising=False)
        config = FullResolutionConfig.load(args=[])
        assert config.model == "def_val"
        assert config.host == "def_host"

    def test_zero_config_with_env_only(self, monkeypatch):
        """AC-39.2: Zero-config with env var resolves from env."""
        monkeypatch.setenv("ISSET_HOST", "env-host")
        config = IsSetConfig.load(args=[])
        assert config.host == "env-host"


@pytest.mark.e2e
class TestPresetIntegration:
    """Preset file in resolution chain."""

    def test_preset_applied_between_env_and_file(self, tmp_path, monkeypatch):
        """Preset is between env and file in priority."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('model = "file_val"\nhost = "file_host"\n')
        preset_file = tmp_path / "preset.toml"
        preset_file.write_text('model = "preset_val"\nhost = "preset_host"\n')
        monkeypatch.delenv("PRESET_MODEL", raising=False)
        monkeypatch.delenv("PRESET_HOST", raising=False)

        config = PresetConfig.load(
            args=["--preset", str(preset_file)],
            files=[str(config_file)],
        )
        # Preset wins over file (no CLI or env for these)
        assert config.model == "preset_val"
        assert config.host == "preset_host"

    def test_cli_wins_over_preset(self, tmp_path, monkeypatch):
        """CLI always wins over preset."""
        preset_file = tmp_path / "preset.toml"
        preset_file.write_text('model = "preset_val"\n')
        monkeypatch.delenv("PRESET_MODEL", raising=False)

        config = PresetConfig.load(
            args=["--model", "cli_val", "--preset", str(preset_file)],
        )
        assert config.model == "cli_val"


@pytest.mark.unit
class TestLoaderDefaultArgs:
    """Tests for loader.py lines that use sys.argv fallback."""

    def test_load_uses_sys_argv_when_args_is_none(self, monkeypatch):
        """loader.py:300 — args=None defaults to sys.argv[1:]."""
        import sys
        monkeypatch.setattr(sys, "argv", ["prog", "--host", "from-argv"])
        config = IsSetConfig.load(args=None)
        assert config.host == "from-argv"


@pytest.mark.unit
class TestLoaderCoercionErrorInNested:
    """Tests for loader.py:201-202 — coercion errors in nested loading."""

    def test_nested_coercion_error_raises(self):
        """loader.py:201-202 — coercion error inside nested config raises ValueError."""
        from configsloader import ConfigsLoader, Field

        class Parent(ConfigsLoader):
            class child(ConfigsLoader):
                port: int = Field(default=8080, flags=["--child.port"])

        with pytest.raises(ValueError, match="port"):
            Parent.load(args=["--child.port", "not_a_number"])


@pytest.mark.unit
class TestLoaderFileKeyResolution:
    """Tests for loader.py:242, 244, 248 — _get_file_key logic."""

    def test_file_key_strips_section_prefix_from_flag(self, tmp_path):
        """loader.py:242, 244, 248 — when field has section and flags, derive local key."""
        from configsloader import ConfigsLoader, Field

        class SectionFlagConfig(ConfigsLoader):
            db_host: str = Field(
                default="localhost",
                flags=["--backend.db.host"],
                section="backend.db",
            )

        config_file = tmp_path / "config.toml"
        config_file.write_text('[backend.db]\nhost = "from-file"\n')
        config = SectionFlagConfig.load(args=[], files=[str(config_file)])
        assert config.db_host == "from-file"


@pytest.mark.unit
class TestLoaderResolveValueFileFallback:
    """Tests for loader.py:557 — file_key != name fallback."""

    def test_file_value_found_by_name_when_file_key_misses(self, tmp_path):
        """loader.py:557 — when file_key doesn't match but name does in file data."""
        from configsloader import ConfigsLoader, Field
        from configsloader.loader import _resolve_value
        from configsloader.field import FieldDescriptor

        # Simulate: file_key is "something" but name is "host" and file has "host"
        descriptor = FieldDescriptor(default="default_val")
        sources = {
            "cli": {},
            "env": {},
            "preset": {},
            "file": {"host": "file_value"},
        }
        value, was_set = _resolve_value("host", descriptor, sources, file_key="nonexistent_key")
        assert value == "file_value"
        assert was_set is True


@pytest.mark.unit
class TestNestedFieldResolutionFromEnv:
    """Tests for loader.py:242 — nested field resolved from env source."""

    def test_nested_field_resolved_from_env(self, monkeypatch):
        """loader.py:242 — nested field resolved from env variable."""
        from configsloader import ConfigsLoader, Field

        class Parent(ConfigsLoader):
            class child(ConfigsLoader):
                host: str = Field(default="localhost", flags=["--child.host"], env="CHILD_HOST")

        monkeypatch.setenv("CHILD_HOST", "env-host")
        config = Parent.load(args=[])
        assert config.child.host == "env-host"


@pytest.mark.unit
class TestNestedFieldResolutionFromPreset:
    """Tests for loader.py:244 — nested field resolved from preset source."""

    def test_nested_field_resolved_from_preset(self, tmp_path, monkeypatch):
        """loader.py:244 — nested field resolved from preset source."""
        from configsloader import ConfigsLoader, Field

        class Parent(ConfigsLoader):
            class child(ConfigsLoader):
                host: str = Field(default="localhost", flags=["--child.host"])

        preset_file = tmp_path / "preset.toml"
        preset_file.write_text('"child.host" = "preset-host"\n')
        monkeypatch.delenv("CHILD_HOST", raising=False)
        config = Parent.load(args=["--preset", str(preset_file)])
        assert config.child.host == "preset-host"


@pytest.mark.unit
class TestNestedFieldResolutionFromFile:
    """Tests for loader.py:248 — nested field resolved from config file."""

    def test_nested_field_resolved_from_file(self, tmp_path):
        """loader.py:248 — nested field resolved from config file section."""
        from configsloader import ConfigsLoader, Field

        class Parent(ConfigsLoader):
            class child(ConfigsLoader):
                host: str = Field(default="localhost", flags=["--child.host"])

        config_file = tmp_path / "config.toml"
        config_file.write_text('[child]\nhost = "file-host"\n')
        config = Parent.load(args=[], files=[str(config_file)])
        assert config.child.host == "file-host"

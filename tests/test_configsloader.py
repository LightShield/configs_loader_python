"""Tests for configsloader — verifies API contract."""

import os
from enum import Enum
from pathlib import Path

import pytest

from configsloader import ConfigsLoader, Field

pytestmark = pytest.mark.unit


class SimpleConfig(ConfigsLoader):
    name: str = Field(default="test", flags=["--name", "-n"], description="App name")
    port: int = Field(default=8080, flags=["--port", "-p"], description="Port number")
    debug: bool = Field(default=False, flags=["--debug", "-d"], description="Debug mode")


class EnvConfig(ConfigsLoader):
    api_key: str = Field(default="", env="MY_API_KEY", description="API key")
    timeout: int = Field(default=30, env="MY_TIMEOUT", flags=["--timeout"])


class RequiredConfig(ConfigsLoader):
    input_file: str = Field(required=True, flags=["--input"], description="Input file")
    output: str = Field(default="out.txt", flags=["--output"])


class TestDefaults:
    def test_load_with_no_sources_uses_defaults(self) -> None:
        config = SimpleConfig.load(args=[], file=None)
        assert config.name == "test"
        assert config.port == 8080
        assert config.debug is False

    def test_load_returns_correctly_typed_fields(self) -> None:
        config = SimpleConfig.load(args=[], file=None)
        assert isinstance(config.name, str)
        assert isinstance(config.port, int)
        assert isinstance(config.debug, bool)


class TestCLI:
    def test_cli_flags_override_defaults(self) -> None:
        config = SimpleConfig.load(args=["--name", "prod", "--port", "9090"], file=None)
        assert config.name == "prod"
        assert config.port == 9090

    def test_parses_short_flags(self) -> None:
        config = SimpleConfig.load(args=["-n", "short", "-p", "1234"], file=None)
        assert config.name == "short"
        assert config.port == 1234

    def test_bool_flag_sets_true(self) -> None:
        config = SimpleConfig.load(args=["--debug"], file=None)
        assert config.debug is True

    def test_type_coercion_from_cli_string(self) -> None:
        config = SimpleConfig.load(args=["--port", "3000"], file=None)
        assert config.port == 3000
        assert isinstance(config.port, int)


class TestEnvVar:
    def test_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_API_KEY", "secret123")
        config = EnvConfig.load(args=[], file=None)
        assert config.api_key == "secret123"

    def test_cli_overrides_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TIMEOUT", "60")
        config = EnvConfig.load(args=["--timeout", "10"], file=None)
        assert config.timeout == 10

    def test_env_var_not_set_uses_default(self) -> None:
        config = EnvConfig.load(args=[], file=None)
        assert config.api_key == ""
        assert config.timeout == 30


class TestConfigFile:
    def test_toml_file_overrides_default(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "from-file"\nport = 5555\n')
        config = SimpleConfig.load(args=[], file=str(config_file))
        assert config.name == "from-file"
        assert config.port == 5555

    def test_loads_fields_from_scoped_section(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('[server]\nname = "scoped"\nport = 7777\n')
        config = SimpleConfig.load(args=[], file=str(config_file), section="server")
        assert config.name == "scoped"
        assert config.port == 7777

    def test_cli_overrides_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('name = "from-file"\n')
        config = SimpleConfig.load(args=["--name", "from-cli"], file=str(config_file))
        assert config.name == "from-cli"

    def test_missing_file_uses_defaults(self) -> None:
        config = SimpleConfig.load(args=[], file="/nonexistent/config.toml")
        assert config.name == "test"


class TestRequired:
    def test_required_field_raises_when_missing(self) -> None:
        with pytest.raises(ValueError, match="Required config field 'input_file'"):
            RequiredConfig.load(args=[], file=None)

    def test_required_field_satisfied_by_cli(self) -> None:
        config = RequiredConfig.load(args=["--input", "data.csv"], file=None)
        assert config.input_file == "data.csv"


class TestHelp:
    def test_help_flag_exits(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            SimpleConfig.load(args=["--help"], file=None)
        assert exc_info.value.code == 0

    def test_short_help_flag_exits(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            SimpleConfig.load(args=["-h"], file=None)
        assert exc_info.value.code == 0


class MultiSectionConfig(ConfigsLoader):
    model: str = Field(default="default-model", section="provider", flags=["--model"])
    base_url: str = Field(default="http://localhost:11434", section="provider")
    max_agents: int = Field(default=1, section="guild")
    permission: str = Field(default="ask", section="guild", flags=["--permission"])


class TestPerFieldSections:
    """Fields can declare which TOML section they belong to."""

    def test_fields_read_from_their_own_section(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[provider]\nmodel = "gemma4"\nbase_url = "http://remote:11434"\n\n'
            '[guild]\nmax_agents = 4\npermission = "autopilot"\n'
        )
        config = MultiSectionConfig.load(args=[], file=str(config_file))
        assert config.model == "gemma4"
        assert config.base_url == "http://remote:11434"
        assert config.max_agents == 4
        assert config.permission == "autopilot"

    def test_cli_overrides_section_values(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('[provider]\nmodel = "from-file"\n')
        config = MultiSectionConfig.load(args=["--model", "from-cli"], file=str(config_file))
        assert config.model == "from-cli"

    def test_missing_section_uses_default(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('[guild]\nmax_agents = 2\n')
        config = MultiSectionConfig.load(args=[], file=str(config_file))
        assert config.model == "default-model"  # provider section missing, uses default
        assert config.max_agents == 2

    def test_global_section_param_as_fallback(self, tmp_path: Path) -> None:
        """Fields without per-field section use the global section param."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('[server]\nname = "from-server-section"\nport = 9999\n')
        config = SimpleConfig.load(args=[], file=str(config_file), section="server")
        assert config.name == "from-server-section"
        assert config.port == 9999


class PermissionTier(str, Enum):
    NOTHING = "nothing"
    ASK = "ask"
    AUTOPILOT = "autopilot"


class EnumConfig(ConfigsLoader):
    permission: PermissionTier = Field(
        default=PermissionTier.ASK, flags=["--permission"], section="guild"
    )
    name: str = Field(default="test")


class TestEnumSupport:
    """str Enum types are coerced from string values."""

    def test_enum_uses_default_value(self) -> None:
        config = EnumConfig.load(args=[], file=None)
        assert config.permission == PermissionTier.ASK
        assert isinstance(config.permission, PermissionTier)

    def test_enum_from_cli_string(self) -> None:
        config = EnumConfig.load(args=["--permission", "autopilot"], file=None)
        assert config.permission == PermissionTier.AUTOPILOT

    def test_enum_from_config_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('[guild]\npermission = "nothing"\n')
        config = EnumConfig.load(args=[], file=str(config_file))
        assert config.permission == PermissionTier.NOTHING

    def test_enum_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumConfig.load(args=["--permission", "invalid"], file=None)


class TestResolutionOrder:
    """CLI > env > file > default."""

    def test_cli_overrides_env_overrides_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('timeout = 100\n')
        monkeypatch.setenv("MY_TIMEOUT", "200")
        config = EnvConfig.load(args=["--timeout", "300"], file=str(config_file))
        assert config.timeout == 300  # CLI wins

    def test_env_beats_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('timeout = 100\n')
        monkeypatch.setenv("MY_TIMEOUT", "200")
        config = EnvConfig.load(args=[], file=str(config_file))
        assert config.timeout == 200  # env wins over file

    def test_file_beats_default(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text('timeout = 100\n')
        config = EnvConfig.load(args=[], file=str(config_file))
        assert config.timeout == 100  # file wins over default (30)

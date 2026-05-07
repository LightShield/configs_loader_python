"""Tests for configsloader — verifies API contract."""

import os
from pathlib import Path

import pytest

from configsloader import ConfigsLoader, Field


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

    def test_field_types_are_correct(self) -> None:
        config = SimpleConfig.load(args=[], file=None)
        assert isinstance(config.name, str)
        assert isinstance(config.port, int)
        assert isinstance(config.debug, bool)


class TestCLI:
    def test_cli_flags_override_defaults(self) -> None:
        config = SimpleConfig.load(args=["--name", "prod", "--port", "9090"], file=None)
        assert config.name == "prod"
        assert config.port == 9090

    def test_short_flags_work(self) -> None:
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

    def test_section_scoped_loading(self, tmp_path: Path) -> None:
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


class TestResolutionOrder:
    """CLI > env > file > default."""

    def test_full_priority_chain(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

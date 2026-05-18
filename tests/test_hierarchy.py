"""Tests for hierarchy — FR-29, FR-44.

Covers: dotted CLI flags, nested class declaration, dotted section declaration.
"""

import pytest

from configsloader import ConfigsLoader, Field

# ---------------------------------------------------------------------------
# Config classes for hierarchy tests
# ---------------------------------------------------------------------------


class DottedFlagConfig(ConfigsLoader):
    """Config using dotted section names (flat pattern)."""

    db_host: str = Field(
        default="localhost",
        flags=["--backend.db.host"],
        section="backend.db",
        description="Database host",
    )
    db_port: int = Field(
        default=5432,
        flags=["--backend.db.port"],
        section="backend.db",
        description="Database port",
    )
    cache_ttl: int = Field(
        default=300,
        flags=["--backend.cache.ttl"],
        section="backend.cache",
        description="Cache TTL",
    )


class NestedClassConfig(ConfigsLoader):
    """Config using nested class declaration (compositional pattern)."""

    class backend(ConfigsLoader):
        class db(ConfigsLoader):
            host: str = Field(
                default="localhost", flags=["--backend.db.host"], description="DB host"
            )
            port: int = Field(default=5432, flags=["--backend.db.port"], description="DB port")

        class cache(ConfigsLoader):
            host: str = Field(
                default="localhost",
                flags=["--backend.cache.host"],
                description="Cache host",
            )
            ttl: int = Field(default=300, flags=["--backend.cache.ttl"], description="Cache TTL")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDottedCLIFlags:
    """AC-29.3: Dotted CLI flag resolves to nested field."""

    def test_dotted_cli_flag_resolves_to_field(self):
        """AC-29.3: --backend.db.host myhost resolves correctly."""
        config = DottedFlagConfig.load(args=["--backend.db.host", "myhost"])
        assert config.db_host == "myhost"

    def test_multiple_dotted_flags_resolve(self):
        """AC-29.3: Multiple dotted flags all resolve correctly."""
        config = DottedFlagConfig.load(
            args=[
                "--backend.db.host",
                "dbserver",
                "--backend.db.port",
                "3306",
                "--backend.cache.ttl",
                "60",
            ]
        )
        assert config.db_host == "dbserver"
        assert config.db_port == 3306
        assert config.cache_ttl == 60


@pytest.mark.unit
class TestNestedClassDeclaration:
    """AC-43.1: Nested class declaration creates field hierarchy."""

    def test_nested_class_cli_resolution(self):
        """AC-43.1: Nested class pattern resolves --backend.db.host to config.backend.db.host."""
        config = NestedClassConfig.load(args=["--backend.db.host", "myhost"])
        assert config.backend.db.host == "myhost"

    def test_nested_class_default_values(self):
        """AC-43.1: Nested class pattern preserves defaults."""
        config = NestedClassConfig.load(args=[])
        assert config.backend.db.host == "localhost"
        assert config.backend.db.port == 5432
        assert config.backend.cache.host == "localhost"
        assert config.backend.cache.ttl == 300

    def test_nested_class_multiple_fields(self):
        """AC-43.1: Multiple fields in nested classes resolve independently."""
        config = NestedClassConfig.load(
            args=["--backend.db.host", "db1", "--backend.cache.host", "cache1"]
        )
        assert config.backend.db.host == "db1"
        assert config.backend.cache.host == "cache1"


@pytest.mark.unit
class TestDottedSectionDeclaration:
    """AC-43.2: Dotted section declaration works for config file mapping."""

    def test_dotted_section_maps_to_nested_toml(self, tmp_path):
        """AC-43.2: section='backend.db' maps to [backend.db] in TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[backend.db]\n"
            'host = "toml-host"\n'
            "port = 3306\n\n"
            "[backend.cache]\n"
            "ttl = 60\n"
        )
        config = DottedFlagConfig.load(args=[], files=[str(config_file)])
        assert config.db_host == "toml-host"
        assert config.db_port == 3306
        assert config.cache_ttl == 60

    def test_dotted_section_cli_flag_equivalent(self):
        """AC-43.2: Dotted section with --backend.db.host resolves same as nested class."""
        config = DottedFlagConfig.load(args=["--backend.db.host", "myhost"])
        assert config.db_host == "myhost"


@pytest.mark.unit
class TestFlattenNestedClass:
    """Tests for flatten_nested_class and _collect_nested."""

    def test_flatten_nested_class_returns_fields(self):
        """hierarchy.py:50-62 — flatten_nested_class discovers nested ConfigsLoader subclasses."""
        from configsloader.hierarchy import flatten_nested_class

        result = flatten_nested_class(NestedClassConfig)
        # Should find backend.db.host, backend.db.port, backend.cache.host, backend.cache.ttl
        assert any("host" in key for key in result)

    def test_flatten_nested_class_includes_section(self):
        """hierarchy.py:77-92 — _collect_nested sets section prefix."""
        from configsloader.hierarchy import flatten_nested_class

        result = flatten_nested_class(NestedClassConfig)
        for _key, data in result.items():
            assert "section" in data
            assert data["section"] != ""


@pytest.mark.unit
class TestResolveDottedSection:
    """Tests for resolve_dotted_section edge cases."""

    def test_resolve_dotted_section_empty_string(self):
        """hierarchy.py:111 — empty section returns the data as-is."""
        from configsloader.hierarchy import resolve_dotted_section

        data = {"key": "value"}
        result = resolve_dotted_section(data, "")
        assert result == data

    def test_resolve_dotted_section_non_dict_leaf(self):
        """hierarchy.py:120 — non-dict leaf returns empty dict."""
        from configsloader.hierarchy import resolve_dotted_section

        data = {"backend": "scalar_value"}
        result = resolve_dotted_section(data, "backend")
        assert result == {}

    def test_resolve_dotted_section_missing_part(self):
        """hierarchy.py:111 — missing part in path returns empty dict."""
        from configsloader.hierarchy import resolve_dotted_section

        data = {"backend": {"db": {"host": "localhost"}}}
        result = resolve_dotted_section(data, "backend.cache")
        assert result == {}

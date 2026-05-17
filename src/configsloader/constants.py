"""Shared constants for the configsloader package.

Centralizes magic strings and value sets used across multiple modules.
"""

from __future__ import annotations

__all__ = [
    "RESERVED_FLAGS",
    "BOOL_TRUE_VALUES",
    "BOOL_FALSE_VALUES",
    "FORMAT_TOML",
    "FORMAT_JSON",
    "FORMAT_AUTO",
    "UNKNOWN_FLAG_ERROR",
    "UNKNOWN_FLAG_WARN",
    "UNKNOWN_FLAG_IGNORE",
    "HELP_MODE_NAVIGATION",
    "HELP_MODE_ALL",
    "HELP_MODE_REQUIRED",
    "HELP_MODE_GROUPS",
    "DEFAULT_SECTION",
    "SOURCE_CLI",
    "SOURCE_ENV",
    "SOURCE_PRESET",
    "SOURCE_FILE",
]

RESERVED_FLAGS: frozenset[str] = frozenset(
    {"--help", "-h", "--preset", "--print-config", "--print-config-verbose"}
)

BOOL_TRUE_VALUES: frozenset[str] = frozenset({"true", "1", "yes"})
BOOL_FALSE_VALUES: frozenset[str] = frozenset({"false", "0", "no"})

FORMAT_TOML: str = "toml"
FORMAT_JSON: str = "json"
FORMAT_AUTO: str = "auto"

UNKNOWN_FLAG_ERROR: str = "error"
UNKNOWN_FLAG_WARN: str = "warn"
UNKNOWN_FLAG_IGNORE: str = "ignore"

HELP_MODE_NAVIGATION: str = "navigation"
HELP_MODE_ALL: str = "all"
HELP_MODE_REQUIRED: str = "required"
HELP_MODE_GROUPS: str = "groups"

DEFAULT_SECTION: str = "general"

SOURCE_CLI: str = "cli"
SOURCE_ENV: str = "env"
SOURCE_PRESET: str = "preset"
SOURCE_FILE: str = "file"

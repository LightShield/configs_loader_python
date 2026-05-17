"""Config file source module.

Supports TOML and JSON formats with auto-detection and explicit override.
Handles multi-file layering where later files override earlier ones.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from configsloader.constants import FORMAT_AUTO, FORMAT_JSON, FORMAT_TOML

__all__ = ["load_file", "load_files"]


def _detect_format(path: str) -> str:
    """Auto-detect file format from extension.

    Args:
        path: File path string.

    Returns:
        Format string: 'toml' or 'json'.

    Raises:
        ValueError: If extension is unsupported.
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".toml":
        return FORMAT_TOML
    elif suffix == ".json":
        return FORMAT_JSON
    else:
        raise ValueError(
            f"Unsupported file format '{suffix}' for '{path}'. "
            f"Use file_format='toml' or file_format='json' explicitly."
        )


def _load_toml(path: str) -> dict[str, Any]:
    """Load and parse a TOML file.

    Args:
        path: Path to the TOML file.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If the file cannot be parsed as valid TOML.
    """
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Invalid TOML in '{path}': {e}") from e


def _load_json(path: str) -> dict[str, Any]:
    """Load and parse a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If the file cannot be parsed as valid JSON.
    """
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in '{path}': {e}") from e


def load_file(path: str, file_format: str = FORMAT_AUTO) -> dict[str, Any]:
    """Load a single config file.

    Args:
        path: Path to the config file.
        file_format: File format ('auto', 'toml', or 'json').

    Returns:
        Parsed dict of config values.

    Raises:
        ValueError: If the file format is unsupported or parsing fails.
        FileNotFoundError: If the file does not exist.
    """
    path = str(Path(path).expanduser())

    if file_format == FORMAT_AUTO:
        file_format = _detect_format(path)

    if file_format == FORMAT_TOML:
        return _load_toml(path)
    elif file_format == FORMAT_JSON:
        return _load_json(path)
    else:
        raise ValueError(f"Unsupported format: '{file_format}'")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dicts, with override taking precedence.

    Args:
        base: Base dictionary.
        override: Override dictionary (values win on conflict).

    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_files(
    paths: list[str],
    strict: bool = False,
) -> dict[str, Any]:
    """Load and layer multiple config files.

    Later files override earlier ones. Missing files are silently skipped
    unless strict mode is enabled.

    Args:
        paths: List of file paths to load in order.
        strict: If True, raise FileNotFoundError for missing files.

    Returns:
        Merged dict of config values.

    Raises:
        FileNotFoundError: If strict=True and a file does not exist.
    """
    result: dict[str, Any] = {}
    for path in paths:
        path = str(Path(path).expanduser())
        if not Path(path).is_file():
            if strict:
                raise FileNotFoundError(
                    f"Config file not found: '{path}'"
                )
            continue
        data = load_file(path)
        result = _deep_merge(result, data)
    return result

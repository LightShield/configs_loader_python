"""Preset file source module.

Loads a preset configuration file specified via --preset flag.
Supports TOML and JSON formats with auto-detection.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from configsloader.sources.file import load_file

__all__ = ["load_preset"]


def _resolve_preset_path(preset: str, preset_dir: str | None = None) -> str:
    """Resolve a preset name or path to an actual file path.

    Args:
        preset: Preset name or full file path.
        preset_dir: Optional directory to search for preset files.

    Returns:
        Resolved file path.

    Raises:
        FileNotFoundError: If the preset file cannot be found.
    """
    preset = os.path.expanduser(preset)

    # If it's already a full path that exists, use it
    if Path(preset).is_file():
        return preset

    # If a preset_dir is given, try resolving there
    if preset_dir:
        preset_dir = os.path.expanduser(preset_dir)
        dir_path = Path(preset_dir)
        # Try with .toml extension
        toml_path = dir_path / f"{preset}.toml"
        if toml_path.is_file():
            return str(toml_path)
        # Try with .json extension
        json_path = dir_path / f"{preset}.json"
        if json_path.is_file():
            return str(json_path)
        # Try bare name
        bare_path = dir_path / preset
        if bare_path.is_file():
            return str(bare_path)

    raise FileNotFoundError(
        f"Preset file not found: '{preset}'"
        + (f" (searched in '{preset_dir}')" if preset_dir else "")
    )


def load_preset(
    preset: str,
    fields: list[dict[str, Any]],
    preset_dir: str | None = None,
) -> dict[str, Any]:
    """Load a preset file and return field values.

    Preset keys are matched to fields using the first flag (stripped of dashes)
    or the field name directly.

    Args:
        preset: Preset file path or name to resolve.
        fields: List of field-info dicts with keys: name, flags, type.
        preset_dir: Optional directory to search for preset files by name.

    Returns:
        Dict mapping field names to values from the preset file.

    Raises:
        FileNotFoundError: If the preset file cannot be found.
    """
    path = _resolve_preset_path(preset, preset_dir)
    data = load_file(path)

    # Build mapping from preset key -> field name
    result: dict[str, Any] = {}
    for field in fields:
        name = field["name"]
        # Check field name directly
        if name in data:
            result[name] = data[name]
            continue
        # Check first flag stripped of leading dashes
        flags = field.get("flags", [])
        if flags:
            key = flags[0].lstrip("-")
            if key in data:
                result[name] = data[key]

    return result

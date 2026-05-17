"""Preset file source module.

Loads a preset configuration file specified via --preset flag.
Supports TOML and JSON formats with auto-detection.
"""

from __future__ import annotations

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
        ValueError: If the resolved preset path escapes the preset directory.
    """
    preset = str(Path(preset).expanduser())

    # If it's already a full path that exists, use it
    if Path(preset).is_file():
        return preset

    # If a preset_dir is given, try resolving there
    if preset_dir:
        preset_dir = str(Path(preset_dir).expanduser())
        dir_path = Path(preset_dir)

        # Guard against path traversal
        resolved_dir = dir_path.resolve()

        toml_path = dir_path / f"{preset}.toml"
        if toml_path.is_file():
            _check_path_traversal(toml_path, resolved_dir, preset)
            return str(toml_path)
        json_path = dir_path / f"{preset}.json"
        if json_path.is_file():
            _check_path_traversal(json_path, resolved_dir, preset)
            return str(json_path)
        bare_path = dir_path / preset
        if bare_path.is_file():
            _check_path_traversal(bare_path, resolved_dir, preset)
            return str(bare_path)

    raise FileNotFoundError(
        f"Preset file not found: '{preset}'"
        + (f" (searched in '{preset_dir}')" if preset_dir else "")
    )


def _check_path_traversal(path: Path, preset_dir_resolved: Path, name: str) -> None:
    """Verify that a resolved path stays within the preset directory.

    Args:
        path: The path to check.
        preset_dir_resolved: The resolved preset directory.
        name: The original preset name (for error messages).

    Raises:
        ValueError: If the path escapes the preset directory.
    """
    resolved = path.resolve()
    if not str(resolved).startswith(str(preset_dir_resolved)):
        raise ValueError(f"Preset path escapes preset directory: {name}")


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
        ValueError: If the preset path escapes the preset directory.
    """
    path = _resolve_preset_path(preset, preset_dir)
    data = load_file(path)

    result: dict[str, Any] = {}
    for field in fields:
        name = field["name"]
        if name in data:
            result[name] = data[name]
            continue
        flags = field.get("flags", [])
        if flags:
            key = flags[0].lstrip("-")
            if key in data:
                result[name] = data[key]

    return result

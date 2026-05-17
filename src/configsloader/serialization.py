"""Serialization module.

Prints configuration in TOML-compatible format.
Supports verbose (all values) and non-verbose (only non-default) modes.
"""

from __future__ import annotations

import sys
from typing import Any

__all__ = ["print_config"]


def _format_value(value: Any) -> str:
    """Format a value as a TOML-compatible string.

    Args:
        value: The value to format.

    Returns:
        TOML-compatible string representation.
    """
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return f'"{value}"'
    return f'"{value}"'


def _group_by_section(
    fields: dict[str, Any],
    values: dict[str, Any],
    verbose: bool,
) -> dict[str, list[tuple[str, Any]]]:
    """Group field values by section for TOML output.

    Args:
        fields: Dict of field name -> FieldDescriptor.
        values: Dict of field name -> resolved value.
        verbose: If True, include all fields; if False, only non-defaults.

    Returns:
        Dict of section -> list of (field_name, value) tuples.
    """
    groups: dict[str, list[tuple[str, Any]]] = {}
    for name, descriptor in fields.items():
        if not verbose and values.get(name) == descriptor.default:
            continue
        section = getattr(descriptor, "section", None) or ""
        if section not in groups:
            groups[section] = []
        groups[section].append((name, values.get(name)))
    return groups


def print_config(
    fields: dict[str, Any],
    resolved_values: dict[str, Any],
    verbose: bool = False,
) -> None:
    """Print configuration values in TOML format and exit.

    If verbose: prints all values.
    If not verbose: prints only values that differ from defaults.

    Args:
        fields: Dict of field name -> FieldDescriptor.
        resolved_values: Dict of field name -> resolved value.
        verbose: Whether to print all values or only non-defaults.

    Raises:
        SystemExit: Always raises SystemExit(0) after printing.
    """
    groups = _group_by_section(fields, resolved_values, verbose)
    lines: list[str] = []

    # Print top-level fields (no section) first
    if "" in groups:
        for name, value in groups[""]:
            lines.append(f"{name} = {_format_value(value)}")
        del groups[""]

    # Print sectioned fields
    for section in sorted(groups.keys()):
        if lines:
            lines.append("")
        lines.append(f"[{section}]")
        for name, value in groups[section]:
            lines.append(f"{name} = {_format_value(value)}")

    output = "\n".join(lines)
    if output:
        output += "\n"
    print(output, end="")
    raise SystemExit(0)

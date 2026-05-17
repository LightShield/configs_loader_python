"""CLI argument parsing source module.

Parses command-line arguments matching declared field flags.
Supports long/short flags, boolean switches, repeated flags (last wins),
and unknown flag handling modes (error/warn/ignore).
"""

from __future__ import annotations

import sys
from typing import Any

from configsloader.constants import (
    BOOL_FALSE_VALUES,
    BOOL_TRUE_VALUES,
    RESERVED_FLAGS,
    UNKNOWN_FLAG_ERROR,
    UNKNOWN_FLAG_WARN,
)

__all__ = ["parse_cli"]


def _validate_reserved(fields: list[dict[str, Any]]) -> None:
    """Raise if any field declares a reserved flag.

    Args:
        fields: List of field-info dicts with 'name' and 'flags' keys.

    Raises:
        ValueError: If a reserved flag is declared by a user field.
    """
    for field in fields:
        for flag in field.get("flags", []):
            if flag in RESERVED_FLAGS:
                raise ValueError(
                    f"Flag '{flag}' is reserved and cannot be used by field "
                    f"'{field['name']}'"
                )


def _build_flag_map(fields: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build mapping from flag strings to their field-info dicts.

    Args:
        fields: List of field-info dicts.

    Returns:
        Dict mapping each flag string to its field-info dict.
    """
    flag_map: dict[str, dict[str, Any]] = {}
    for field in fields:
        for flag in field.get("flags", []):
            flag_map[flag] = field
    return flag_map


def _is_flag(token: str) -> bool:
    """Check if a token looks like a CLI flag."""
    return token.startswith("-")


def parse_cli(
    args: list[str],
    fields: list[dict[str, Any]],
    unknown_flags: str = UNKNOWN_FLAG_ERROR,
) -> dict[str, Any]:
    """Parse CLI arguments and return resolved values.

    Args:
        args: Raw CLI argument list.
        fields: List of field-info dicts with keys: name, flags, type, is_bool.
        unknown_flags: How to handle unknown flags: 'error', 'warn', or 'ignore'.

    Returns:
        Dict mapping field names to their parsed string values.

    Raises:
        ValueError: On reserved flag conflict or unknown flags in error mode.
    """
    _validate_reserved(fields)
    flag_map = _build_flag_map(fields)
    result: dict[str, Any] = {}
    unknown: list[str] = []

    _parse_args_loop(args, flag_map, result, unknown)

    _handle_unknown(unknown, unknown_flags)
    return result


def _parse_args_loop(
    args: list[str],
    flag_map: dict[str, dict[str, Any]],
    result: dict[str, Any],
    unknown: list[str],
) -> None:
    """Main loop that processes CLI tokens into result values.

    Args:
        args: Raw CLI argument list.
        flag_map: Mapping from flag string to field-info dict.
        result: Accumulator dict for parsed values.
        unknown: Accumulator list for unknown flag strings.
    """
    i = 0
    while i < len(args):
        token = args[i]

        if token in RESERVED_FLAGS:
            i += 1
            # Skip reserved flag values (e.g., --preset <path>)
            if token == "--preset" and i < len(args) and not _is_flag(args[i]):
                i += 1
            continue

        if token in flag_map:
            field = flag_map[token]
            is_bool = field.get("is_bool", False)
            if is_bool:
                result[field["name"]] = _parse_bool_flag(args, i)
                # Advance past explicit bool value if present
                if i + 1 < len(args) and args[i + 1].lower() in (BOOL_TRUE_VALUES | BOOL_FALSE_VALUES):
                    i += 2
                else:
                    i += 1
            else:
                if i + 1 < len(args):
                    result[field["name"]] = args[i + 1]
                    i += 2
                else:
                    i += 1
        elif _is_flag(token):
            unknown.append(token)
            # Skip value of unknown flag if next arg is not a flag
            if i + 1 < len(args) and not _is_flag(args[i + 1]):
                i += 2
            else:
                i += 1
        else:
            i += 1


def _parse_bool_flag(args: list[str], idx: int) -> bool:
    """Determine boolean value for a flag at given index.

    Args:
        args: Full argument list.
        idx: Index of the boolean flag.

    Returns:
        True/False based on next token or bare switch semantics.
    """
    if idx + 1 < len(args):
        next_val = args[idx + 1].lower()
        if next_val in BOOL_TRUE_VALUES:
            return True
        if next_val in BOOL_FALSE_VALUES:
            return False
    return True


def _handle_unknown(unknown: list[str], mode: str) -> None:
    """Handle unknown flags based on mode.

    Args:
        unknown: List of unknown flag strings.
        mode: One of 'error', 'warn', 'ignore'.

    Raises:
        ValueError: In error mode when unknown flags are present.
    """
    if not unknown:
        return
    if mode == UNKNOWN_FLAG_ERROR:
        raise ValueError(f"Unknown CLI flags: {', '.join(unknown)}")
    elif mode == UNKNOWN_FLAG_WARN:
        print(f"Warning: unknown CLI flags: {', '.join(unknown)}", file=sys.stderr)

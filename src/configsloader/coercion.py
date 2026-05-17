"""Type coercion module.

Coerces raw string values from sources into their declared Python types.
Supports: str, int, float, bool (extended semantics), and Enum types.
"""

from __future__ import annotations

import enum
from typing import Any

__all__ = ["coerce"]

_BOOL_TRUE = {"true", "1", "yes"}


def coerce(value: Any, target_type: type, field_name: str) -> Any:
    """Coerce a value to the target type.

    Args:
        value: Raw value (typically a string from CLI/env/file).
        target_type: The declared Python type for the field.
        field_name: Name of the field (for error messages).

    Returns:
        The coerced value in the target type.

    Raises:
        ValueError: If coercion fails.
    """
    if value is None:
        return None
    if isinstance(value, target_type):
        return value
    if target_type is bool:
        return _coerce_bool(value)
    if _is_enum_type(target_type):
        return _coerce_enum(value, target_type, field_name)
    return _coerce_primitive(value, target_type, field_name)


def _coerce_bool(value: Any) -> bool:
    """Coerce a value to boolean with extended semantics.

    Args:
        value: Value to coerce.

    Returns:
        True for 'true'/'1'/'yes' (case-insensitive), False otherwise.
    """
    if isinstance(value, str):
        return value.lower() in _BOOL_TRUE
    return bool(value)


def _is_enum_type(target_type: type) -> bool:
    """Check if a type is an Enum subclass."""
    try:
        return isinstance(target_type, type) and issubclass(target_type, enum.Enum)
    except TypeError:
        return False


def _coerce_enum(value: Any, target_type: type, field_name: str) -> Any:
    """Coerce a value to an Enum type.

    Tries: by value, then by name (case-insensitive).
    For IntEnum, also tries numeric string conversion.

    Args:
        value: Value to coerce.
        target_type: Enum subclass.
        field_name: Field name for error messages.

    Returns:
        The matching enum member.

    Raises:
        ValueError: If no matching enum member is found.
    """
    # Try by value first
    for member in target_type:
        if member.value == value:
            return member

    # Try by name (case-insensitive)
    if isinstance(value, str):
        upper_val = value.upper()
        for member in target_type:
            if member.name == upper_val:
                return member

    # For IntEnum, try numeric string
    if isinstance(value, str) and issubclass(target_type, enum.IntEnum):
        try:
            int_val = int(value)
            return target_type(int_val)
        except (ValueError, KeyError):
            pass

    valid = [f"{m.name}={m.value!r}" for m in target_type]
    raise ValueError(
        f"Cannot convert '{value}' to {target_type.__name__} for field "
        f"'{field_name}'. Valid values: {', '.join(valid)}"
    )


def _coerce_primitive(value: Any, target_type: type, field_name: str) -> Any:
    """Coerce a value to a primitive type (int, float, str).

    Args:
        value: Value to coerce.
        target_type: Target primitive type.
        field_name: Field name for error messages.

    Returns:
        The coerced value.

    Raises:
        ValueError: If coercion fails.
    """
    try:
        return target_type(value)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Cannot convert '{value}' to {target_type.__name__} for field "
            f"'{field_name}': {e}"
        ) from None

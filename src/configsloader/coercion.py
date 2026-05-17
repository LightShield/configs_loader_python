"""Type coercion module.

Coerces raw string values from sources into their declared Python types.
Supports: str, int, float, bool (extended semantics), and Enum types.
"""

from __future__ import annotations

import enum
from typing import Any

from configsloader.constants import BOOL_TRUE_VALUES

__all__ = ["coerce"]


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
        TypeError: If target_type is a generic or unsupported type.
    """
    if value is None:
        return None
    try:
        if isinstance(value, target_type):
            return value
    except TypeError:
        pass  # Generic types (list[str]) don't support isinstance
    if target_type is bool:
        return _coerce_bool(value)
    if _is_enum_type(target_type):
        return _coerce_enum(value, target_type, field_name)
    if _is_unsupported_type(target_type):
        raise TypeError(
            f"Type '{target_type}' is not supported for coercion of field "
            f"'{field_name}'. Supported types: str, int, float, bool, Enum subclasses."
        )
    return _coerce_primitive(value, target_type, field_name)


def _is_unsupported_type(target_type: type) -> bool:
    """Check if a type is unsupported for coercion (e.g., generic types).

    Args:
        target_type: The type to check.

    Returns:
        True if the type is not supported.
    """
    # Check for generic types (list[str], dict[str, int], etc.)
    if hasattr(target_type, "__origin__"):
        return True
    # Check that it's a callable type constructor (str, int, float, etc.)
    if not isinstance(target_type, type):
        return True
    return False


def _coerce_bool(value: Any) -> bool:
    """Coerce a value to boolean with extended semantics.

    Args:
        value: Value to coerce.

    Returns:
        True for 'true'/'1'/'yes' (case-insensitive), False otherwise.
    """
    if isinstance(value, str):
        return value.lower() in BOOL_TRUE_VALUES
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

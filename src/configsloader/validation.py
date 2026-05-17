"""Validation module.

Validates resolved config values: required fields, custom validators,
and cross-field validators. Collects all errors for batch reporting.
"""

from __future__ import annotations

import inspect
from typing import Any

__all__ = ["validate_required", "run_validators", "collect_errors"]


def validate_required(
    fields: dict[str, Any],
    resolved_values: dict[str, Any],
) -> list[str]:
    """Check that all required fields have non-None values.

    Args:
        fields: Dict of field name -> FieldDescriptor.
        resolved_values: Dict of field name -> resolved value.

    Returns:
        List of error strings for missing required fields.
    """
    errors: list[str] = []
    for name, descriptor in fields.items():
        if descriptor.required and resolved_values.get(name) is None:
            errors.append(f"Required config field '{name}' has no value from any source")
    return errors


def run_validators(
    fields: dict[str, Any],
    resolved_values: dict[str, Any],
    config_instance: Any,
) -> list[str]:
    """Run custom validators on resolved values.

    Simple validators (1 arg): called with the field value.
    Cross-field validators (2 args): called with (value, config_instance).

    Args:
        fields: Dict of field name -> FieldDescriptor.
        resolved_values: Dict of field name -> resolved value.
        config_instance: The config instance for cross-field validation.

    Returns:
        List of error strings for failed validators.
    """
    errors: list[str] = []
    for name, descriptor in fields.items():
        validator = getattr(descriptor, "validator", None)
        if validator is None:
            continue
        value = resolved_values.get(name)
        if value is None:
            continue
        try:
            if _is_cross_field_validator(validator):
                result = validator(value, config_instance)
            else:
                result = validator(value)
            if result is False:
                errors.append(
                    f"Validation failed for field '{name}': "
                    f"validator returned False for value {value!r}"
                )
        except (TypeError, ValueError, AttributeError) as e:
            # Validators return bool; these are the most likely exceptions
            # from a malformed validator or unexpected value type.
            errors.append(f"Validation failed for field '{name}': {e}")
    return errors


def _is_cross_field_validator(validator: Any) -> bool:
    """Detect if a validator is a cross-field validator (2 params).

    Args:
        validator: The validator callable.

    Returns:
        True if the validator takes 2 parameters.
    """
    try:
        sig = inspect.signature(validator)
        params = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        return len(params) >= 2
    except (ValueError, TypeError):
        return False


def collect_errors(errors: list[str]) -> None:
    """Raise a ValueError with all collected errors if any exist.

    Args:
        errors: List of error strings.

    Raises:
        ValueError: Formatted multi-error message if errors is non-empty.
    """
    if not errors:
        return
    count = len(errors)
    formatted = "\n".join(f"  * {e}" for e in errors)
    raise ValueError(
        f"Configuration validation failed with {count} error(s):\n{formatted}"
    )

"""Hierarchy module.

Handles nested class declarations and dotted section names for
hierarchical configuration structures.
"""

from __future__ import annotations

from typing import Any

__all__ = ["find_nested_configs", "flatten_nested_class", "resolve_dotted_section"]


def find_nested_configs(cls: type, base_class: type) -> dict[str, type]:
    """Find all nested ConfigsLoader subclasses in a class.

    Args:
        cls: Class to inspect for nested subclasses.
        base_class: The base class to match (e.g., ConfigsLoader).

    Returns:
        Dict mapping attribute name to nested class.
    """
    results: dict[str, type] = {}
    for attr_name in list(vars(cls)):
        attr = getattr(cls, attr_name, None)
        if (
            isinstance(attr, type)
            and issubclass(attr, base_class)
            and attr is not base_class
            and attr is not cls
            and not attr_name.startswith("_")
        ):
            results[attr_name] = attr
    return results


def flatten_nested_class(cls: type) -> dict[str, Any]:
    """Find nested ConfigsLoader subclasses and flatten their fields.

    Nested classes have their fields extracted with dotted section names.
    E.g., nested class `Backend` with field `host` gets section="backend".

    Args:
        cls: The parent ConfigsLoader class to inspect.

    Returns:
        Dict of augmented fields with dotted section names.
    """
    from configsloader.core import ConfigsLoader as _Base

    nested: dict[str, Any] = {}
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name, None)
        if (
            isinstance(attr, type)
            and issubclass(attr, _Base)
            and attr is not _Base
            and attr is not cls
        ):
            _collect_nested(attr, attr_name.lower(), nested)
    return nested


def _collect_nested(
    cls: type,
    prefix: str,
    result: dict[str, Any],
) -> None:
    """Recursively collect fields from nested classes.

    Args:
        cls: The nested class to inspect.
        prefix: Current dotted prefix path.
        result: Accumulator dict for flattened fields.
    """
    from configsloader.core import ConfigsLoader as _Base

    for attr_name in dir(cls):
        attr = getattr(cls, attr_name, None)
        if (
            isinstance(attr, type)
            and issubclass(attr, _Base)
            and attr is not _Base
            and attr is not cls
        ):
            _collect_nested(attr, f"{prefix}.{attr_name.lower()}", result)

    fields = getattr(cls, "_fields", {})
    for name, descriptor in fields.items():
        key = f"{prefix}.{name}"
        result[key] = {
            "descriptor": descriptor,
            "section": prefix,
            "field_name": name,
            "full_path": key,
        }


def resolve_dotted_section(data: dict[str, Any], section: str) -> dict[str, Any]:
    """Navigate nested dicts by dot-separated keys.

    Args:
        data: The full config data dict (e.g., from TOML).
        section: Dot-separated section path (e.g., "backend.db").

    Returns:
        The nested dict at the specified path, or empty dict if not found.
    """
    if not section:
        return data
    current = data
    for part in section.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return {}
    if isinstance(current, dict):
        return current
    return {}

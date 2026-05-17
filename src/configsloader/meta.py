"""Metaclass for ConfigsLoader that collects Field declarations.

Handles field collection from class body and annotations, validates
reserved flag conflicts, and detects duplicate flag declarations at
class definition time.
"""

from __future__ import annotations

from typing import Any

from configsloader.constants import RESERVED_FLAGS
from configsloader.field import FieldDescriptor


__all__ = ["_ConfigMeta"]


class _ConfigMeta(type):
    """Metaclass that collects Field declarations from class body.

    Validates at class definition time that:
    - No field uses reserved flags (--help, -h, --preset, etc.)
    - No two fields share the same flag
    - Type annotations are preserved for coercion
    - Fields are inherited from parent classes
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
    ) -> type:
        """Create a new class, collecting and validating field declarations.

        Args:
            name: The class name.
            bases: Base classes.
            namespace: The class body namespace.

        Returns:
            The newly created class with _fields populated.

        Raises:
            ValueError: If reserved or duplicate flags are detected.
        """
        # Collect from parent classes first, then override with current class
        fields: dict[str, FieldDescriptor] = {}
        for base in bases:
            if not hasattr(base, "_fields"):
                continue
            for fname, fdesc in base._fields.items():
                # Skip private/internal fields from the base ConfigsLoader
                if not fname.startswith("_"):
                    fields[fname] = fdesc

        # Then process current class annotations (overrides parents)
        annotations = namespace.get("__annotations__", {})
        for field_name in annotations:
            value = namespace.get(field_name)
            if isinstance(value, FieldDescriptor):
                fields[field_name] = value
            else:
                fields[field_name] = FieldDescriptor(default=value)

        # Skip validation for the base ConfigsLoader class itself
        if bases:
            _validate_reserved_flags(fields)
            _validate_duplicate_flags(fields)

        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields = fields  # type: ignore[attr-defined]
        return cls


def _validate_reserved_flags(fields: dict[str, FieldDescriptor]) -> None:
    """Raise ValueError if any field uses a reserved flag.

    Args:
        fields: Mapping of field names to their descriptors.

    Raises:
        ValueError: If a reserved flag is found.
    """
    for field_name, descriptor in fields.items():
        for flag in descriptor.flags:
            if flag in RESERVED_FLAGS:
                raise ValueError(
                    f"Field '{field_name}' uses reserved flag '{flag}'. "
                    f"Reserved flags: {sorted(RESERVED_FLAGS)}"
                )


def _validate_duplicate_flags(fields: dict[str, FieldDescriptor]) -> None:
    """Raise ValueError if two fields share the same flag.

    Args:
        fields: Mapping of field names to their descriptors.

    Raises:
        ValueError: If duplicate flags are detected.
    """
    seen: dict[str, str] = {}
    for field_name, descriptor in fields.items():
        for flag in descriptor.flags:
            if flag in seen:
                raise ValueError(
                    f"Duplicate flag '{flag}' declared by both "
                    f"'{seen[flag]}' and '{field_name}'"
                )
            seen[flag] = field_name

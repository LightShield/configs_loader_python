"""Field descriptor for declarative config field declarations.

Provides the FieldDescriptor dataclass and the Field() factory function
for declaring configuration fields with metadata for multi-source resolution.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

__all__ = ["FieldDescriptor", "Field"]


@dataclass
class FieldDescriptor:
    """Metadata for a single config field.

    Attributes:
        default: Default value if no source provides one.
        flags: CLI flags (e.g., ["--model", "-m"]).
        env: Environment variable name.
        section: Config file section this field lives in.
        description: Human-readable description for --help.
        required: If True, raises if no value found from any source.
        validator: Optional callable to validate the resolved value.
    """

    default: Any = None
    flags: list[str] = dc_field(default_factory=list)
    env: str | None = None
    section: str | None = None
    description: str = ""
    required: bool = False
    validator: Callable[[Any], bool] | None = None


# Intentional: Field() mirrors dataclasses.field() pattern — grouping these would hurt usability
def Field(  # noqa: N802
    default: Any = None,
    flags: list[str] | None = None,
    env: str | None = None,
    section: str | None = None,
    description: str = "",
    required: bool = False,
    validator: Callable[[Any], bool] | None = None,
) -> Any:
    """Declare a config field with resolution metadata.

    Args:
        default: Default value if no source provides one.
        flags: CLI flags (e.g., ["--model", "-m"]).
        env: Environment variable name.
        section: Config file section this field lives in.
        description: Human-readable description for --help.
        required: If True, raises if no value found from any source.
        validator: Optional callable to validate the resolved value.

    Returns:
        A FieldDescriptor instance used by the ConfigsLoader metaclass.
    """
    return FieldDescriptor(
        default=default,
        flags=flags or [],
        env=env,
        section=section,
        description=description,
        required=required,
        validator=validator,
    )

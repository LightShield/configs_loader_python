"""Core implementation — declarative config with multi-source resolution.

Provides the ConfigsLoader base class that uses _ConfigMeta for field
collection and delegates .load() to the loader orchestrator module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from configsloader.field import Field, FieldDescriptor
from configsloader.meta import _ConfigMeta


__all__ = ["ConfigsLoader", "Field"]


class ConfigsLoader(metaclass=_ConfigMeta):
    """Base class for declarative config definitions.

    Subclass this and declare fields with Field(). Then call .load() to
    resolve values from CLI > env > preset > config file > default.
    """

    _fields: dict[str, FieldDescriptor]
    _is_set: dict[str, bool]

    def __init__(self, **values: Any) -> None:
        """Initialize with resolved field values."""
        self._is_set = {}
        for name, descriptor in self._fields.items():
            setattr(self, name, values.get(name, descriptor.default))

    def is_set(self, field_name: str) -> bool:
        """Check if a field was explicitly set by any source.

        Args:
            field_name: Name of the field to check.

        Returns:
            True if the field was set by CLI, env, preset, or file.
        """
        return self._is_set.get(field_name, False)

    @classmethod
    def load(
        cls,
        args: list[str] | None = None,
        files: list[str] | None = None,
        file: str | Path | None = None,
        section: str | None = None,
    ) -> "ConfigsLoader":
        """Load config from all sources.

        Resolution order (highest priority first):
        1. CLI arguments
        2. Environment variables
        3. Preset file (if --preset specified)
        4. Config files
        5. Default values

        Args:
            args: CLI arguments (default: sys.argv[1:]).
            files: List of config file paths.
            file: Single config file path (convenience).
            section: Global section override. If set, all fields without a
                per-field section use this. Per-field sections take priority.

        Returns:
            An instance with all fields resolved.

        Raises:
            SystemExit: If --help or --print-config is requested.
            ValueError: If validation fails.
        """
        from configsloader.loader import load_config
        return load_config(cls, args=args, files=files, file=file, section=section)

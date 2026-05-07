"""Core implementation — declarative config with multi-source resolution.

⚠️  TEMPORARY: trivial implementation using tomllib + sys.argv.
    Will be replaced with proper parser later.
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, get_type_hints


__all__ = ["ConfigsLoader", "Field"]


@dataclass
class FieldDescriptor:
    """Metadata for a single config field."""

    default: Any = None
    flags: list[str] = dc_field(default_factory=list)
    env: str | None = None
    description: str = ""
    required: bool = False


def Field(
    default: Any = None,
    flags: list[str] | None = None,
    env: str | None = None,
    description: str = "",
    required: bool = False,
) -> Any:
    """Declare a config field with resolution metadata.

    Args:
        default: Default value if no source provides one.
        flags: CLI flags (e.g., ["--model", "-m"]).
        env: Environment variable name.
        description: Human-readable description for --help.
        required: If True, raises if no value found from any source.

    Returns:
        A FieldDescriptor (used by ConfigsLoader metaclass).
    """
    return FieldDescriptor(
        default=default,
        flags=flags or [],
        env=env,
        description=description,
        required=required,
    )


class _ConfigMeta(type):
    """Metaclass that collects Field declarations from class body."""

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        fields: dict[str, FieldDescriptor] = {}
        annotations = namespace.get("__annotations__", {})

        for field_name, _ in annotations.items():
            value = namespace.get(field_name)
            if isinstance(value, FieldDescriptor):
                fields[field_name] = value
            else:
                fields[field_name] = FieldDescriptor(default=value)

        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields = fields  # type: ignore[attr-defined]
        return cls


class ConfigsLoader(metaclass=_ConfigMeta):
    """Base class for declarative config definitions.

    Subclass this and declare fields with Field(). Then call .load() to
    resolve values from CLI > env > config file > default.
    """

    _fields: dict[str, FieldDescriptor]

    def __init__(self, **values: Any) -> None:
        for name, descriptor in self._fields.items():
            setattr(self, name, values.get(name, descriptor.default))

    @classmethod
    def load(
        cls,
        args: list[str] | None = None,
        file: str | Path | None = None,
        section: str | None = None,
    ) -> "ConfigsLoader":
        """Load config from all sources.

        Resolution order (highest priority first):
        1. CLI arguments
        2. Environment variables
        3. Config file
        4. Default values

        Args:
            args: CLI arguments (default: sys.argv[1:]).
            file: Path to TOML config file.
            section: Section within the TOML file to read from.

        Returns:
            An instance with all fields resolved.

        Raises:
            SystemExit: If --help is requested.
            ValueError: If a required field has no value from any source.
        """
        if args is None:
            args = sys.argv[1:]

        if "--help" in args or "-h" in args:
            cls._print_help()
            raise SystemExit(0)

        file_values = cls._load_file(file, section)
        env_values = cls._load_env()
        cli_values = cls._parse_cli(args)

        resolved: dict[str, Any] = {}
        type_hints = get_type_hints(cls)

        for name, descriptor in cls._fields.items():
            raw = _resolve_value(name, descriptor, cli_values, env_values, file_values)
            target_type = type_hints.get(name, str)
            resolved[name] = _coerce(raw, target_type, name)

        return cls(**resolved)

    @classmethod
    def _load_file(cls, file: str | Path | None, section: str | None) -> dict[str, Any]:
        """Load values from a TOML file."""
        if file is None:
            return {}
        path = Path(file)
        if not path.is_file():
            return {}
        with open(path, "rb") as f:
            data = tomllib.load(f)
        if section and section in data:
            data = data[section]
        return data

    @classmethod
    def _load_env(cls) -> dict[str, str]:
        """Load values from environment variables."""
        values: dict[str, str] = {}
        for name, descriptor in cls._fields.items():
            if descriptor.env and descriptor.env in os.environ:
                values[name] = os.environ[descriptor.env]
        return values

    @classmethod
    def _parse_cli(cls, args: list[str]) -> dict[str, str]:
        """Parse CLI arguments matching declared flags."""
        values: dict[str, str] = {}
        flag_map: dict[str, str] = {}

        for name, descriptor in cls._fields.items():
            for flag in descriptor.flags:
                flag_map[flag] = name

        i = 0
        while i < len(args):
            arg = args[i]
            if arg in flag_map:
                field_name = flag_map[arg]
                type_hint = get_type_hints(cls).get(field_name, str)
                if type_hint is bool:
                    values[field_name] = "true"
                elif i + 1 < len(args):
                    i += 1
                    values[field_name] = args[i]
            i += 1

        return values

    @classmethod
    def _print_help(cls) -> None:
        """Print auto-generated help text."""
        print(f"\nUsage: [options]\n")
        print("Options:")
        for name, descriptor in cls._fields.items():
            flags_str = ", ".join(descriptor.flags) if descriptor.flags else f"  --{name}"
            type_hint = get_type_hints(cls).get(name, str)
            type_name = type_hint.__name__ if hasattr(type_hint, "__name__") else str(type_hint)
            default_str = f" (default: {descriptor.default})" if descriptor.default is not None else ""
            required_str = " [REQUIRED]" if descriptor.required else ""
            desc = descriptor.description or ""
            print(f"  {flags_str:<20} {desc}{default_str}{required_str} [{type_name}]")
        print(f"\n  --help, -h{'':14} Show this help message")


def _resolve_value(
    name: str,
    descriptor: FieldDescriptor,
    cli: dict[str, Any],
    env: dict[str, Any],
    file: dict[str, Any],
) -> Any:
    """Resolve a field value from sources in priority order."""
    if name in cli:
        return cli[name]
    if name in env:
        return env[name]
    if name in file:
        return file[name]
    if descriptor.required and descriptor.default is None:
        raise ValueError(
            f"Required config field '{name}' has no value. "
            f"Provide via: {', '.join(descriptor.flags) or f'--{name}'}"
            + (f" or env {descriptor.env}" if descriptor.env else "")
            + " or config file."
        )
    return descriptor.default


def _coerce(value: Any, target_type: type, field_name: str) -> Any:
    """Coerce a value to the target type."""
    if value is None:
        return None
    if isinstance(value, target_type):
        return value
    if target_type is bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    try:
        return target_type(value)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Cannot convert '{value}' to {target_type.__name__} for field '{field_name}': {e}"
        ) from None

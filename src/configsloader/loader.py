"""Loader orchestrator module.

Wires together all source modules, coercion, validation, help, and
serialization to implement the full ConfigsLoader.load() flow.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, get_type_hints

from configsloader.coercion import coerce
from configsloader.help import print_help_and_exit
from configsloader.hierarchy import resolve_dotted_section
from configsloader.serialization import print_config
from configsloader.sources.cli import parse_cli
from configsloader.sources.env import load_env
from configsloader.sources.file import load_files
from configsloader.sources.preset import load_preset
from configsloader.validation import collect_errors, run_validators, validate_required

__all__ = ["load_config"]


def _build_field_infos(cls: type) -> list[dict[str, Any]]:
    """Build field-info dicts for source modules from class fields.

    Includes fields from nested ConfigsLoader subclasses.

    Args:
        cls: ConfigsLoader subclass.

    Returns:
        List of field-info dicts compatible with source module APIs.
    """
    type_hints = get_type_hints(cls)
    infos: list[dict[str, Any]] = []
    for name, descriptor in cls._fields.items():
        target_type = type_hints.get(name, str)
        infos.append({
            "name": name,
            "flags": descriptor.flags,
            "env": getattr(descriptor, "env", None),
            "type": target_type,
            "is_bool": target_type is bool,
        })

    # Add fields from nested classes
    nested_fields = _collect_nested_fields(cls)
    for nf in nested_fields:
        infos.append(nf["info"])

    return infos


def _collect_nested_fields(cls: type, prefix: str = "") -> list[dict[str, Any]]:
    """Recursively collect field infos from nested ConfigsLoader subclasses.

    Args:
        cls: Class to inspect for nested ConfigsLoader subclasses.
        prefix: Dotted prefix for nested path.

    Returns:
        List of dicts with 'info', 'path', 'field_name', 'descriptor', 'type'.
    """
    from configsloader.core import ConfigsLoader as _Base

    results: list[dict[str, Any]] = []
    for attr_name in list(vars(cls)):
        attr = getattr(cls, attr_name, None)
        if (
            isinstance(attr, type)
            and issubclass(attr, _Base)
            and attr is not _Base
            and attr is not cls
            and not attr_name.startswith("_")
        ):
            nested_prefix = f"{prefix}{attr_name}" if not prefix else f"{prefix}.{attr_name}"
            # Get this nested class's own fields
            nested_hints = get_type_hints(attr)
            for name, descriptor in attr._fields.items():
                target_type = nested_hints.get(name, str)
                results.append({
                    "info": {
                        "name": f"{nested_prefix}.{name}",
                        "flags": descriptor.flags,
                        "env": getattr(descriptor, "env", None),
                        "type": target_type,
                        "is_bool": target_type is bool,
                    },
                    "path": nested_prefix,
                    "field_name": name,
                    "descriptor": descriptor,
                    "type": target_type,
                })
            # Recurse into sub-nested classes
            results.extend(_collect_nested_fields(attr, nested_prefix))
    return results


def _extract_preset_arg(args: list[str]) -> str | None:
    """Extract --preset value from args if present.

    Args:
        args: CLI argument list.

    Returns:
        Preset path string, or None.
    """
    for i, arg in enumerate(args):
        if arg == "--preset" and i + 1 < len(args):
            return args[i + 1]
    return None


def _extract_help_mode(args: list[str]) -> str | None:
    """Extract help mode from args.

    Args:
        args: CLI argument list.

    Returns:
        Help mode string or None if --help not present.
    """
    for i, arg in enumerate(args):
        if arg in ("--help", "-h"):
            # Check if next arg is a mode (not another flag)
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                return args[i + 1]
            return "navigation"
    return None


def _has_print_config(args: list[str]) -> bool:
    """Check if --print-config is in args."""
    return "--print-config" in args


def _has_print_config_verbose(args: list[str]) -> bool:
    """Check if --print-config-verbose is in args."""
    return "--print-config-verbose" in args


def _build_nested_instances(
    cls: type,
    cli_values: dict[str, Any],
    env_values: dict[str, Any],
    preset_values: dict[str, Any],
    file_data: dict[str, Any],
) -> dict[str, Any]:
    """Build nested config instances for nested ConfigsLoader subclasses.

    Args:
        cls: Parent ConfigsLoader class.
        cli_values: Parsed CLI values (keys may be dotted like 'backend.db.host').
        env_values: Env var values.
        preset_values: Preset values.
        file_data: Raw file data dict.

    Returns:
        Dict mapping attribute names to nested instances.
    """
    from configsloader.core import ConfigsLoader as _Base

    nested_instances: dict[str, Any] = {}
    for attr_name in list(vars(cls)):
        attr = getattr(cls, attr_name, None)
        if (
            isinstance(attr, type)
            and issubclass(attr, _Base)
            and attr is not _Base
            and attr is not cls
            and not attr_name.startswith("_")
        ):
            instance = _load_nested(
                attr, attr_name, cli_values, env_values, preset_values, file_data
            )
            nested_instances[attr_name] = instance
    return nested_instances


def _load_nested(
    cls: type,
    prefix: str,
    cli_values: dict[str, Any],
    env_values: dict[str, Any],
    preset_values: dict[str, Any],
    file_data: dict[str, Any],
) -> Any:
    """Load a single nested ConfigsLoader instance.

    Args:
        cls: Nested ConfigsLoader subclass.
        prefix: Dotted prefix path.
        cli_values: All CLI values.
        env_values: All env values.
        preset_values: All preset values.
        file_data: Full file data.

    Returns:
        Populated nested instance.
    """
    from configsloader.core import ConfigsLoader as _Base

    type_hints = get_type_hints(cls)
    instance = cls.__new__(cls)
    instance._is_set = {}

    # Resolve this class's own fields
    for name, descriptor in cls._fields.items():
        dotted_key = f"{prefix}.{name}"
        # Look up in sources using dotted key
        raw = descriptor.default
        was_set = False

        if dotted_key in cli_values:
            raw = cli_values[dotted_key]
            was_set = True
        elif dotted_key in env_values:
            raw = env_values[dotted_key]
            was_set = True
        elif dotted_key in preset_values:
            raw = preset_values[dotted_key]
            was_set = True
        else:
            # Check file data using dotted section
            section_data = resolve_dotted_section(file_data, prefix)
            if name in section_data:
                raw = section_data[name]
                was_set = True

        target_type = type_hints.get(name, str)
        try:
            value = coerce(raw, target_type, name)
        except ValueError:
            value = raw
        setattr(instance, name, value)
        instance._is_set[name] = was_set

    # Recursively handle sub-nested classes
    for attr_name in list(vars(cls)):
        attr = getattr(cls, attr_name, None)
        if (
            isinstance(attr, type)
            and issubclass(attr, _Base)
            and attr is not _Base
            and attr is not cls
            and not attr_name.startswith("_")
        ):
            sub_instance = _load_nested(
                attr, f"{prefix}.{attr_name}",
                cli_values, env_values, preset_values, file_data
            )
            setattr(instance, attr_name, sub_instance)

    return instance


def load_config(
    cls: type,
    args: list[str] | None = None,
    files: list[str] | None = None,
    file: str | Path | None = None,
    section: str | None = None,
) -> Any:
    """Load configuration from all sources.

    Resolution order (highest priority first):
    1. CLI arguments
    2. Environment variables
    3. Preset file (if --preset specified)
    4. Config files
    5. Default values

    Args:
        cls: ConfigsLoader subclass with declared fields.
        args: CLI arguments (default: sys.argv[1:]).
        files: List of config file paths to load.
        file: Single config file path (convenience for single file).
        section: Global section override.

    Returns:
        Populated instance of cls.

    Raises:
        SystemExit: For --help or --print-config.
        ValueError: For validation errors.
    """
    if args is None:
        args = sys.argv[1:]

    type_hints = get_type_hints(cls)
    field_infos = _build_field_infos(cls)

    # Handle help early
    help_mode = _extract_help_mode(args)
    if help_mode is not None:
        print_help_and_exit(cls._fields, type_hints, mode=help_mode)

    # Parse CLI (includes nested fields)
    cli_values = parse_cli(args, field_infos, unknown_flags="ignore")

    # Load env vars
    env_values = load_env(field_infos)

    # Load preset if specified
    preset_path = _extract_preset_arg(args)
    preset_values: dict[str, Any] = {}
    if preset_path:
        preset_dir = None
        meta = getattr(cls, "Meta", None)
        if meta:
            preset_dir = getattr(meta, "preset_dir", None)
        preset_values = load_preset(preset_path, field_infos, preset_dir=preset_dir)

    # Load config files
    file_paths: list[str] = []
    if files:
        file_paths = files
    elif file:
        file_paths = [str(file)]
    file_data = load_files(file_paths) if file_paths else {}

    # Resolve own fields and track is_set
    resolved: dict[str, Any] = {}
    is_set: dict[str, bool] = {}
    coercion_errors: list[str] = []

    for name, descriptor in cls._fields.items():
        # Determine file value using section
        field_section = getattr(descriptor, "section", None) or section
        if field_section:
            field_values = resolve_dotted_section(file_data, field_section)
        else:
            field_values = file_data

        # Determine the key to look up in file_values
        file_key = _get_file_key(name, descriptor, field_section)

        # Resolve from sources in priority order
        raw, was_set = _resolve_value(
            name, descriptor, cli_values, env_values, preset_values,
            field_values, file_key
        )
        is_set[name] = was_set

        # Coerce type
        target_type = type_hints.get(name, str)
        try:
            resolved[name] = coerce(raw, target_type, name)
        except ValueError as e:
            coercion_errors.append(str(e))
            resolved[name] = raw

    # Handle --print-config
    if _has_print_config_verbose(args):
        print_config(cls._fields, resolved, verbose=True)
    if _has_print_config(args):
        print_config(cls._fields, resolved, verbose=False)

    # Build instance for cross-field validation
    instance = cls.__new__(cls)
    for name, value in resolved.items():
        setattr(instance, name, value)
    instance._is_set = is_set

    # Build nested instances
    nested = _build_nested_instances(
        cls, cli_values, env_values, preset_values, file_data
    )
    for attr_name, nested_inst in nested.items():
        setattr(instance, attr_name, nested_inst)

    # Run validators
    validator_errors = run_validators(cls._fields, resolved, instance)

    # Validate required fields
    required_errors = validate_required(cls._fields, resolved)

    # Collect all errors
    all_errors = coercion_errors + validator_errors + required_errors
    collect_errors(all_errors)

    return instance


def _get_file_key(name: str, descriptor: Any, section: str | None) -> str:
    """Determine the key to look up in file data for a field.

    If the field has a dotted section and flags, derive the local key
    from the first flag by stripping the section prefix.

    Args:
        name: Field name.
        descriptor: FieldDescriptor instance.
        section: The resolved section for this field.

    Returns:
        The key string to use in file data lookup.
    """
    if section and descriptor.flags:
        # Try to derive key from first flag: --backend.db.host -> host
        first_flag = descriptor.flags[0].lstrip("-")
        prefix = section + "."
        if first_flag.startswith(prefix):
            return first_flag[len(prefix):]
    return name


def _resolve_value(
    name: str,
    descriptor: Any,
    cli: dict[str, Any],
    env: dict[str, Any],
    preset: dict[str, Any],
    file: dict[str, Any],
    file_key: str | None = None,
) -> tuple[Any, bool]:
    """Resolve a field value from sources in priority order.

    Args:
        name: Field name.
        descriptor: FieldDescriptor instance.
        cli: CLI values dict.
        env: Env values dict.
        preset: Preset values dict.
        file: File values dict.
        file_key: Key to look up in file dict (may differ from name).

    Returns:
        Tuple of (resolved value, was_set flag).
    """
    if name in cli:
        return cli[name], True
    if name in env:
        return env[name], True
    if name in preset:
        return preset[name], True
    # Check file using file_key (may be different from name for dotted sections)
    lookup_key = file_key if file_key else name
    if lookup_key in file:
        return file[lookup_key], True
    # Also try the field name itself as fallback
    if file_key and name in file:
        return file[name], True
    return descriptor.default, False

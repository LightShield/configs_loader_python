"""Help output module.

Generates formatted help text with ANSI colors, section grouping,
and multiple display modes (navigation, all, required, groups, group name).
"""

from __future__ import annotations

import os
import sys
from typing import Any

from configsloader.constants import (
    DEFAULT_SECTION,
    HELP_MODE_ALL,
    HELP_MODE_GROUPS,
    HELP_MODE_NAVIGATION,
    HELP_MODE_REQUIRED,
)

__all__ = ["generate_help", "print_help_and_exit"]

# ANSI color codes
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _should_use_colors() -> bool:
    """Determine if ANSI colors should be used based on environment."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


def _colorize(text: str, code: str, use_colors: bool) -> str:
    """Wrap text in ANSI color codes if colors are enabled."""
    if not use_colors:
        return text
    return f"{code}{text}{_RESET}"


_TYPE_DISPLAY_NAMES = {
    "str": "string",
    "int": "integer",
    "float": "float",
    "bool": "bool",
}


def _format_type_name(type_hint: type) -> str:
    """Format a type hint as a display string."""
    if hasattr(type_hint, "__name__"):
        name = type_hint.__name__
        return _TYPE_DISPLAY_NAMES.get(name, name)
    return str(type_hint)


def _format_default(value: Any, type_hint: type) -> str:
    """Format a default value for display."""
    if value is None:
        return ""
    if isinstance(value, str):
        return f'default: "{value}"'
    if isinstance(value, bool):
        return f"default: {str(value).lower()}"
    return f"default: {value}"


def _group_fields_by_section(
    fields: dict[str, Any],
) -> dict[str, list[tuple[str, Any]]]:
    """Group fields by their section attribute.

    Args:
        fields: Dict of field name -> FieldDescriptor.

    Returns:
        Dict of section name -> list of (field_name, descriptor) tuples.
    """
    groups: dict[str, list[tuple[str, Any]]] = {}
    for name, descriptor in fields.items():
        section = getattr(descriptor, "section", None) or DEFAULT_SECTION
        if section not in groups:
            groups[section] = []
        groups[section].append((name, descriptor))
    return groups


def _format_field_line(
    name: str,
    descriptor: Any,
    type_hints: dict[str, type],
    use_colors: bool,
) -> str:
    """Format a single field as a help line.

    Args:
        name: Field name.
        descriptor: FieldDescriptor instance.
        type_hints: Dict of field name -> type.
        use_colors: Whether to use ANSI colors.

    Returns:
        Formatted help line string.
    """
    # Flags
    flags = descriptor.flags if descriptor.flags else [f"--{name}"]
    flags_str = ", ".join(flags)
    flags_str = _colorize(flags_str, _GREEN, use_colors)

    # Type
    type_hint = type_hints.get(name, str)
    type_name = _format_type_name(type_hint)
    type_str = _colorize(f"<{type_name}>", _DIM, use_colors)

    # Required tag
    required_str = ""
    if descriptor.required:
        required_str = _colorize(" [Required]", _RED, use_colors)

    # Description
    desc = descriptor.description or ""

    # Default
    default_str = _format_default(descriptor.default, type_hint)
    if default_str:
        default_str = _colorize(f" ({default_str})", _DIM, use_colors)

    return f"  {flags_str} {type_str}{required_str} {desc}{default_str}"


def _build_group_tree(sections: list[str]) -> dict[str, Any]:
    """Build a tree structure from dotted section names.

    Args:
        sections: List of section name strings.

    Returns:
        Nested dict representing the tree.
    """
    tree: dict[str, Any] = {}
    for section in sections:
        parts = section.split(".")
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    return tree


def _render_tree(tree: dict[str, Any], indent: int = 0) -> str:
    """Render a tree dict as indented text.

    Args:
        tree: Nested dict from _build_group_tree.
        indent: Current indentation level.

    Returns:
        Formatted tree string.
    """
    lines: list[str] = []
    for key, subtree in sorted(tree.items()):
        lines.append("  " * indent + key)
        if subtree:
            lines.append(_render_tree(subtree, indent + 1))
    return "\n".join(lines)


def generate_help(
    fields: dict[str, Any],
    type_hints: dict[str, type],
    mode: str = "navigation",
    use_colors: bool | None = None,
    program_name: str = "program",
) -> str:
    """Generate formatted help text.

    Args:
        fields: Dict of field name -> FieldDescriptor.
        type_hints: Dict of field name -> type.
        mode: Display mode: 'navigation', 'all', 'required', 'groups',
              or a specific group name.
        use_colors: Whether to use ANSI colors (None = auto-detect).
        program_name: Program name for usage line.

    Returns:
        Formatted help text string.
    """
    if use_colors is None:
        use_colors = _should_use_colors()

    if mode == HELP_MODE_NAVIGATION:
        return _generate_navigation(fields, use_colors, program_name)
    if mode == HELP_MODE_ALL:
        return _generate_all(fields, type_hints, use_colors, program_name)
    if mode == HELP_MODE_REQUIRED:
        return _generate_required(fields, type_hints, use_colors, program_name)
    if mode == HELP_MODE_GROUPS:
        return _generate_groups(fields, use_colors, program_name)
    return _generate_group(fields, type_hints, mode, use_colors, program_name)


def _generate_navigation(
    fields: dict[str, Any],
    use_colors: bool,
    program_name: str,
) -> str:
    """Generate navigation mode help (bare --help)."""
    groups = _group_fields_by_section(fields)
    lines: list[str] = []
    usage = _colorize(f"Usage: {program_name} [options]", _BOLD, use_colors)
    lines.append(usage)
    lines.append("")
    lines.append("Available groups:")
    for group in sorted(groups.keys()):
        lines.append(f"  {group}")
    lines.append("")
    lines.append("Use --help all to see all options")
    lines.append("Use --help <group> to see options for a specific group")
    return "\n".join(lines)


def _generate_all(
    fields: dict[str, Any],
    type_hints: dict[str, type],
    use_colors: bool,
    program_name: str,
) -> str:
    """Generate all-fields help mode."""
    groups = _group_fields_by_section(fields)
    lines: list[str] = []
    usage = _colorize(f"Usage: {program_name} [options]", _BOLD, use_colors)
    lines.append(usage)
    lines.append("")

    for section in sorted(groups.keys()):
        header = _colorize(f"[{section}]", _CYAN, use_colors)
        lines.append(header)
        for name, descriptor in groups[section]:
            lines.append(_format_field_line(name, descriptor, type_hints, use_colors))
        lines.append("")

    return "\n".join(lines)


def _generate_required(
    fields: dict[str, Any],
    type_hints: dict[str, type],
    use_colors: bool,
    program_name: str,
) -> str:
    """Generate required-fields-only help mode."""
    lines: list[str] = []
    usage = _colorize(f"Usage: {program_name} [options]", _BOLD, use_colors)
    lines.append(usage)
    lines.append("")
    lines.append("Required options:")
    lines.append("")

    for name, descriptor in fields.items():
        if descriptor.required:
            lines.append(_format_field_line(name, descriptor, type_hints, use_colors))

    return "\n".join(lines)


def _generate_groups(
    fields: dict[str, Any],
    use_colors: bool,
    program_name: str,
) -> str:
    """Generate groups hierarchy tree."""
    groups = _group_fields_by_section(fields)
    sections = list(groups.keys())
    tree = _build_group_tree(sections)
    lines: list[str] = []
    usage = _colorize(f"Usage: {program_name} [options]", _BOLD, use_colors)
    lines.append(usage)
    lines.append("")
    lines.append("Configuration groups:")
    lines.append("")
    lines.append(_render_tree(tree))
    return "\n".join(lines)


def _generate_group(
    fields: dict[str, Any],
    type_hints: dict[str, type],
    group_name: str,
    use_colors: bool,
    program_name: str,
) -> str:
    """Generate help for a specific group."""
    groups = _group_fields_by_section(fields)
    lines: list[str] = []
    usage = _colorize(f"Usage: {program_name} [options]", _BOLD, use_colors)
    lines.append(usage)
    lines.append("")

    # Find matching group (exact or prefix match for dotted)
    matching_fields: list[tuple[str, Any]] = []
    for section, section_fields in groups.items():
        if section == group_name or section.startswith(group_name + "."):
            matching_fields.extend(section_fields)

    if matching_fields:
        header = _colorize(f"[{group_name}]", _CYAN, use_colors)
        lines.append(header)
        for name, descriptor in matching_fields:
            lines.append(_format_field_line(name, descriptor, type_hints, use_colors))

    return "\n".join(lines)


def print_help_and_exit(
    fields: dict[str, Any],
    type_hints: dict[str, type],
    mode: str = "navigation",
    use_colors: bool | None = None,
    program_name: str = "program",
) -> None:
    """Print help text and exit with code 0.

    Args:
        fields: Dict of field name -> FieldDescriptor.
        type_hints: Dict of field name -> type.
        mode: Display mode.
        use_colors: Whether to use ANSI colors.
        program_name: Program name for usage line.

    Raises:
        SystemExit: Always raises SystemExit(0).
    """
    text = generate_help(fields, type_hints, mode, use_colors, program_name)
    print(text)
    raise SystemExit(0)

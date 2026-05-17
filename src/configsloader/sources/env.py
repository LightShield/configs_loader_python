"""Environment variable source module.

Loads configuration values from environment variables.
"""

from __future__ import annotations

import os
from typing import Any

__all__ = ["load_env"]


def load_env(fields: list[dict[str, Any]]) -> dict[str, str]:
    """Load values from environment variables for declared fields.

    Args:
        fields: List of field-info dicts with keys: name, env, type.

    Returns:
        Dict mapping field names to their env var string values.
        Only includes fields whose env var is actually set.
    """
    result: dict[str, str] = {}
    for field in fields:
        env_var = field.get("env")
        if env_var and env_var in os.environ:
            result[field["name"]] = os.environ[env_var]
    return result

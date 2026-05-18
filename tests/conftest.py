"""Shared fixtures for configsloader tests."""

import enum


class Color(enum.Enum):
    """Plain Enum for coercion tests."""

    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Priority(enum.IntEnum):
    """IntEnum for coercion tests."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Mode(enum.StrEnum):
    """StrEnum for coercion tests."""

    FAST = "fast"
    SLOW = "slow"
    AUTO = "auto"

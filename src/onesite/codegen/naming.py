"""Naming conventions shared by metadata parsing and generation phases."""

import re


def to_snake(name: str) -> str:
    """Convert PascalCase to snake_case, e.g. UserProfile → user_profile."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def to_pascal(snake: str) -> str:
    """Convert snake_case to PascalCase, e.g. device_model → DeviceModel."""
    return "".join(word.capitalize() for word in snake.split("_"))


def pluralize(name: str) -> str:
    """Simple English pluralization."""
    if name.endswith("y") and name[-2] not in "aeiou":
        return f"{name[:-1]}ies"
    return f"{name}s"

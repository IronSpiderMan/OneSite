"""Validation for declarative field display colors."""

import math

PRESET_COLORS = (
    "gray",
    "red",
    "orange",
    "amber",
    "yellow",
    "lime",
    "green",
    "emerald",
    "teal",
    "cyan",
    "sky",
    "blue",
    "indigo",
    "violet",
    "purple",
    "pink",
    "rose",
)


def normalize_color(value, *, field_name, field_names, location, config_key="color"):
    def fail(message):
        raise ValueError(f"{location}.{config_key} {message}")

    def color(name):
        if not isinstance(name, str) or name not in PRESET_COLORS:
            fail(f"must use a preset color, got {name!r}")
        return name

    def scalar(value):
        return (
            value is None
            or isinstance(value, (str, bool, int, float))
            and (not isinstance(value, float) or math.isfinite(value))
        )

    if value is None:
        return None
    if isinstance(value, str):
        return color(value)
    if not isinstance(value, dict) or set(value) - {"rules", "default"}:
        fail("must be a preset name or an object with rules and optional default")
    if not isinstance(value.get("rules"), list) or not value["rules"]:
        fail("rules must be a non-empty list")
    result = {"rules": []}
    if "default" in value:
        result["default"] = color(value["default"])
    for index, rule in enumerate(value["rules"]):
        if not isinstance(rule, dict) or set(rule) != {"when", "color"}:
            fail(f"rules[{index}] requires when and color")
        when = rule["when"]
        if not isinstance(when, dict):
            fail(f"rules[{index}].when must be an object")
        target = when.get("field", field_name)
        if not isinstance(target, str) or target not in field_names:
            fail(f"rules[{index}] references unknown field {target!r}")
        operators = set(when) - {"field"}
        if len(operators) != 1 or not operators <= {"eq", "ne", "in", "gt", "gte", "lt", "lte"}:
            fail(f"rules[{index}].when requires exactly one supported operator")
        op = next(iter(operators))
        expected = when[op]
        if op == "in":
            valid = isinstance(expected, list) and all(scalar(item) for item in expected)
        elif op in {"gt", "gte", "lt", "lte"}:
            valid = (
                isinstance(expected, (int, float))
                and not isinstance(expected, bool)
                and scalar(expected)
            )
        else:
            valid = scalar(expected)
        if not valid:
            fail(f"rules[{index}].when.{op} has an invalid operand")
        result["rules"].append(
            {"when": {"field": target, op: expected}, "color": color(rule["color"])}
        )
    return result


def enum_color_config(enum_cls, *, field_name):
    """Compile shared Enum value colors into the existing field rule format."""
    props = getattr(enum_cls, "__onesite__", None)
    if props is None:
        return None
    location = f"{enum_cls.__name__}.__onesite__.color"
    if not isinstance(props, dict):
        raise ValueError(f"{enum_cls.__name__}.__onesite__ must be an object")
    mapping = props.get("color")
    if mapping is None:
        return None
    if not isinstance(mapping, dict):
        raise ValueError(f"{location} must map enum values to preset colors")
    members = list(enum_cls)
    rules = []
    for value, color in mapping.items():
        # Preserve integer/string identity instead of coercing mapping keys.
        member = next(
            (item for item in members
             if type(item.value) is type(value) and item.value == value),
            None,
        )
        if member is None:
            raise ValueError(f"{location} references unknown enum value {value!r}")
        if not isinstance(color, str) or color not in PRESET_COLORS:
            raise ValueError(f"{location} must use a preset color, got {color!r}")
        rules.append({"when": {"field": field_name, "eq": member.value}, "color": color})
    return {"rules": rules} if rules else None

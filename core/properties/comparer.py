"""
Property comparison helpers.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


PropertyTree = dict[str, Any]
PropertyExtractor = Callable[[str], PropertyTree | None]


def get_flat_properties_for_display(conditional_properties: PropertyTree | None) -> dict[str, dict[str, str]]:
    """
    Convert the conditional-aware property structure into flat display values.

    For conditional properties, if values are applied first and else values
    override them. This preserves the legacy comparison behavior.
    """
    flat: dict[str, dict[str, str]] = {}
    if not conditional_properties:
        return flat

    for category, data in conditional_properties.items():
        if category.startswith("_") or not isinstance(data, dict):
            continue

        category_values: dict[str, str] = {}
        if "_flat" not in data and "_conditional" not in data:
            category_values.update(
                {key: value for key, value in data.items() if not str(key).startswith("_")}
            )
            flat[category] = category_values
            continue

        category_values.update(data.get("_flat", {}))

        for block in data.get("_conditional", []):
            if not isinstance(block, dict):
                continue
            category_values.update(block.get("if_props", {}))
            else_props = block.get("else_props")
            if else_props:
                category_values.update(else_props)

        flat[category] = category_values

    return flat


def compare_property_dict(
    first: dict[str, str],
    second: dict[str, str],
    category: str,
    first_label: str = "File1",
    second_label: str = "File2",
) -> list[str]:
    differences: list[str] = []

    for key in sorted(set(first.keys()) | set(second.keys())):
        first_value = first.get(key, "<missing>")
        second_value = second.get(key, "<missing>")

        if first_value != second_value:
            differences.append(
                f"{category}.{key}: {first_label}='{first_value}' vs {second_label}='{second_value}'"
            )

    return differences


def compare_properties(
    first_properties: PropertyTree | None,
    second_properties: PropertyTree | None,
    first_label: str = "File1",
    second_label: str = "File2",
) -> list[str] | None:
    if not first_properties or not second_properties:
        return None

    first_flat = get_flat_properties_for_display(first_properties)
    second_flat = get_flat_properties_for_display(second_properties)

    differences: list[str] = []
    for category in ("LMKD", "Chimera"):
        differences.extend(
            compare_property_dict(
                first_flat.get(category, {}),
                second_flat.get(category, {}),
                category,
                first_label=first_label,
                second_label=second_label,
            )
        )

    return differences


def compare_properties_between_files(
    first_path: str,
    second_path: str,
    extractor: PropertyExtractor,
    first_label: str = "File1",
    second_label: str = "File2",
) -> list[str] | None:
    try:
        return compare_properties(
            extractor(first_path),
            extractor(second_path),
            first_label=first_label,
            second_label=second_label,
        )
    except Exception:
        return None

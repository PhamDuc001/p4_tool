"""
Property parsing helpers for device_common.mk property sections.
"""

from __future__ import annotations

from typing import Any


PropertyTree = dict[str, Any]


def parse_prop_line(line: str) -> tuple[str, str] | None:
    """Parse a single property line into (key, value)."""
    stripped = line.strip().rstrip(" \\")
    if not stripped or stripped.startswith("#"):
        return None
    if "PRODUCT_PROPERTY_OVERRIDES" in stripped:
        return None
    if stripped in ("ifneq", "ifdef", "ifndef", "else", "endif"):
        return None
    if stripped.startswith(("ifneq", "ifdef", "ifndef", "else", "endif")):
        return None
    if "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if "#" in value:
        value = value.split("#")[0].strip()
    value = value.rstrip(" \\")
    if not key:
        return None
    return key, value


def extract_block_lines(all_lines: list[str], start_header: str) -> list[str]:
    """
    Return lines for the first matching property section, including the header.

    Repeated occurrences of the same header are merged until a different section
    header is reached. This preserves the current legacy behavior.
    """
    result: list[str] = []
    in_block = False

    for line in all_lines:
        stripped = line.strip()
        if stripped.lower() == start_header.lower():
            if not in_block:
                result.append(line)
                in_block = True
            continue

        if in_block:
            if stripped.startswith("#") and stripped.lower() != start_header.lower():
                break
            result.append(line)

    return result


def parse_block_with_conditionals(block_lines: list[str]) -> dict[str, Any]:
    flat: dict[str, str] = {}
    conditionals: list[dict[str, Any]] = []

    index = 0
    if block_lines and block_lines[0].strip().lower().startswith("# "):
        index = 1

    while index < len(block_lines):
        stripped = block_lines[index].strip()

        if stripped.startswith(("ifneq", "ifdef", "ifndef")):
            condition = stripped
            if_props: dict[str, str] = {}
            else_props: dict[str, str] | None = None
            state = "if"
            index += 1

            while index < len(block_lines):
                current = block_lines[index].strip()

                if current == "else":
                    state = "else"
                    else_props = {}
                    index += 1
                    continue

                if current == "endif":
                    index += 1
                    break

                if current.startswith(("ifneq", "ifdef", "ifndef")):
                    depth = 1
                    index += 1
                    while index < len(block_lines) and depth > 0:
                        nested = block_lines[index].strip()
                        if nested.startswith(("ifneq", "ifdef", "ifndef")):
                            depth += 1
                        elif nested == "endif":
                            depth -= 1
                        index += 1
                    continue

                parsed = parse_prop_line(block_lines[index])
                if parsed:
                    key, value = parsed
                    if state == "if":
                        if_props[key] = value
                    elif else_props is not None:
                        else_props[key] = value
                index += 1

            conditionals.append(
                {
                    "condition": condition,
                    "if_props": if_props,
                    "else_props": else_props,
                }
            )
            continue

        parsed = parse_prop_line(block_lines[index])
        if parsed:
            key, value = parsed
            flat[key] = value
        index += 1

    return {"_flat": flat, "_conditional": conditionals}


def extract_properties_from_lines(lines: list[str]) -> PropertyTree | None:
    properties: PropertyTree = {}

    lmkd_block = extract_block_lines(lines, "# LMKD property")
    if not lmkd_block:
        lmkd_block = extract_block_lines(lines, "# DHA property")
    if lmkd_block:
        parsed = parse_block_with_conditionals(lmkd_block)
        parsed["_raw_lines"] = "".join(lmkd_block)
        if parsed["_flat"] or parsed["_conditional"]:
            properties["LMKD"] = parsed

    chimera_block = extract_block_lines(lines, "# Chimera property")
    if chimera_block:
        parsed = parse_block_with_conditionals(chimera_block)
        parsed["_raw_lines"] = "".join(chimera_block)
        if parsed["_flat"] or parsed["_conditional"]:
            properties["Chimera"] = parsed

    if not properties:
        return None

    for category in ("LMKD", "Chimera"):
        properties.setdefault(category, {"_flat": {}, "_conditional": [], "_raw_lines": ""})

    return properties


def extract_properties_from_file(file_path: str) -> PropertyTree | None:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return extract_properties_from_lines(file.readlines())
    except Exception:
        return None


def validate_conditional_structure_match(
    first: PropertyTree,
    second: PropertyTree | None,
) -> tuple[bool, list[str]]:
    diffs: list[str] = []
    second = second or {}

    for category in ("LMKD", "Chimera"):
        first_blocks = first.get(category, {}).get("_conditional", [])
        second_blocks = second.get(category, {}).get("_conditional", [])
        if len(first_blocks) != len(second_blocks):
            diffs.append(
                f"{category}: different number of conditional blocks "
                f"({len(first_blocks)} vs {len(second_blocks)})"
            )
            continue

        for index, (first_block, second_block) in enumerate(zip(first_blocks, second_blocks)):
            if first_block["condition"] != second_block["condition"]:
                diffs.append(
                    f"{category} block {index}: condition mismatch "
                    f"('{first_block['condition']}' vs '{second_block['condition']}')"
                )

    return len(diffs) == 0, diffs


def parse_properties_block(block_lines: list[str]) -> dict[str, str]:
    """Parse a legacy flat property block, ignoring conditional structure."""
    properties: dict[str, str] = {}

    for line in block_lines:
        parsed = parse_prop_line(line)
        if parsed:
            key, value = parsed
            properties[key] = value

    return properties


def enforce_structure_from_raw(file_path: str, properties_dict: PropertyTree) -> tuple[bool, str | None]:
    """
    Replace LMKD and Chimera sections with _raw_lines from a parsed source tree.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        for category, header in (("LMKD", "# LMKD property"), ("Chimera", "# Chimera property")):
            category_data = properties_dict.get(category)
            if not category_data:
                continue

            raw_content = category_data.get("_raw_lines", "")
            if not raw_content:
                continue

            raw_lines = (
                raw_content.splitlines(keepends=True)
                if isinstance(raw_content, str)
                else raw_content
            )

            lines = _remove_existing_category_lines(lines, category, header)
            insert_index = _find_insert_index(lines, category)
            lines = lines[:insert_index] + ["\n"] + raw_lines + ["\n"] + lines[insert_index:]

        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(_collapse_extra_empty_lines(lines))

        return True, None
    except Exception as exc:
        return False, str(exc)


def _remove_existing_category_lines(lines: list[str], category: str, header: str) -> list[str]:
    new_lines: list[str] = []
    in_block = False

    for line in lines:
        stripped = line.strip()
        is_category_header = stripped.lower() == header.lower() or (
            category == "LMKD" and stripped.lower() == "# dha property"
        )

        if is_category_header:
            in_block = True
            continue

        if in_block:
            is_new_section = stripped.startswith("#") and not is_category_header
            if is_new_section:
                in_block = False
                new_lines.append(line)
            continue

        new_lines.append(line)

    return new_lines


def _find_insert_index(lines: list[str], category: str) -> int:
    if category == "LMKD":
        for index, line in enumerate(lines):
            if line.strip().lower() == "# chimera property":
                return max(0, index - 1)
        return len(lines)

    last_property_index = -1
    for index, line in enumerate(lines):
        if line.strip().startswith("ro.slmk."):
            last_property_index = index
    return last_property_index + 1 if last_property_index != -1 else len(lines)


def _collapse_extra_empty_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    empty_count = 0

    for line in lines:
        if not line.strip():
            empty_count += 1
            if empty_count > 2:
                continue
        else:
            empty_count = 0
        cleaned.append(line)

    return cleaned

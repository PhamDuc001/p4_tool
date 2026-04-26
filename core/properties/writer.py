"""
Property update helpers for device_common.mk property sections.
"""

from __future__ import annotations

from typing import Any

from core.properties.parser import parse_prop_line


def find_block_boundaries(lines: list[str], start_header: str, next_header_list: list[str]):
    start = end = None
    for idx, line in enumerate(lines):
        if line.strip() == start_header:
            start = idx
            break

    if start is None:
        return None, None

    for idx in range(start + 1, len(lines)):
        if lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(lines)

    return start, end


def analyze_product_override_blocks(original_lines: list[str]) -> list[dict[str, Any]]:
    override_blocks: list[dict[str, Any]] = []
    index = 1
    conditional_stack = []

    while index < len(original_lines):
        stripped_line = original_lines[index].strip()

        if stripped_line.startswith(("ifneq", "ifdef", "ifndef")):
            conditional_stack.append(("if", index))
        elif stripped_line == "else":
            if conditional_stack:
                conditional_stack[-1] = ("else", index)
        elif stripped_line == "endif":
            if conditional_stack:
                conditional_stack.pop()

        if "PRODUCT_PROPERTY_OVERRIDES" in stripped_line and "+=" in stripped_line:
            block_start = index
            block_properties: list[str] = []
            block_lines = [index]
            block_conditional_context = list(conditional_stack)
            index += 1

            while index < len(original_lines):
                prop_line = original_lines[index]
                prop_stripped = prop_line.strip()

                if prop_stripped.startswith(("ifneq", "ifdef", "ifndef")):
                    break
                if prop_stripped in ("else", "endif"):
                    break
                if not prop_stripped or prop_stripped.startswith("#"):
                    block_lines.append(index)
                    index += 1
                    continue
                if "=" in prop_stripped:
                    prop_content = prop_stripped[:-1].strip() if prop_stripped.endswith("\\") else prop_stripped
                    if "=" in prop_content:
                        block_properties.append(prop_content.split("=", 1)[0].strip())
                    block_lines.append(index)
                    if not prop_stripped.endswith("\\"):
                        index += 1
                        break
                    index += 1
                    continue
                break

            override_blocks.append(
                {
                    "start": block_start,
                    "properties": block_properties,
                    "lines": block_lines,
                    "conditional_context": block_conditional_context,
                }
            )
        else:
            index += 1

    return override_blocks


def get_default_indentation(original_lines: list[str]) -> str:
    for line in original_lines:
        if "=" in line and not line.strip().startswith("#") and "PRODUCT_PROPERTY_OVERRIDES" not in line:
            return line[: len(line) - len(line.lstrip())]
    return "    "


def update_product_override_block_with_deletions(
    original_lines: list[str],
    override_blocks: list[dict[str, Any]],
    remaining_properties: dict[str, str],
):
    new_block = [original_lines[0]]
    processed_lines = set()

    for line_idx in range(1, len(original_lines)):
        if line_idx in processed_lines:
            continue
        new_block.append(original_lines[line_idx])
        processed_lines.add(line_idx)

    for block in override_blocks:
        properties_to_update = {
            prop_key: remaining_properties[prop_key]
            for prop_key in block["properties"]
            if prop_key in remaining_properties
        }

        if not properties_to_update:
            continue

        updated_block_lines = []
        for line_idx in block["lines"]:
            if line_idx >= len(original_lines):
                continue

            line = original_lines[line_idx]
            stripped_line = line.strip()

            if "=" in stripped_line and not stripped_line.startswith("#") and "PRODUCT_PROPERTY_OVERRIDES" not in stripped_line:
                prop_line_content = stripped_line[:-1].strip() if stripped_line.endswith("\\") else stripped_line
                if "=" in prop_line_content:
                    prop_key = prop_line_content.split("=", 1)[0].strip()
                    if prop_key in properties_to_update:
                        indent = line[: len(line) - len(line.lstrip())]
                        new_value = properties_to_update[prop_key]
                        original_content = prop_line_content.split("=", 1)[1].strip()
                        if "#" in original_content:
                            comment_part = original_content.split("#", 1)[1]
                            new_line = f"{indent}{prop_key}={new_value} #{comment_part}\n"
                        elif stripped_line.endswith("\\"):
                            new_line = f"{indent}{prop_key}={new_value} \\\n"
                        else:
                            new_line = f"{indent}{prop_key}={new_value}\n"
                        updated_block_lines.append((line_idx, new_line))
                        remaining_properties.pop(prop_key, None)
                        continue

            updated_block_lines.append((line_idx, line))

        for line_idx, updated_line in updated_block_lines:
            if line_idx < len(new_block):
                new_block[line_idx] = updated_line

    return new_block, remaining_properties


def add_remaining_properties(
    new_block: list[str],
    remaining_properties: dict[str, str],
    original_lines: list[str],
) -> list[str]:
    if not remaining_properties:
        return new_block

    default_indent = get_default_indentation(original_lines)
    for key, value in remaining_properties.items():
        new_block.append(f"{default_indent}{key}={value}\n")
    return new_block


def update_properties_block_preserve_format_with_deletions(
    lines: list[str],
    new_properties: dict[str, str],
    start_header: str,
    next_header_list: list[str],
) -> list[str]:
    start, end = find_block_boundaries(lines, start_header, next_header_list)
    if start is None:
        return lines

    original_lines = lines[start:end]
    remaining_properties = new_properties.copy()
    override_blocks = analyze_product_override_blocks(original_lines)
    new_block, remaining_properties = update_product_override_block_with_deletions(
        original_lines, override_blocks, remaining_properties
    )
    new_block = add_remaining_properties(new_block, remaining_properties, original_lines)
    return lines[:start] + new_block + lines[end:]


def is_new_conditional_structure(properties_dict: dict[str, Any]) -> bool:
    for category in ("LMKD", "Chimera"):
        value = properties_dict.get(category)
        if isinstance(value, dict) and ("_flat" in value or "_conditional" in value):
            return True
    return False


def is_conditional_aware_update(properties_dict: dict[str, Any]) -> bool:
    for props in properties_dict.values():
        if isinstance(props, dict):
            for prop_value in props.values():
                if isinstance(prop_value, dict) and "values_by_context" in prop_value:
                    return True
                if isinstance(prop_value, dict) and any(str(key).startswith("[") for key in prop_value.keys()):
                    return True
    return False


def update_properties_in_file(file_path: str, properties_dict: dict[str, Any]):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        if is_new_conditional_structure(properties_dict):
            return update_v2_conditional_structure(file_path, properties_dict, lines)

        if is_conditional_aware_update(properties_dict):
            return update_properties_conditional_aware(file_path, properties_dict, lines)

        if properties_dict.get("LMKD"):
            lines = update_properties_block_preserve_format_with_deletions(
                lines,
                properties_dict["LMKD"],
                "# LMKD property",
                ["# Chimera property", "# DHA property"],
            )
            if not any("# LMKD property" in line for line in lines):
                lines = update_properties_block_preserve_format_with_deletions(
                    lines,
                    properties_dict["LMKD"],
                    "# DHA property",
                    ["# Chimera property"],
                )

        if properties_dict.get("Chimera"):
            lines = update_properties_block_preserve_format_with_deletions(
                lines,
                properties_dict["Chimera"],
                "# Chimera property",
                ["# Nandswap", "#", ""],
            )

        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(lines)

        return True, None
    except Exception as exc:
        return False, str(exc)


def update_v2_conditional_structure(file_path: str, properties_dict: dict[str, Any], lines: list[str]):
    try:
        for category in ("LMKD", "Chimera"):
            category_data = properties_dict.get(category)
            if not category_data or not isinstance(category_data, dict):
                continue

            flat_props = category_data.get("_flat", {})
            conditional_blocks = category_data.get("_conditional", [])

            if category == "LMKD":
                section_header = "# LMKD property"
                alt_header = "# DHA property"
                next_headers = ["# Chimera property", "# DHA property", "# Nandswap"]
            else:
                section_header = "# Chimera property"
                alt_header = None
                next_headers = ["# Nandswap", "#", ""]

            if flat_props:
                lines = update_flat_props_in_section(lines, flat_props, section_header, next_headers)
                if alt_header and not any(section_header in line for line in lines):
                    lines = update_flat_props_in_section(lines, flat_props, alt_header, next_headers)

            for conditional_block in conditional_blocks:
                condition = conditional_block.get("condition", "")
                if condition:
                    lines = update_conditional_block_in_file(
                        lines,
                        condition,
                        conditional_block.get("if_props", {}),
                        conditional_block.get("else_props"),
                    )

        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(lines)

        return True, None
    except Exception as exc:
        return False, str(exc)


def update_flat_props_in_section(
    lines: list[str],
    flat_props: dict[str, str],
    section_header: str,
    next_headers: list[str],
) -> list[str]:
    start, end = find_block_boundaries(lines, section_header, next_headers)
    if start is None:
        return lines

    section = lines[start:end]
    remaining = flat_props.copy()
    in_conditional = 0

    for index in range(1, len(section)):
        stripped = section[index].strip()

        if stripped.startswith(("ifneq", "ifdef", "ifndef")):
            in_conditional += 1
            continue
        if stripped == "else" and in_conditional > 0:
            continue
        if stripped == "endif":
            if in_conditional > 0:
                in_conditional -= 1
            continue
        if in_conditional > 0:
            continue

        parsed = parse_prop_line(section[index])
        if parsed:
            key, _ = parsed
            if key in remaining:
                section[index] = format_property_line(section[index], key, remaining[key])
                del remaining[key]

    return lines[:start] + section + lines[end:]


def update_conditional_block_in_file(
    lines: list[str],
    condition: str,
    if_props: dict[str, str],
    else_props: dict[str, str] | None,
) -> list[str]:
    index = 0
    while index < len(lines):
        if lines[index].strip() == condition:
            index += 1
            state = "if"
            depth = 1

            while index < len(lines) and depth > 0:
                current = lines[index].strip()

                if current.startswith(("ifneq", "ifdef", "ifndef")):
                    depth += 1
                    index += 1
                    continue
                if current == "else" and depth == 1:
                    state = "else"
                    index += 1
                    continue
                if current == "endif":
                    depth -= 1
                    index += 1
                    continue

                parsed = parse_prop_line(lines[index])
                if parsed:
                    key, _ = parsed
                    if state == "if" and if_props and key in if_props:
                        lines[index] = format_property_line(lines[index], key, if_props[key])
                    elif state == "else" and else_props and key in else_props:
                        lines[index] = format_property_line(lines[index], key, else_props[key])

                index += 1

            return lines

        index += 1

    return lines


def update_properties_conditional_aware(file_path: str, properties_dict: dict[str, Any], lines: list[str]):
    try:
        for category, props in properties_dict.items():
            if not isinstance(props, dict) or category not in ("LMKD", "Chimera"):
                continue

            conditional_props = {}
            flat_props = {}
            for prop_name, prop_value in props.items():
                if isinstance(prop_value, dict) and "values_by_context" in prop_value:
                    conditional_props[prop_name] = prop_value
                else:
                    flat_props[prop_name] = prop_value

            if conditional_props:
                lines = update_conditional_properties_in_section(lines, category, conditional_props)

            if flat_props:
                if category == "LMKD":
                    lines = update_properties_block_preserve_format_with_deletions(
                        lines, flat_props, "# LMKD property", ["# Chimera property", "# DHA property"]
                    )
                    if not any("# LMKD property" in line for line in lines):
                        lines = update_properties_block_preserve_format_with_deletions(
                            lines, flat_props, "# DHA property", ["# Chimera property"]
                        )
                elif category == "Chimera":
                    lines = update_properties_block_preserve_format_with_deletions(
                        lines, flat_props, "# Chimera property", ["# Nandswap", "#", ""]
                    )

        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(lines)

        return True, None
    except Exception as exc:
        return False, str(exc)


def update_conditional_properties_in_section(
    lines: list[str],
    category: str,
    conditional_props: dict[str, Any],
) -> list[str]:
    section_header = f"# {category} property"
    next_headers = (
        ["# Chimera property", "# DHA property", "# Nandswap", "#", ""]
        if category == "LMKD"
        else ["# Nandswap", "#", ""]
    )

    start, end = find_block_boundaries(lines, section_header, next_headers)
    if start is None:
        return lines

    section_lines = lines[start:end]
    for prop_name, prop_data in conditional_props.items():
        section_lines = update_property_in_conditional_contexts(
            section_lines,
            prop_name,
            prop_data.get("values_by_context", {}),
            prop_data.get("selected_contexts", list(prop_data.get("values_by_context", {}).keys())),
        )

    return lines[:start] + section_lines + lines[end:]


def update_property_in_conditional_contexts(
    section_lines: list[str],
    prop_name: str,
    context_values: dict[str, str],
    selected_contexts: list[str],
) -> list[str]:
    index = 1
    while index < len(section_lines):
        line = section_lines[index].strip()
        if line.startswith(("ifneq", "ifdef", "ifndef")):
            context_key = f"[{line}]"
            if context_key in selected_contexts and context_key in context_values:
                index = update_properties_in_conditional_block(section_lines, index, prop_name, context_values[context_key])
            else:
                index = skip_conditional_block(section_lines, index)
        else:
            index += 1

    index = 1
    while index < len(section_lines):
        if section_lines[index].strip() == "else":
            else_key = "[else]"
            if else_key in selected_contexts and else_key in context_values:
                index = update_properties_in_else_block(section_lines, index, prop_name, context_values[else_key])
            else:
                index += 1
        else:
            index += 1

    return section_lines


def update_properties_in_conditional_block(
    lines: list[str],
    start_idx: int,
    prop_name: str,
    new_value: str,
) -> int:
    index = start_idx + 1
    while index < len(lines) and not lines[index].strip().startswith(("else", "endif")):
        parsed = parse_prop_line(lines[index])
        if parsed and parsed[0] == prop_name:
            lines[index] = format_property_line(lines[index], prop_name, new_value)
            return index + 1

        stripped = lines[index].strip()
        if not stripped or stripped.startswith(("endif", "ifneq", "ifdef", "ifndef")):
            break
        index += 1

    return index + 1


def update_properties_in_else_block(
    lines: list[str],
    start_idx: int,
    prop_name: str,
    new_value: str,
) -> int:
    index = start_idx + 1
    while index < len(lines) and not lines[index].strip().startswith("endif"):
        parsed = parse_prop_line(lines[index])
        if parsed and parsed[0] == prop_name:
            lines[index] = format_property_line(lines[index], prop_name, new_value)
            return index + 1

        stripped = lines[index].strip()
        if not stripped or stripped.startswith(("ifneq", "ifdef", "ifndef")):
            break
        index += 1

    return index + 1


def skip_conditional_block(lines: list[str], start_idx: int) -> int:
    index = start_idx + 1
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("endif"):
            return index + 1
        if line.startswith(("ifneq", "ifdef", "ifndef")):
            index = skip_conditional_block(lines, index)
        else:
            index += 1
    return index


def format_property_line(original_line: str, key: str, value: str) -> str:
    indent = original_line[: len(original_line) - len(original_line.lstrip())]
    has_backslash = original_line.rstrip("\n\r").endswith("\\")
    if has_backslash:
        return f"{indent}{key}={value} \\\n"
    return f"{indent}{key}={value}\n"

"""
File-operation compatibility helpers.

Property parsing, comparison, and writing now live in core.properties.*.
This module keeps the older import surface stable for GUI/process code while
retaining the local block-copy helpers used by bring-up workflows.
"""

import shutil
from datetime import datetime

from core.properties.comparer import (
    compare_properties_between_files as _compare_properties_between_files,
    compare_property_dict as _compare_property_dict,
    get_flat_properties_for_display,
)
from core.properties.parser import (
    enforce_structure_from_raw,
    extract_block_lines as _extract_block_lines,
    extract_properties_from_file,
    parse_block_with_conditionals as _parse_block_with_conditionals,
    parse_prop_line as _parse_prop_line,
    parse_properties_block,
    validate_conditional_structure_match,
)
from core.properties.writer import (
    add_remaining_properties,
    analyze_product_override_blocks,
    find_block_boundaries,
    get_default_indentation,
    is_conditional_aware_update as _is_conditional_aware_update,
    is_new_conditional_structure as _is_new_conditional_structure,
    skip_conditional_block as _skip_conditional_block,
    update_conditional_block_in_file as _update_conditional_block_in_file,
    update_conditional_properties_in_section as _update_conditional_properties_in_section,
    update_flat_props_in_section as _update_flat_props_in_section,
    update_product_override_block_with_deletions,
    update_properties_block_preserve_format_with_deletions,
    update_properties_conditional_aware as _update_properties_conditional_aware,
    update_properties_in_conditional_block as _update_properties_in_conditional_block,
    update_properties_in_else_block as _update_properties_in_else_block,
    update_properties_in_file,
    update_property_in_conditional_contexts as _update_property_in_conditional_contexts,
    update_v2_conditional_structure as _update_v2_conditional_structure,
)


def find_block_boundaries_improved(lines, start_header):
    """Find start and end indices of a block, case-insensitively."""
    start = end = None

    for idx, line in enumerate(lines):
        if line.strip().lower() == start_header.lower():
            start = idx
            break

    if start is None:
        return None, None

    for idx in range(start + 1, len(lines)):
        stripped = lines[idx].strip()
        if not stripped or stripped.startswith("#"):
            end = idx
            break

    if end is None:
        end = len(lines)

    return start, end


def extract_block_content(lines, start_header):
    """Extract content within a section, excluding the header."""
    start, end = find_block_boundaries_improved(lines, start_header)
    if start is None:
        return []
    return lines[start + 1 : end]


def replace_block_content(target_lines, new_content_lines, start_header):
    """Replace content within a section while preserving its header."""
    start, end = find_block_boundaries_improved(target_lines, start_header)
    if start is None:
        return target_lines + [start_header + "\n"] + new_content_lines
    return target_lines[: start + 1] + new_content_lines + target_lines[end:]


def extract_block(lines, start_header, next_header_list):
    """Extract block of lines between headers."""
    start = end = None
    for idx, line in enumerate(lines):
        if line.strip() == start_header:
            start = idx
            break
    if start is None:
        return []

    for idx in range(start + 1, len(lines)):
        if lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(lines)
    return lines[start:end]


def validate_properties_exist(file_path):
    """Check if LMKD/DHA and Chimera property sections exist in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        has_lmkd = "# LMKD property" in content or "# DHA property" in content
        has_chimera = "# Chimera property" in content
        return has_lmkd, has_chimera
    except Exception:
        return False, False


def replace_block(target_lines, block_lines, start_header, next_header_list):
    """Replace a block in target lines with another block."""
    start = end = None
    for idx, line in enumerate(target_lines):
        if line.strip() == start_header:
            start = idx
            break
    if start is None:
        return target_lines

    for idx in range(start + 1, len(target_lines)):
        if target_lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(target_lines)

    return target_lines[:start] + block_lines + target_lines[end:]


def update_lmkd_chimera(vince_path, target_path, log_callback):
    """Copy LMKD/DHA and Chimera block content from VINCE to a target file."""
    target_name = (
        "BENI"
        if "beni" in target_path.lower()
        else "FLUMEN"
        if "flumen" in target_path.lower()
        else "TARGET"
    )
    log_callback(f"[STEP 3] Updating LMKD and Chimera properties in {target_name}...")

    with open(vince_path, "r", encoding="utf-8") as file:
        vince_lines = file.readlines()
    with open(target_path, "r", encoding="utf-8") as file:
        target_lines = file.readlines()

    lmkd_content = extract_block_content(vince_lines, "# LMKD property")
    if not lmkd_content:
        lmkd_content = extract_block_content(vince_lines, "# DHA property")
    chimera_content = extract_block_content(vince_lines, "# Chimera property")

    has_lmkd = any(line.strip().lower() == "# lmkd property" for line in target_lines)
    has_dha = any(line.strip().lower() == "# dha property" for line in target_lines)
    has_chimera = any(line.strip().lower() == "# chimera property" for line in target_lines)

    updated_target = target_lines[:]

    if lmkd_content:
        if has_lmkd:
            updated_target = replace_block_content(updated_target, lmkd_content, "# LMKD property")
            log_callback(f"[OK] Updated LMKD property block in {target_name}")
        elif has_dha:
            updated_target = replace_block_content(updated_target, lmkd_content, "# DHA property")
            log_callback(f"[OK] Updated DHA property block in {target_name}")
        else:
            lmkd_header = (
                "# LMKD property"
                if any("# LMKD property" in line for line in vince_lines)
                else "# DHA property"
            )
            updated_target = replace_block_content(updated_target, lmkd_content, lmkd_header)
            log_callback(f"[OK] Added LMKD property block to {target_name}")
    else:
        log_callback("[INFO] No LMKD content found in VINCE, skipping LMKD update")

    if chimera_content:
        if has_chimera:
            updated_target = replace_block_content(updated_target, chimera_content, "# Chimera property")
            log_callback(f"[OK] Updated Chimera property block in {target_name}")
        else:
            updated_target = replace_block_content(updated_target, chimera_content, "# Chimera property")
            log_callback(f"[OK] Added Chimera property block to {target_name}")
    else:
        log_callback("[INFO] No Chimera content found in VINCE, skipping Chimera update")

    with open(target_path, "w", encoding="utf-8") as file:
        file.writelines(updated_target)

    log_callback(f"[OK] Updated {target_name} file successfully.")


def create_backup(file_path):
    """Create backup of file with timestamp."""
    backup_path = file_path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copyfile(file_path, backup_path)
    return backup_path


def compare_properties_between_files(file1_path, file2_path):
    """Compare properties between two files and return differences."""
    return _compare_properties_between_files(file1_path, file2_path, extract_properties_from_file)


def compare_property_dict(dict1, dict2, category):
    """Compare two property dictionaries."""
    return _compare_property_dict(dict1, dict2, category)


def update_properties_block_preserve_format(lines, new_properties, start_header, next_header_list):
    """Backward-compatible wrapper for the deletion-aware block writer."""
    return update_properties_block_preserve_format_with_deletions(
        lines, new_properties, start_header, next_header_list
    )


def update_properties_block(lines, new_properties, start_header, next_header_list):
    """Legacy simple block replacement."""
    start = end = None
    for idx, line in enumerate(lines):
        if line.strip() == start_header:
            start = idx
            break
    if start is None:
        return lines

    for idx in range(start + 1, len(lines)):
        if lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(lines)

    new_block = [lines[start]]
    for key, value in new_properties.items():
        new_block.append(f"{key}={value}\n")

    if end < len(lines) and lines[end].strip():
        new_block.append("\n")

    return lines[:start] + new_block + lines[end:]


def analyze_conditional_structure(file_content):
    """
    Analyze conditional blocks in property sections for GUI display.
    """
    lines = file_content.split("\n") if isinstance(file_content, str) else file_content
    conditional_sections = {}

    for section_header in ["# LMKD property", "# Chimera property", "# DHA property"]:
        section_data = analyze_section_conditional_blocks(lines, section_header)
        if section_data:
            section_name = section_header.replace("# ", "").replace(" property", "")
            conditional_sections[section_name] = section_data

    return conditional_sections


def analyze_section_conditional_blocks(lines, section_header):
    """Analyze conditional blocks in a specific section."""
    start_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == section_header:
            start_idx = idx
            break

    if start_idx is None:
        return None

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        stripped = lines[idx].strip()
        if not stripped or (stripped.startswith("#") and section_header not in stripped):
            if idx > start_idx + 1:
                end_idx = idx
                break

    section_lines = lines[start_idx:end_idx]
    conditional_blocks = []
    index = 1

    while index < len(section_lines):
        line = section_lines[index].strip()

        if line.startswith(("ifneq", "ifdef", "ifndef")):
            condition_text = line
            properties = []
            index += 1

            while index < len(section_lines):
                prop_line = section_lines[index].strip()
                if prop_line.startswith(("else", "endif", "ifneq")):
                    break
                parsed = _parse_prop_line(prop_line)
                if parsed:
                    key, value = parsed
                    properties.append(
                        {"key": key, "value": value, "line_number": start_idx + index}
                    )
                index += 1

            else_properties = []
            if index < len(section_lines) and section_lines[index].strip() == "else":
                index += 1
                while index < len(section_lines):
                    prop_line = section_lines[index].strip()
                    if prop_line.startswith(("endif", "ifneq")):
                        break
                    parsed = _parse_prop_line(prop_line)
                    if parsed:
                        key, value = parsed
                        else_properties.append(
                            {"key": key, "value": value, "line_number": start_idx + index}
                        )
                    index += 1

            conditional_blocks.append(
                {
                    "condition": condition_text,
                    "type": "if",
                    "properties": properties,
                    "else_properties": else_properties or None,
                }
            )

            if index < len(section_lines) and section_lines[index].strip() == "endif":
                index += 1
        else:
            index += 1

    return {"header_line": start_idx, "blocks": conditional_blocks}


def test_conditional_parser():
    """Small manual smoke test retained for backward compatibility."""
    test_content = """# LMKD property
ifneq ($(filter %zn %ctc %zm %zc %zcx, $(TARGET_PRODUCT)), )
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.enable_upgrade_criadj=true \\
    ro.slmk.use_bg_keeping_policy_light=true
else
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.use_bg_keeping_policy=true
endif
"""
    return analyze_conditional_structure(test_content)

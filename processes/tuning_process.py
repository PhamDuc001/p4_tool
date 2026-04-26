"""
Backward-compatible tuning process wrappers.

The tuning workflow now lives in services.tuning_service. This module keeps the
older import surface stable for GUI/process callers that have not been migrated.
"""

from __future__ import annotations

from core.properties.comparer import (
    compare_properties as _compare_properties,
    compare_property_dict as _compare_property_dict,
)
from core.properties.parser import (
    extract_properties_from_file as _extract_properties_from_file,
    parse_properties_block as _parse_properties_block,
)
from services.tuning_service import TuningService


_DEFAULT_SERVICE = TuningService()


def _service() -> TuningService:
    return _DEFAULT_SERVICE


def generate_tuning_description(original_properties, current_properties):
    return _service().generate_tuning_description(original_properties, current_properties)


def analyze_property_changes(original_dict, current_dict):
    return _service()._analyze_property_changes(original_dict, current_dict)


def build_category_description_part(category, changes):
    return _service()._build_category_description_part(category, changes)


def resolve_tuning_input_to_depot_path(user_input, log_callback=None):
    return _service().resolve_input_to_depot_path(user_input, log_callback)


def map_three_depots_silent(depot1, depot2, depot3):
    return _service()._map_three_depots_silent(depot1, depot2, depot3)


def auto_resolve_missing_depot_paths(original_depot_paths, log_callback=None):
    return _service().auto_resolve_missing_depot_paths(
        original_depot_paths,
        log_callback=log_callback,
    )


def apply_tuning_changes_enhanced_with_auto_resolve(
    current_properties,
    original_depot_paths,
    log_callback,
    progress_callback=None,
    error_callback=None,
    original_properties=None,
    confirm_reopen_callback=None,
):
    """Apply property changes to all target files with auto-resolve for missing paths."""
    result = _service().apply_changes(
        current_properties,
        original_depot_paths,
        log_callback=log_callback,
        progress_callback=progress_callback,
        original_properties=original_properties,
        confirm_reopen_callback=confirm_reopen_callback,
    )
    if not result.success and error_callback:
        error_callback("Apply Tuning Error", result.message)
    return result.success


def load_properties_for_tuning_enhanced(
    beni_input,
    flumen_input,
    rel_input,
    progress_callback=None,
    error_callback=None,
    info_callback=None,
):
    """
    Load and compare properties from BENI, FLUMEN, and REL files.

    Returns the legacy tuple: (comparison_data, merged_properties).
    """
    try:
        result = _service().load_properties(
            beni_input,
            flumen_input,
            rel_input,
            progress_callback=progress_callback,
        )
        return result.comparison_data, result.merged_properties
    except Exception as exc:
        if error_callback:
            error_callback("Load Properties Error", str(exc))
        return None


def apply_tuning_changes_enhanced(
    current_properties,
    depot_paths_dict,
    log_callback,
    progress_callback=None,
    error_callback=None,
):
    """Apply property changes to all target files (BENI, FLUMEN, REL)."""
    return apply_tuning_changes_enhanced_with_auto_resolve(
        current_properties,
        depot_paths_dict,
        log_callback,
        progress_callback,
        error_callback,
    )


def load_properties_for_tuning(
    beni_depot_path,
    flumen_depot_path,
    progress_callback=None,
    error_callback=None,
    info_callback=None,
):
    """Legacy function: load properties from BENI and FLUMEN only."""
    try:
        result = _service().load_properties(
            beni_depot_path,
            flumen_depot_path,
            "",
            progress_callback=progress_callback,
        )

        if (
            info_callback
            and "BENI" in result.comparison_data
            and "FLUMEN" in result.comparison_data
        ):
            differences = compare_properties(
                result.comparison_data["BENI"],
                result.comparison_data["FLUMEN"],
            )
            if differences:
                diff_message = (
                    "Properties differ between BENI and FLUMEN:\n\n"
                    + "\n".join(differences)
                )
                info_callback("Properties Comparison", diff_message)

        return result.merged_properties
    except Exception as exc:
        if error_callback:
            error_callback("Load Properties Error", str(exc))
        return None


def apply_tuning_changes(
    current_properties,
    original_depot_paths,
    log_callback,
    progress_callback=None,
    error_callback=None,
):
    """Legacy function: apply changes to original depot paths."""
    return apply_tuning_changes_enhanced_with_auto_resolve(
        current_properties,
        original_depot_paths,
        log_callback,
        progress_callback,
        error_callback,
    )


def _legacy_extract_properties_from_file(file_path):
    """Extract LMKD and Chimera properties from file."""
    return _extract_properties_from_file(file_path)


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


def parse_properties_block(block_lines):
    """Parse property block and extract key-value pairs."""
    return _parse_properties_block(block_lines)


def compare_properties(beni_props, flumen_props):
    """Compare properties between BENI and FLUMEN files."""
    return _compare_properties(
        beni_props,
        flumen_props,
        first_label="BENI",
        second_label="FLUMEN",
    ) or []


def compare_property_dict(dict1, dict2, category):
    """Compare two property dictionaries."""
    return _compare_property_dict(
        dict1,
        dict2,
        category,
        first_label="BENI",
        second_label="FLUMEN",
    )

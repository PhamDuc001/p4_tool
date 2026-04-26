"""
Canonical property parser, comparer, and writer APIs.
"""

from core.properties.comparer import (
    compare_properties,
    compare_properties_between_files,
    compare_property_dict,
    get_flat_properties_for_display,
)
from core.properties.parser import (
    enforce_structure_from_raw,
    extract_properties_from_file,
    extract_properties_from_lines,
    parse_properties_block,
    validate_conditional_structure_match,
)
from core.properties.writer import update_properties_in_file

__all__ = [
    "compare_properties",
    "compare_properties_between_files",
    "compare_property_dict",
    "enforce_structure_from_raw",
    "extract_properties_from_file",
    "extract_properties_from_lines",
    "get_flat_properties_for_display",
    "parse_properties_block",
    "update_properties_in_file",
    "validate_conditional_structure_match",
]

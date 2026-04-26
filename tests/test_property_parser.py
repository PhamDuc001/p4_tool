from core.properties.parser import (
    extract_properties_from_file,
    extract_properties_from_lines,
    parse_properties_block,
    validate_conditional_structure_match,
)


def test_extract_properties_from_lines_handles_conditional_and_flat_sections():
    lines = [
        "# LMKD property\n",
        "ifneq ($(filter usa%, $(PROJECT_REGION)), )\n",
        "PRODUCT_PROPERTY_OVERRIDES += \\\n",
        "    ro.slmk.policy=if-value \\\n",
        "else\n",
        "PRODUCT_PROPERTY_OVERRIDES += \\\n",
        "    ro.slmk.policy=else-value\n",
        "endif\n",
        "\n",
        "PRODUCT_PROPERTY_OVERRIDES += \\\n",
        "    ro.slmk.plg_key=1\n",
        "# Chimera property\n",
        "PRODUCT_PROPERTY_OVERRIDES += \\\n",
        "    ro.slmk.chimera_strategy_8gb=1024\n",
    ]

    parsed = extract_properties_from_lines(lines)

    assert parsed["LMKD"]["_flat"] == {"ro.slmk.plg_key": "1"}
    assert parsed["LMKD"]["_conditional"][0]["if_props"] == {"ro.slmk.policy": "if-value"}
    assert parsed["LMKD"]["_conditional"][0]["else_props"] == {"ro.slmk.policy": "else-value"}
    assert parsed["Chimera"]["_flat"] == {"ro.slmk.chimera_strategy_8gb": "1024"}


def test_extract_properties_from_file_uses_dha_fallback(tmp_path):
    target = tmp_path / "device_common.mk"
    target.write_text(
        """# DHA property
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.dha_2ndprop_thMB=4096
""",
        encoding="utf-8",
    )

    parsed = extract_properties_from_file(str(target))

    assert parsed["LMKD"]["_flat"] == {"ro.slmk.dha_2ndprop_thMB": "4096"}
    assert parsed["Chimera"] == {"_flat": {}, "_conditional": [], "_raw_lines": ""}


def test_validate_conditional_structure_match_detects_mismatch():
    first = {
        "LMKD": {"_conditional": [{"condition": "ifneq (a)", "if_props": {}, "else_props": {}}]},
        "Chimera": {"_conditional": []},
    }
    second = {
        "LMKD": {"_conditional": [{"condition": "ifneq (b)", "if_props": {}, "else_props": {}}]},
        "Chimera": {"_conditional": []},
    }

    match, diffs = validate_conditional_structure_match(first, second)

    assert not match
    assert "LMKD block 0: condition mismatch ('ifneq (a)' vs 'ifneq (b)')" in diffs


def test_parse_properties_block_ignores_control_lines_and_comments():
    block = [
        "# LMKD property\n",
        "ifneq ($(x),1)\n",
        "PRODUCT_PROPERTY_OVERRIDES += \\\n",
        "    ro.slmk.plg_key=1 \\\n",
        "else\n",
        "    # comment\n",
        "    ro.slmk.dha_2ndprop_thMB=4096\n",
        "endif\n",
    ]

    parsed = parse_properties_block(block)

    assert parsed == {
        "ro.slmk.plg_key": "1",
        "ro.slmk.dha_2ndprop_thMB": "4096",
    }

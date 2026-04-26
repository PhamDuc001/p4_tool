from core.properties.comparer import compare_properties_between_files
from core.properties.parser import extract_properties_from_file
from core.properties.writer import update_properties_in_file


def test_update_selected_conditional_context_only(tmp_path):
    target = tmp_path / "device_common.mk"
    target.write_text(
        """# Chimera property
ifneq ($(filter usa%, $(PROJECT_REGION)), )
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.chimera_strategy_8gb=1024,24,10,2550
else
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.chimera_strategy_8gb=1228,24,10,2550
endif
""",
        encoding="utf-8",
    )

    success, error = update_properties_in_file(
        str(target),
        {
            "Chimera": {
                "ro.slmk.chimera_strategy_8gb": {
                    "values_by_context": {
                        "[ifneq ($(filter usa%, $(PROJECT_REGION)), )]": "2048,32,15,3000",
                        "[else]": "1228,24,10,2550",
                    },
                    "selected_contexts": ["[ifneq ($(filter usa%, $(PROJECT_REGION)), )]"],
                }
            }
        },
    )

    content = target.read_text(encoding="utf-8")
    assert success, error
    assert "ro.slmk.chimera_strategy_8gb=2048,32,15,3000" in content
    assert "ro.slmk.chimera_strategy_8gb=1228,24,10,2550" in content
    assert content.count("ifneq") == 1
    assert content.count("else") == 1
    assert content.count("endif") == 1


def test_compare_properties_uses_flat_display_values(tmp_path):
    file1 = tmp_path / "one.mk"
    file2 = tmp_path / "two.mk"
    file1.write_text(
        """# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.plg_key=1
""",
        encoding="utf-8",
    )
    file2.write_text(
        """# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.plg_key=2
""",
        encoding="utf-8",
    )

    differences = compare_properties_between_files(
        str(file1),
        str(file2),
        extract_properties_from_file,
    )

    assert differences == ["LMKD.ro.slmk.plg_key: File1='1' vs File2='2'"]

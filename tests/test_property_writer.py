from core.properties.writer import update_properties_in_file


def test_update_properties_in_file_updates_flat_properties(tmp_path):
    target = tmp_path / "device_common.mk"
    target.write_text(
        """# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.plg_key=1 \\
    ro.slmk.dha_2ndprop_thMB=4096

# Chimera property
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.chimera_strategy_8gb=1024
""",
        encoding="utf-8",
    )

    success, error = update_properties_in_file(
        str(target),
        {
            "LMKD": {"ro.slmk.plg_key": "2"},
            "Chimera": {"ro.slmk.chimera_strategy_8gb": "2048"},
        },
    )

    content = target.read_text(encoding="utf-8")
    assert success, error
    assert "ro.slmk.plg_key=2" in content
    assert "ro.slmk.chimera_strategy_8gb=2048" in content


def test_update_properties_in_file_supports_legacy_context_updates(tmp_path):
    target = tmp_path / "device_common.mk"
    target.write_text(
        """# Chimera property
ifneq ($(filter usa%, $(PROJECT_REGION)), )
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.chimera_strategy_12gb=1024,28,14,2857
else
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.chimera_strategy_12gb=1228,28,14,2857
endif
""",
        encoding="utf-8",
    )

    success, error = update_properties_in_file(
        str(target),
        {
            "Chimera": {
                "ro.slmk.chimera_strategy_12gb": {
                    "values_by_context": {
                        "[ifneq ($(filter usa%, $(PROJECT_REGION)), )]": "2048,32,15,3000",
                        "[else]": "2456,36,20,3500",
                    },
                    "selected_contexts": ["[else]"],
                }
            }
        },
    )

    content = target.read_text(encoding="utf-8")
    assert success, error
    assert "ro.slmk.chimera_strategy_12gb=1024,28,14,2857" in content
    assert "ro.slmk.chimera_strategy_12gb=2456,36,20,3500" in content

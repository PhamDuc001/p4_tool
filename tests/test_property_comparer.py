from core.properties.comparer import (
    compare_properties,
    compare_property_dict,
    get_flat_properties_for_display,
)


def test_get_flat_properties_supports_conditional_structure():
    properties = {
        "LMKD": {
            "_flat": {"ro.slmk.plg_key": "1"},
            "_conditional": [
                {
                    "condition": "ifneq (...)",
                    "if_props": {"ro.slmk.policy": "if-value"},
                    "else_props": {"ro.slmk.policy": "else-value"},
                }
            ],
        }
    }

    flat = get_flat_properties_for_display(properties)

    assert flat["LMKD"] == {
        "ro.slmk.plg_key": "1",
        "ro.slmk.policy": "else-value",
    }


def test_get_flat_properties_supports_legacy_flat_structure():
    properties = {
        "LMKD": {"ro.slmk.plg_key": "1"},
        "Chimera": {"ro.slmk.chimera_strategy_8gb": "1024"},
    }

    flat = get_flat_properties_for_display(properties)

    assert flat == properties


def test_compare_property_dict_uses_custom_labels_and_sorted_keys():
    differences = compare_property_dict(
        {"b": "1", "a": "1"},
        {"b": "2", "c": "3"},
        "LMKD",
        first_label="BENI",
        second_label="FLUMEN",
    )

    assert differences == [
        "LMKD.a: BENI='1' vs FLUMEN='<missing>'",
        "LMKD.b: BENI='1' vs FLUMEN='2'",
        "LMKD.c: BENI='<missing>' vs FLUMEN='3'",
    ]


def test_compare_properties_supports_legacy_flat_inputs():
    differences = compare_properties(
        {"LMKD": {"ro.slmk.plg_key": "1"}, "Chimera": {}},
        {"LMKD": {"ro.slmk.plg_key": "2"}, "Chimera": {}},
        first_label="BENI",
        second_label="FLUMEN",
    )

    assert differences == ["LMKD.ro.slmk.plg_key: BENI='1' vs FLUMEN='2'"]

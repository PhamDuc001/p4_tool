from services.tuning_service import TuningService


def sample_properties(value="1", conditional_value="if-value", else_value="else-value"):
    return {
        "LMKD": {
            "_flat": {"ro.slmk.plg_key": value},
            "_conditional": [
                {
                    "condition": "ifneq ($(REGION),usa)",
                    "if_props": {"ro.slmk.policy": conditional_value},
                    "else_props": {"ro.slmk.policy": else_value},
                }
            ],
            "_raw_lines": "# LMKD property\n",
        },
        "Chimera": {"_flat": {}, "_conditional": [], "_raw_lines": ""},
    }


def test_generate_tuning_description_handles_v2_property_structures():
    service = TuningService()

    original = sample_properties()
    current = sample_properties(conditional_value="new-if-value")

    description = service.generate_tuning_description(original, current)

    assert description == "Tuning value ro.slmk.policy"


def test_load_properties_returns_merged_metadata():
    mapped = []
    synced = []
    locals_by_depot = {
        "//depot/beni/device_common.mk": "C:/beni/device_common.mk",
        "//depot/flumen/device_common.mk": "C:/flumen/device_common.mk",
    }
    properties_by_local = {
        "C:/beni/device_common.mk": sample_properties(value="1"),
        "C:/flumen/device_common.mk": sample_properties(value="2"),
    }

    service = TuningService(
        validate_depot_path_fn=lambda path: True,
        validate_device_common_mk_path_fn=lambda path: (True, True),
        is_workspace_like_fn=lambda text: False,
        map_single_depot_fn=lambda depot: mapped.append(("single", depot)),
        map_two_depots_fn=lambda first, second: mapped.append(("double", first, second)),
        sync_file_fn=lambda depot: synced.append(depot),
        depot_to_local_path_fn=lambda depot: locals_by_depot[depot],
        extract_properties_fn=lambda local_path: properties_by_local[local_path],
        p4_client=object(),
    )

    result = service.load_properties(
        "//depot/beni/device_common.mk",
        "//depot/flumen/device_common.mk",
        "",
    )

    assert mapped == [("double", "//depot/beni/device_common.mk", "//depot/flumen/device_common.mk")]
    assert synced == ["//depot/beni/device_common.mk", "//depot/flumen/device_common.mk"]
    assert set(result.comparison_data.keys()) == {"BENI", "FLUMEN"}
    assert result.merged_properties["_metadata"]["depot_paths"] == {
        "BENI": "//depot/beni/device_common.mk",
        "FLUMEN": "//depot/flumen/device_common.mk",
    }
    assert result.merged_properties["LMKD"]["_flat"]["ro.slmk.plg_key"] == "1"


def test_build_apply_confirmation_for_rel_mentions_auto_resolve():
    service = TuningService()

    confirmation = service.build_apply_confirmation(
        {"REL": "//depot/rel/device_common.mk"},
        sample_properties(value="2"),
        sample_properties(value="1"),
    )

    assert confirmation.title == "Confirm Apply with Auto-Resolve"
    assert "REL -> FLUMEN -> BENI" in confirmation.message
    assert "[MODIFIED] LMKD[flat].ro.slmk.plg_key: 1 -> 2" in confirmation.message


def test_apply_changes_returns_operation_result_and_passes_confirm_callback():
    checkout_calls = []
    update_calls = []

    def checkout_file(depot_path, changelist_id, log_callback=None, confirm_reopen_callback=None):
        checkout_calls.append((depot_path, changelist_id, confirm_reopen_callback))
        assert confirm_reopen_callback is not None

    def update_properties(local_path, properties):
        update_calls.append((local_path, properties))
        return True, None

    service = TuningService(
        map_single_depot_fn=lambda depot: None,
        sync_file_fn=lambda depot: None,
        create_changelist_fn=lambda description: "12345",
        checkout_file_fn=checkout_file,
        depot_to_local_path_fn=lambda depot: "C:/ws/device_common.mk",
        extract_properties_fn=lambda local_path: sample_properties(),
        validate_structure_match_fn=lambda first, second: (True, []),
        update_properties_fn=update_properties,
        p4_client=object(),
    )

    result = service.apply_changes(
        sample_properties(value="9"),
        {"BENI": "//depot/beni/device_common.mk"},
        log_callback=lambda message: None,
        original_properties=sample_properties(value="1"),
        confirm_reopen_callback=lambda depot_path, current_cl, target_cl: True,
    )

    assert result.success is True
    assert result.changelist_id == "12345"
    assert result.changed_files == ["BENI"]
    assert checkout_calls[0][0] == "//depot/beni/device_common.mk"
    assert update_calls[0][0] == "C:/ws/device_common.mk"

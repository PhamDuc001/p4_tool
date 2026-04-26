"""
Service layer for tuning-property workflows.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from config.p4_config import depot_to_local_path, get_client_name
from core.p4_client import get_default_p4_client
from core.p4_operations import (
    checkout_file_silent,
    create_changelist_silent,
    find_device_common_mk_path,
    get_integration_source_depot_path,
    is_workspace_like,
    map_single_depot,
    map_two_depots_silent,
    sync_file_silent,
    validate_depot_path,
    validate_device_common_mk_path,
)
from core.properties import (
    enforce_structure_from_raw,
    extract_properties_from_file,
    update_properties_in_file,
    validate_conditional_structure_match,
)

from services.models import ConfirmationRequest, OperationResult, TuningLoadResult


PropertyTree = dict[str, Any]
ConfirmReopenCallback = Callable[[str, str, str], bool]
LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]


class TuningService:
    def __init__(
        self,
        *,
        validate_depot_path_fn: Callable[[str], bool] = validate_depot_path,
        validate_device_common_mk_path_fn: Callable[[str], tuple[bool, bool]] = validate_device_common_mk_path,
        is_workspace_like_fn: Callable[[str], bool] = is_workspace_like,
        find_device_common_mk_path_fn: Callable[[str, LogCallback | None], tuple[str | None, list[str]]] = find_device_common_mk_path,
        map_single_depot_fn: Callable[[str], None] = map_single_depot,
        map_two_depots_fn: Callable[[str, str], None] = map_two_depots_silent,
        sync_file_fn: Callable[[str], None] = sync_file_silent,
        create_changelist_fn: Callable[[str], str] = create_changelist_silent,
        checkout_file_fn: Callable[..., None] = checkout_file_silent,
        get_integration_source_depot_path_fn: Callable[[str, LogCallback | None], str | None] = get_integration_source_depot_path,
        depot_to_local_path_fn: Callable[[str], str] = depot_to_local_path,
        extract_properties_fn: Callable[[str], PropertyTree | None] = extract_properties_from_file,
        validate_structure_match_fn: Callable[[PropertyTree, PropertyTree | None], tuple[bool, list[str]]] = validate_conditional_structure_match,
        enforce_structure_fn: Callable[[str, PropertyTree], tuple[bool, str | None]] = enforce_structure_from_raw,
        update_properties_fn: Callable[[str, PropertyTree], tuple[bool, str | None]] = update_properties_in_file,
        p4_client=None,
    ):
        self.validate_depot_path = validate_depot_path_fn
        self.validate_device_common_mk_path = validate_device_common_mk_path_fn
        self.is_workspace_like = is_workspace_like_fn
        self.find_device_common_mk_path = find_device_common_mk_path_fn
        self.map_single_depot = map_single_depot_fn
        self.map_two_depots = map_two_depots_fn
        self.sync_file = sync_file_fn
        self.create_changelist = create_changelist_fn
        self.checkout_file = checkout_file_fn
        self.get_integration_source_depot_path = get_integration_source_depot_path_fn
        self.depot_to_local_path = depot_to_local_path_fn
        self.extract_properties = extract_properties_fn
        self.validate_structure_match = validate_structure_match_fn
        self.enforce_structure = enforce_structure_fn
        self.update_properties = update_properties_fn
        self.p4_client = p4_client or get_default_p4_client()

    def generate_tuning_description(
        self,
        original_properties: PropertyTree | None,
        current_properties: PropertyTree | None,
    ) -> str:
        if not original_properties or not current_properties:
            return "Tuning - Apply property changes"

        description_parts: list[str] = []
        for category in ("LMKD", "Chimera"):
            changes = self._analyze_property_changes(
                original_properties.get(category, {}),
                current_properties.get(category, {}),
            )
            part = self._build_category_description_part(category, changes)
            if part:
                description_parts.append(part)

        if not description_parts:
            return "Tuning - No changes detected"

        return " & ".join(description_parts)

    def resolve_input_to_depot_path(
        self,
        user_input: str,
        log_callback: LogCallback | None = None,
    ) -> str:
        if not user_input:
            return ""

        user_input = user_input.strip()

        if user_input.startswith("//"):
            self._log(log_callback, f"[TUNING] Detected depot path: {user_input}")
            if not self.validate_depot_path(user_input):
                raise RuntimeError(f"Depot path does not exist: {user_input}")

            exists, is_device_common = self.validate_device_common_mk_path(user_input)
            if not exists:
                raise RuntimeError(f"Depot path does not exist: {user_input}")
            if not is_device_common:
                raise RuntimeError(f"Path must be a device_common.mk file: {user_input}")

            self._log(log_callback, f"[OK] Valid depot path: {user_input}")
            return user_input

        if self.is_workspace_like(user_input):
            self._log(log_callback, f"[TUNING] Detected workspace: {user_input}")
            try:
                resolved_path, _ = self.find_device_common_mk_path(user_input, log_callback)
            except Exception as exc:
                raise RuntimeError(f"Workspace resolution failed: {exc}") from exc

            if not resolved_path:
                raise RuntimeError(f"Workspace resolution failed: no device_common.mk path found for {user_input}")

            self._log(log_callback, f"[OK] Resolved workspace to device_common.mk: {resolved_path}")
            return resolved_path

        raise RuntimeError(
            f"Input must be depot path (//depot/...) or workspace (TEMPLATE_*): {user_input}"
        )

    def load_properties(
        self,
        beni_input: str,
        flumen_input: str,
        rel_input: str,
        *,
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
    ) -> TuningLoadResult:
        paths_to_process: dict[str, str] = {}

        for path_name, user_input in (
            ("BENI", beni_input),
            ("FLUMEN", flumen_input),
            ("REL", rel_input),
        ):
            if not user_input:
                continue
            resolved_path = self.resolve_input_to_depot_path(user_input, log_callback)
            if resolved_path:
                paths_to_process[path_name] = resolved_path

        if not paths_to_process:
            raise RuntimeError("At least one valid input (workspace or depot path) is required.")

        self._progress(progress_callback, 20)

        depot_paths_list = list(paths_to_process.values())
        self._map_depot_paths(depot_paths_list)
        for depot_path in depot_paths_list:
            self.sync_file(depot_path)

        self._progress(progress_callback, 60)

        comparison_data: dict[str, Any] = {}
        all_depot_paths: dict[str, str] = {}

        for path_name, depot_path in paths_to_process.items():
            local_path = self.depot_to_local_path(depot_path)
            properties = self.extract_properties(local_path)
            if not properties:
                raise RuntimeError(
                    f"{path_name} file does not contain LMKD or Chimera properties"
                )

            property_snapshot = self._copy_property_tree(properties)
            per_path_properties = self._copy_property_tree(properties)
            per_path_properties["_metadata"] = {
                "depot_paths": {path_name: depot_path},
                "original_properties": property_snapshot,
            }
            comparison_data[path_name] = per_path_properties
            all_depot_paths[path_name] = depot_path

        self._progress(progress_callback, 80)

        first_path = next(iter(comparison_data))
        merged_properties = self._copy_property_tree(comparison_data[first_path])
        merged_snapshot = self._copy_property_tree(merged_properties)
        merged_snapshot.pop("_metadata", None)
        merged_properties["_metadata"] = {
            "depot_paths": all_depot_paths,
            "original_properties": merged_snapshot,
        }

        self._progress(progress_callback, 100)
        return TuningLoadResult(
            comparison_data=comparison_data,
            merged_properties=merged_properties,
        )

    def properties_are_identical(self, comparison_data: dict[str, Any] | None) -> bool:
        if not comparison_data:
            return True

        valid_paths = [path for path in ("BENI", "FLUMEN", "REL") if path in comparison_data]
        if len(valid_paths) <= 1:
            return True

        first_path = valid_paths[0]
        first_props = self._without_metadata(comparison_data[first_path])
        for path in valid_paths[1:]:
            if self._without_metadata(comparison_data[path]) != first_props:
                return False

        return True

    def properties_unchanged(
        self,
        original_properties: PropertyTree,
        current_properties: PropertyTree,
    ) -> bool:
        if not original_properties:
            return True

        for category in ("LMKD", "Chimera"):
            original_category = original_properties.get(category, {})
            current_category = current_properties.get(category, {})

            if isinstance(original_category, dict) and "_flat" in original_category:
                if original_category.get("_flat", {}) != current_category.get("_flat", {}):
                    return False
                original_conditional = original_category.get("_conditional", [])
                current_conditional = current_category.get("_conditional", [])
                if len(original_conditional) != len(current_conditional):
                    return False
                for original_block, current_block in zip(original_conditional, current_conditional):
                    if original_block.get("if_props") != current_block.get("if_props"):
                        return False
                    if original_block.get("else_props") != current_block.get("else_props"):
                        return False
            elif original_category != current_category:
                return False

        return True

    def summarize_changes(
        self,
        original_properties: PropertyTree,
        current_properties: PropertyTree,
    ) -> str:
        changes: list[str] = []

        for category in ("LMKD", "Chimera"):
            original_category = original_properties.get(category, {})
            current_category = current_properties.get(category, {})

            if isinstance(original_category, dict) and "_flat" in original_category:
                changes.extend(
                    self._compare_property_categories(
                        original_category.get("_flat", {}),
                        current_category.get("_flat", {}),
                        f"{category}[flat]",
                    )
                )

                original_conditional = original_category.get("_conditional", [])
                current_conditional = current_category.get("_conditional", [])
                for index, (original_block, current_block) in enumerate(
                    zip(original_conditional, current_conditional)
                ):
                    condition_label = original_block.get("condition", f"block{index}")[:40]
                    changes.extend(
                        self._compare_property_categories(
                            original_block.get("if_props", {}),
                            current_block.get("if_props", {}),
                            f"{category}[if: {condition_label}]",
                        )
                    )
                    if (
                        original_block.get("else_props") is not None
                        or current_block.get("else_props") is not None
                    ):
                        changes.extend(
                            self._compare_property_categories(
                                original_block.get("else_props") or {},
                                current_block.get("else_props") or {},
                                f"{category}[else]",
                            )
                        )
            else:
                changes.extend(
                    self._compare_property_categories(
                        original_category,
                        current_category,
                        category,
                    )
                )

        return "\n".join(changes)

    def build_apply_confirmation(
        self,
        original_depot_paths: dict[str, str],
        current_properties: PropertyTree,
        original_properties: PropertyTree,
    ) -> ConfirmationRequest:
        changes_summary = self.summarize_changes(original_properties, current_properties)

        if len(original_depot_paths) == 1:
            single_path = next(iter(original_depot_paths))
            message = f"You loaded properties from {single_path} only.\n\n"

            if single_path == "REL":
                message += "Auto-resolve will find FLUMEN and BENI paths using integration history.\n"
                message += "Changes will be applied to: REL -> FLUMEN -> BENI\n\n"
            elif single_path == "FLUMEN":
                message += "Auto-resolve will find BENI path using integration history.\n"
                message += "Changes will be applied to: FLUMEN -> BENI\n\n"
            else:
                message += "No auto-resolve needed for BENI.\n"
                message += "Changes will be applied to: BENI only\n\n"

            if changes_summary:
                message += f"Changes to apply:\n{changes_summary}\n\n"

            message += "Do you want to continue?"
            return ConfirmationRequest(
                title="Confirm Apply with Auto-Resolve",
                message=message,
                options=["Apply", "Cancel"],
            )

        message = "This will apply all property changes to the loaded paths and create a pending changelist.\n\n"
        if changes_summary:
            message = f"The following changes will be applied to all loaded paths:\n\n{changes_summary}\n\n" + message
        message += "Do you want to continue?"
        return ConfirmationRequest(
            title="Confirm Apply Changes",
            message=message,
            options=["Apply", "Cancel"],
        )

    def apply_changes(
        self,
        current_properties: PropertyTree,
        original_depot_paths: dict[str, str],
        *,
        log_callback: LogCallback | None,
        progress_callback: ProgressCallback | None = None,
        original_properties: PropertyTree | None = None,
        confirm_reopen_callback: ConfirmReopenCallback | None = None,
    ) -> OperationResult:
        try:
            properties_to_apply = {
                key: value
                for key, value in current_properties.items()
                if key != "_metadata"
            }

            self._log(log_callback, "[TUNING] Starting apply tuning changes with auto-resolve...")
            self._log(
                log_callback,
                "[INFO] Properties to apply: "
                f"LMKD={self._count_properties(properties_to_apply.get('LMKD', {}))}, "
                f"Chimera={self._count_properties(properties_to_apply.get('Chimera', {}))}",
            )
            self._progress(progress_callback, 5)

            if len(original_depot_paths) == 1:
                self._log(log_callback, "[AUTO-RESOLVE] Single path detected - performing auto-resolve...")
                resolved_depot_paths = self.auto_resolve_missing_depot_paths(
                    original_depot_paths,
                    log_callback=log_callback,
                )
            else:
                self._log(log_callback, "[INFO] Multiple paths provided - skipping auto-resolve")
                resolved_depot_paths = dict(original_depot_paths)

            self._progress(progress_callback, 15)

            description = "Tuning - Apply property changes to all paths"
            if original_properties:
                description = self.generate_tuning_description(original_properties, current_properties)
                self._log(log_callback, f"[DESCRIPTION] Generated changelist description: {description}")

            self._log(log_callback, "[STEP 1] Creating pending changelist for tuning changes...")
            changelist_id = self.create_changelist(description)
            self._log(log_callback, f"[OK] Created changelist {changelist_id}")
            self._progress(progress_callback, 25)

            depot_paths_list = list(resolved_depot_paths.values())
            self._map_depot_paths(depot_paths_list)

            processed_files: list[str] = []
            progress_step = max(1, 60 // max(1, len(resolved_depot_paths)))

            for index, (path_name, depot_path) in enumerate(resolved_depot_paths.items(), start=1):
                self._log(log_callback, f"[STEP 2.{index}] Processing {path_name} file...")
                self.sync_file(depot_path)
                self._log(log_callback, f"[OK] Synced latest version of {path_name}")
                self._progress(progress_callback, min(95, 25 + index * progress_step))

                self.checkout_file(
                    depot_path,
                    changelist_id,
                    log_callback=log_callback,
                    confirm_reopen_callback=confirm_reopen_callback,
                )
                self._log(log_callback, f"[OK] Checked out {path_name} for editing")

                local_path = self.depot_to_local_path(depot_path)
                self._log(log_callback, f"[DEBUG] Applying properties to {path_name}:")
                for category, props in properties_to_apply.items():
                    if props:
                        self._log(
                            log_callback,
                            f"[DEBUG]   {category}: {self._count_properties(props)} properties",
                        )

                local_props = self.extract_properties(local_path)
                match, diffs = self.validate_structure_match(properties_to_apply, local_props)
                if not match:
                    self._log(log_callback, f"[WARNING] Structure mismatch detected in {path_name}: {diffs}")
                    self._log(log_callback, "[INFO] Enforcing structure from source (higher branch)...")
                    enforce_success, enforce_error = self.enforce_structure(local_path, properties_to_apply)
                    if not enforce_success:
                        message = f"Failed to enforce structure in {path_name}: {enforce_error}"
                        self._log(log_callback, f"[ERROR] {message}")
                        return OperationResult(
                            success=False,
                            message=message,
                            changelist_id=changelist_id,
                            changed_files=processed_files,
                            details={"resolved_depot_paths": resolved_depot_paths},
                        )
                    self._log(log_callback, f"[OK] Source structure successfully enforced onto {path_name}.")

                success, error_message = self.update_properties(local_path, properties_to_apply)
                if not success:
                    message = f"Failed to apply changes to {path_name}: {error_message}"
                    self._log(log_callback, f"[ERROR] {message}")
                    return OperationResult(
                        success=False,
                        message=message,
                        changelist_id=changelist_id,
                        changed_files=processed_files,
                        details={"resolved_depot_paths": resolved_depot_paths},
                    )

                self._log(log_callback, f"[OK] Applied tuning changes to {path_name}.")
                processed_files.append(path_name)

            self._progress(progress_callback, 100)
            self._log(
                log_callback,
                f"[SUCCESS] Tuning changes applied successfully to: {', '.join(processed_files)}",
            )
            self._log(
                log_callback,
                f"[INFO] Changelist {changelist_id} contains all modifications for all paths",
            )

            if len(original_depot_paths) == 1:
                original_path = next(iter(original_depot_paths))
                self._log(
                    log_callback,
                    f"[SUMMARY] Auto-resolved from {original_path} to {len(processed_files)} files",
                )

            self._log(
                log_callback,
                f"[INFO] All properties have been synchronized across {len(processed_files)} files",
            )
            return OperationResult(
                success=True,
                message="Tuning changes applied successfully.",
                changelist_id=changelist_id,
                changed_files=processed_files,
                details={"resolved_depot_paths": resolved_depot_paths},
            )
        except Exception as exc:
            message = f"Apply tuning changes failed: {exc}"
            self._log(log_callback, f"[ERROR] {message}")
            return OperationResult(success=False, message=message)

    def auto_resolve_missing_depot_paths(
        self,
        original_depot_paths: dict[str, str],
        *,
        log_callback: LogCallback | None = None,
    ) -> dict[str, str]:
        self._log(log_callback, "[AUTO-RESOLVE] Starting auto-resolve for missing depot paths...")
        resolved_paths = dict(original_depot_paths)

        try:
            provided_path_name = next(iter(original_depot_paths))
            provided_depot_path = original_depot_paths[provided_path_name]
            self._log(
                log_callback,
                f"[AUTO-RESOLVE] Starting from {provided_path_name}: {provided_depot_path}",
            )

            if provided_path_name == "REL":
                self._log(log_callback, "[AUTO-RESOLVE] REL -> FLUMEN -> BENI resolution")
                self.map_single_depot(provided_depot_path)
                self.sync_file(provided_depot_path)

                flumen_path = self.get_integration_source_depot_path(provided_depot_path, log_callback)
                if not flumen_path:
                    raise RuntimeError(f"Cannot find integration source for REL: {provided_depot_path}")
                if not self.validate_depot_path(flumen_path):
                    raise RuntimeError(f"Integration source does not exist: {flumen_path}")

                resolved_paths["FLUMEN"] = flumen_path
                self._log(log_callback, f"[AUTO-RESOLVE] Found FLUMEN: {flumen_path}")

                self.map_single_depot(flumen_path)
                self.sync_file(flumen_path)

                beni_path = self.get_integration_source_depot_path(flumen_path, log_callback)
                if not beni_path:
                    raise RuntimeError(f"Cannot find integration source for FLUMEN: {flumen_path}")
                if not self.validate_depot_path(beni_path):
                    raise RuntimeError(f"Integration source does not exist: {beni_path}")

                resolved_paths["BENI"] = beni_path
                self._log(log_callback, f"[AUTO-RESOLVE] Found BENI: {beni_path}")
            elif provided_path_name == "FLUMEN":
                self._log(log_callback, "[AUTO-RESOLVE] FLUMEN -> BENI resolution")
                self.map_single_depot(provided_depot_path)
                self.sync_file(provided_depot_path)

                beni_path = self.get_integration_source_depot_path(provided_depot_path, log_callback)
                if not beni_path:
                    raise RuntimeError(f"Cannot find integration source for FLUMEN: {provided_depot_path}")
                if not self.validate_depot_path(beni_path):
                    raise RuntimeError(f"Integration source does not exist: {beni_path}")

                resolved_paths["BENI"] = beni_path
                self._log(log_callback, f"[AUTO-RESOLVE] Found BENI: {beni_path}")
            elif provided_path_name == "BENI":
                self._log(log_callback, "[AUTO-RESOLVE] BENI provided - no resolution needed")

            self._log(log_callback, "[AUTO-RESOLVE] Final resolved paths:")
            for path_name, depot_path in resolved_paths.items():
                self._log(log_callback, f"[RESOLVED] {path_name}: {depot_path}")

            return resolved_paths
        except Exception as exc:
            self._log(log_callback, f"[AUTO-RESOLVE ERROR] {exc}")
            self._log(log_callback, "[FALLBACK] Using original paths without auto-resolve")
            return dict(original_depot_paths)

    def _map_depot_paths(self, depot_paths: list[str]) -> None:
        if len(depot_paths) == 1:
            self.map_single_depot(depot_paths[0])
        elif len(depot_paths) == 2:
            self.map_two_depots(depot_paths[0], depot_paths[1])
        elif len(depot_paths) == 3:
            self._map_three_depots_silent(*depot_paths)

    def _map_three_depots_silent(self, depot1: str, depot2: str, depot3: str) -> None:
        client_name = get_client_name()
        if not client_name:
            raise RuntimeError("Client name not initialized. Please check P4 configuration.")

        client_spec = self.p4_client.client_spec_text()
        lines = client_spec.splitlines()
        new_lines: list[str] = []
        for line in lines:
            if depot1 in line or depot2 in line or depot3 in line:
                continue
            new_lines.append(line)

        new_lines.append(f"\t{depot1}\t//{client_name}/{depot1[2:]}")
        new_lines.append(f"\t{depot2}\t//{client_name}/{depot2[2:]}")
        new_lines.append(f"\t{depot3}\t//{client_name}/{depot3[2:]}")
        self.p4_client.update_client_spec("\n".join(new_lines))

    def _analyze_property_changes(
        self,
        original_dict: dict[str, Any] | None,
        current_dict: dict[str, Any] | None,
    ) -> dict[str, list[str]]:
        changes = {"add": [], "modify": [], "delete": []}
        original_entries = self._collect_property_entries(original_dict or {})
        current_entries = self._collect_property_entries(current_dict or {})

        original_keys = set(original_entries)
        current_keys = set(current_entries)

        changes["add"] = sorted({self._base_property_name(name) for name in current_keys - original_keys})
        changes["delete"] = sorted({self._base_property_name(name) for name in original_keys - current_keys})

        modified: set[str] = set()
        for key in original_keys & current_keys:
            if original_entries[key] != current_entries[key]:
                modified.add(self._base_property_name(key))
        changes["modify"] = sorted(modified)
        return changes

    def _build_category_description_part(self, category: str, changes: dict[str, list[str]]) -> str:
        add_list = changes.get("add", [])
        modify_list = changes.get("modify", [])
        delete_list = changes.get("delete", [])

        if not any(changes.values()):
            return ""

        add_count = len(add_list)
        modify_count = len(modify_list)
        delete_count = len(delete_list)

        if add_count > 0 and modify_count == 0 and delete_count == 0:
            return f"Add value {add_list[0]}" if add_count == 1 else f"Add {category} values"
        if delete_count > 0 and add_count == 0 and modify_count == 0:
            return f"Delete value {delete_list[0]}" if delete_count == 1 else f"Delete {category} values"
        if modify_count > 0 and add_count == 0 and delete_count == 0:
            return f"Tuning value {modify_list[0]}" if modify_count == 1 else f"Tuning {category}"
        if add_count > 0 and modify_count > 0 and delete_count == 0:
            return f"Add & Tuning {category}"
        if modify_count > 0 and delete_count > 0 and add_count == 0:
            return f"Tuning & Delete {category}"
        if add_count > 0 and delete_count > 0 and modify_count == 0:
            return f"Add & Delete {category}"
        if add_count > 0 and modify_count > 0 and delete_count > 0:
            return f"Add/Tune/Delete {category}"
        return f"Update {category}"

    def _collect_property_entries(self, category_data: dict[str, Any]) -> dict[str, str]:
        if not isinstance(category_data, dict):
            return {}

        if "_flat" not in category_data and "_conditional" not in category_data:
            return {
                str(key): str(value)
                for key, value in category_data.items()
                if not str(key).startswith("_")
            }

        entries = {str(key): str(value) for key, value in category_data.get("_flat", {}).items()}
        for block in category_data.get("_conditional", []):
            condition = block.get("condition", "<condition>")
            for key, value in block.get("if_props", {}).items():
                entries[f"{key}@if:{condition}"] = str(value)
            for key, value in (block.get("else_props") or {}).items():
                entries[f"{key}@else:{condition}"] = str(value)

        return entries

    @staticmethod
    def _base_property_name(entry_name: str) -> str:
        return entry_name.split("@", 1)[0]

    def _count_properties(self, category_data: Any) -> int:
        if not isinstance(category_data, dict):
            return 0
        if "_flat" not in category_data and "_conditional" not in category_data:
            return len([key for key in category_data if not str(key).startswith("_")])

        total = len(category_data.get("_flat", {}))
        for block in category_data.get("_conditional", []):
            total += len(block.get("if_props", {}))
            total += len(block.get("else_props") or {})
        return total

    @staticmethod
    def _compare_property_categories(
        original_dict: dict[str, str],
        current_dict: dict[str, str],
        category: str,
    ) -> list[str]:
        changes: list[str] = []
        all_keys = set(original_dict.keys()) | set(current_dict.keys())

        for key in sorted(all_keys):
            original_value = original_dict.get(key)
            current_value = current_dict.get(key)

            if original_value is None and current_value is not None:
                changes.append(f"[ADDED] {category}.{key} = {current_value}")
            elif original_value is not None and current_value is None:
                changes.append(f"[DELETED] {category}.{key} (was: {original_value})")
            elif original_value != current_value:
                changes.append(f"[MODIFIED] {category}.{key}: {original_value} -> {current_value}")

        return changes

    @staticmethod
    def _without_metadata(properties: dict[str, Any]) -> dict[str, Any]:
        cleaned = copy.deepcopy(properties)
        cleaned.pop("_metadata", None)
        return cleaned

    @staticmethod
    def _copy_property_tree(properties: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(properties)

    @staticmethod
    def _log(log_callback: LogCallback | None, message: str) -> None:
        if log_callback:
            log_callback(message)

    @staticmethod
    def _progress(progress_callback: ProgressCallback | None, value: int) -> None:
        if progress_callback:
            progress_callback(value)

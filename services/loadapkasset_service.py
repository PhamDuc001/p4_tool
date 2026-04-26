"""
Service layer for LoadApkAsset workflows.
"""

from __future__ import annotations

from collections.abc import Callable

from processes import loadapkasset_process
from services.models import OperationResult
from services.preview import preview_text_change


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]
ErrorCallback = Callable[..., None]
ContinueCallback = Callable[[str, str], bool]


class LoadApkAssetService:
    available_assets = loadapkasset_process.AVAILABLE_ASSETS

    def __init__(
        self,
        *,
        depot_to_local_path_fn: Callable[[str], str] = loadapkasset_process.depot_to_local_path,
        add_assets_to_chipset_content_fn: Callable[..., tuple[str, bool, list[str]]] = loadapkasset_process.add_assets_to_chipset_content,
    ):
        self.depot_to_local_path = depot_to_local_path_fn
        self.add_assets_to_chipset_content = add_assets_to_chipset_content_fn

    def find_samsung_vendor_path(self, workspace_name: str, log_callback: LogCallback | None = None):
        return loadapkasset_process.find_samsung_vendor_path(workspace_name, log_callback)

    def construct_readahead_manager_path(self, samsung_path: str) -> str:
        return loadapkasset_process.construct_readahead_manager_path(samsung_path)

    def parse_readahead_manager_file(self, file_path: str, log_callback: LogCallback | None = None):
        return loadapkasset_process.parse_readahead_manager_file(file_path, log_callback)

    def preview_add_assets(
        self,
        file_path: str,
        chipset_name: str,
        selected_assets: list[str],
        *,
        log_callback: LogCallback | None = None,
    ) -> OperationResult:
        try:
            local_path = self.depot_to_local_path(file_path)
            if log_callback:
                log_callback(f"[PREVIEW] Reading file: {local_path}")

            with open(local_path, "r", encoding="utf-8") as file:
                before = file.read()

            after, changed, assets_to_add = self.add_assets_to_chipset_content(
                before,
                chipset_name,
                selected_assets,
                log_callback,
            )
            preview = preview_text_change(local_path, before, after)

            if changed:
                message = f"Preview generated: {len(assets_to_add)} asset(s) would be added to {chipset_name}."
                changed_files = [file_path]
            else:
                message = f"Preview generated: no LoadApkAsset changes needed for {chipset_name}."
                changed_files = []

            return OperationResult(
                True,
                message,
                changed_files=changed_files,
                details={
                    "preview": preview,
                    "assets_to_add": assets_to_add,
                    "depot_path": file_path,
                    "local_path": local_path,
                },
            )
        except Exception as exc:
            return OperationResult(False, f"LoadApkAsset preview failed: {exc}")

    def run(
        self,
        workspaces: dict[str, str],
        chipset_name: str,
        selected_assets: list[str],
        changelist_id: str | None,
        *,
        log_callback: LogCallback,
        progress_callback: ProgressCallback | None = None,
        error_callback: ErrorCallback | None = None,
        continue_callback: ContinueCallback | None = None,
    ) -> OperationResult:
        try:
            loadapkasset_process.run_loadapkasset_process(
                workspaces,
                chipset_name,
                selected_assets,
                changelist_id,
                log_callback,
                progress_callback,
                error_callback,
                continue_callback=continue_callback,
            )
            return OperationResult(True, "LoadApkAsset process completed.")
        except Exception as exc:
            return OperationResult(False, f"LoadApkAsset process failed: {exc}")

"""
Service layer for LoadApkAsset workflows.
"""

from __future__ import annotations

from collections.abc import Callable

from processes import loadapkasset_process
from services.models import OperationResult


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]
ErrorCallback = Callable[..., None]
ContinueCallback = Callable[[str, str], bool]


class LoadApkAssetService:
    available_assets = loadapkasset_process.AVAILABLE_ASSETS

    def find_samsung_vendor_path(self, workspace_name: str, log_callback: LogCallback | None = None):
        return loadapkasset_process.find_samsung_vendor_path(workspace_name, log_callback)

    def construct_readahead_manager_path(self, samsung_path: str) -> str:
        return loadapkasset_process.construct_readahead_manager_path(samsung_path)

    def parse_readahead_manager_file(self, file_path: str, log_callback: LogCallback | None = None):
        return loadapkasset_process.parse_readahead_manager_file(file_path, log_callback)

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

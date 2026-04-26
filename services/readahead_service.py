"""
Service layer for readahead workflows.
"""

from __future__ import annotations

from collections.abc import Callable

from processes import readahead_process
from services.models import OperationResult


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]
ErrorCallback = Callable[..., None]
ContinueCallback = Callable[[str, str], bool]
PromptCallback = Callable[[str, str, str], str | None]


class ReadaheadService:
    def run(
        self,
        workspaces: dict[str, str],
        resource1_libs: list[str],
        resource2_libs: list[str],
        changelist_id: str | None,
        *,
        log_callback: LogCallback,
        progress_callback: ProgressCallback | None = None,
        error_callback: ErrorCallback | None = None,
        prompt_filename_callback: PromptCallback | None = None,
        continue_callback: ContinueCallback | None = None,
    ) -> OperationResult:
        try:
            readahead_process.run_readahead_process(
                workspaces,
                resource1_libs,
                resource2_libs,
                changelist_id,
                log_callback,
                progress_callback,
                error_callback,
                prompt_filename_callback=prompt_filename_callback,
                continue_callback=continue_callback,
            )
            return OperationResult(True, "Readahead process completed.")
        except Exception as exc:
            return OperationResult(False, f"Readahead process failed: {exc}")

    def prompt_for_rscmgr_filename(
        self,
        *,
        log_callback: LogCallback | None = None,
        prompt_filename_callback: PromptCallback | None = None,
    ) -> str | None:
        return readahead_process.prompt_for_rscmgr_filename(
            log_callback=log_callback,
            prompt_filename_callback=prompt_filename_callback,
        )

    def find_rscmgr_file_path(
        self,
        workspace: str,
        rscmgr_filename: str,
        *,
        log_callback: LogCallback | None = None,
    ) -> str | None:
        return readahead_process.find_rscmgr_file_path(
            workspace,
            rscmgr_filename,
            log_callback,
        )

    def find_rscmgr_filename_from_device_common(
        self,
        device_common_path: str,
        *,
        log_callback: LogCallback | None = None,
    ) -> str | None:
        return readahead_process.find_rscmgr_filename_from_device_common(
            device_common_path,
            log_callback,
        )

    def auto_resolve_missing_branches(
        self,
        workspaces: dict,
        rscmgr_filename: str,
        *,
        log_callback: LogCallback | None = None,
    ) -> dict:
        return readahead_process.auto_resolve_missing_branches_readahead(
            workspaces,
            rscmgr_filename,
            log_callback,
        )

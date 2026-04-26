"""
Service layer for bring-up workflows.
"""

from __future__ import annotations

from collections.abc import Callable

from processes import bringup_process, system_process
from services.models import OperationResult


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]
ErrorCallback = Callable[..., None]
ContinueCallback = Callable[[str, str], bool]


class BringupService:
    def run_vendor(
        self,
        beni_input: str,
        vince_input: str,
        flumen_input: str,
        rel_input: str,
        *,
        log_callback: LogCallback,
        progress_callback: ProgressCallback | None = None,
        error_callback: ErrorCallback | None = None,
    ) -> OperationResult:
        try:
            bringup_process.run_bringup_process(
                beni_input,
                vince_input,
                flumen_input,
                rel_input,
                log_callback,
                progress_callback,
                error_callback,
            )
            return OperationResult(True, "Vendor bring-up completed.")
        except Exception as exc:
            return OperationResult(False, f"Vendor bring-up failed: {exc}")

    def run_system(
        self,
        beni_input: str,
        vince_input: str,
        flumen_input: str,
        rel_input: str,
        *,
        log_callback: LogCallback,
        progress_callback: ProgressCallback | None = None,
        error_callback: ErrorCallback | None = None,
        continue_callback: ContinueCallback | None = None,
    ) -> OperationResult:
        try:
            system_process.run_system_process(
                beni_input,
                vince_input,
                flumen_input,
                rel_input,
                log_callback,
                progress_callback,
                error_callback,
                continue_callback=continue_callback,
            )
            return OperationResult(True, "System bring-up completed.")
        except Exception as exc:
            return OperationResult(False, f"System bring-up failed: {exc}")

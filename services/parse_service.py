"""
Service layer for workspace parsing and ADB library-size workflows.
"""

from __future__ import annotations

from processes import parse_process


class ParseService:
    def __init__(self):
        self.process = parse_process

    def parse_multiple_workspaces(self, workspace_dict, log_callback=None, progress_callback=None):
        return self.process.parse_multiple_workspaces(
            workspace_dict,
            log_callback=log_callback,
            progress_callback=progress_callback,
        )

    def refresh_adb_devices(self, log_callback=None):
        return self.process.refresh_adb_devices(log_callback=log_callback)

    def connect_to_device(self, device_id, log_callback=None):
        return self.process.connect_to_device(device_id, log_callback=log_callback)

    def calculate_library_sizes(
        self,
        device_id,
        libraries,
        log_callback=None,
        progress_callback=None,
    ):
        return self.process.calculate_library_sizes(
            device_id,
            libraries,
            log_callback=log_callback,
            progress_callback=progress_callback,
        )

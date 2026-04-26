from services.app_logging import create_operation_logger
from services.parse_service import ParseService


def test_parse_service_delegates_to_process_object():
    calls = {}

    class FakeProcess:
        def parse_multiple_workspaces(self, workspace_dict, log_callback=None, progress_callback=None):
            calls["parse"] = workspace_dict
            return {"BENI": ["//depot/device_common.mk"]}

        def refresh_adb_devices(self, log_callback=None):
            calls["refresh"] = True
            return ["device1"]

        def connect_to_device(self, device_id, log_callback=None):
            calls["connect"] = device_id
            return True

        def calculate_library_sizes(self, device_id, libraries, log_callback=None, progress_callback=None):
            calls["calculate"] = (device_id, libraries)
            return {libraries[0]: 1024}

    service = ParseService()
    service.process = FakeProcess()

    assert service.parse_multiple_workspaces({"BENI": "ws"}) == {"BENI": ["//depot/device_common.mk"]}
    assert service.refresh_adb_devices() == ["device1"]
    assert service.connect_to_device("device1") is True
    assert service.calculate_library_sizes("device1", ["/system/lib/liba.so"]) == {
        "/system/lib/liba.so": 1024
    }
    assert calls["parse"] == {"BENI": "ws"}
    assert calls["refresh"] is True
    assert calls["connect"] == "device1"
    assert calls["calculate"] == ("device1", ["/system/lib/liba.so"])


def test_create_operation_logger_writes_log_file(tmp_path):
    operation_logger = create_operation_logger("testop", log_dir=tmp_path)
    operation_logger.info("hello")

    for handler in operation_logger.logger.handlers:
        handler.flush()

    assert operation_logger.log_path.exists()
    assert "hello" in operation_logger.log_path.read_text(encoding="utf-8")

import importlib


def test_core_modules_import():
    for module_name in [
        "config.settings",
        "core.p4_client",
        "core.p4_operations",
        "core.file_operations",
        "services.app_logging",
        "services.bringup_service",
        "services.loadapkasset_service",
        "services.parse_service",
        "services.preview",
        "services.readahead_service",
        "services.tuning_service",
        "main",
    ]:
        importlib.import_module(module_name)

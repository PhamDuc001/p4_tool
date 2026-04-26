import importlib


def test_core_modules_import():
    for module_name in [
        "config.settings",
        "core.p4_client",
        "core.p4_operations",
        "core.file_operations",
        "main",
    ]:
        importlib.import_module(module_name)

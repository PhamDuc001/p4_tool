import subprocess

from core import p4_operations
from services.bringup_service import BringupService
from services.loadapkasset_service import LoadApkAssetService
from services.preview import build_unified_diff, preview_text_change
from services.readahead_service import ReadaheadService


def completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def test_checkout_file_silent_without_callback_keeps_existing_changelist(monkeypatch):
    calls = {"reopen": 0, "edit": 0}

    class FakeClient:
        def opened(self, depot_path):
            return completed(["p4", "opened", depot_path], stdout=f"{depot_path}#1 - edit change 111 (text)")

        def edit(self, depot_path, changelist_id):
            calls["edit"] += 1

        def reopen(self, depot_path, changelist_id):
            calls["reopen"] += 1

        def sync(self, depot_path):
            return None

    monkeypatch.setattr(p4_operations, "get_default_p4_client", lambda: FakeClient())

    p4_operations.checkout_file_silent("//depot/file.txt", "222")

    assert calls["edit"] == 0
    assert calls["reopen"] == 0


def test_bringup_service_passes_continue_callback(monkeypatch):
    captured = {}

    def fake_run_system_process(*args, **kwargs):
        captured["continue_callback"] = kwargs["continue_callback"]

    monkeypatch.setattr("services.bringup_service.system_process.run_system_process", fake_run_system_process)

    service = BringupService()
    callback = lambda title, message: True
    result = service.run_system(
        "BENI",
        "VINCE",
        "",
        "",
        log_callback=lambda message: None,
        continue_callback=callback,
    )

    assert result.success is True
    assert captured["continue_callback"] is callback


def test_readahead_service_passes_prompt_and_continue_callbacks(monkeypatch):
    captured = {}

    def fake_run_readahead_process(*args, **kwargs):
        captured["prompt"] = kwargs["prompt_filename_callback"]
        captured["continue"] = kwargs["continue_callback"]

    monkeypatch.setattr("services.readahead_service.readahead_process.run_readahead_process", fake_run_readahead_process)

    service = ReadaheadService()
    prompt_callback = lambda title, message, initial: "rscmgr.rc"
    continue_callback = lambda title, message: True
    result = service.run(
        {"REL": "workspace"},
        ["libA.so"],
        [],
        None,
        log_callback=lambda message: None,
        prompt_filename_callback=prompt_callback,
        continue_callback=continue_callback,
    )

    assert result.success is True
    assert captured["prompt"] is prompt_callback
    assert captured["continue"] is continue_callback


def test_loadapkasset_service_passes_continue_callback(monkeypatch):
    captured = {}

    def fake_run_loadapkasset_process(*args, **kwargs):
        captured["continue"] = kwargs["continue_callback"]

    monkeypatch.setattr("services.loadapkasset_service.loadapkasset_process.run_loadapkasset_process", fake_run_loadapkasset_process)

    service = LoadApkAssetService()
    continue_callback = lambda title, message: False
    result = service.run(
        {"REL": "workspace"},
        "EXYNOS850",
        ["ASSET_CAMERA"],
        None,
        log_callback=lambda message: None,
        continue_callback=continue_callback,
    )

    assert result.success is True
    assert captured["continue"] is continue_callback


def test_readahead_prompt_uses_callback():
    service = ReadaheadService()
    result = service.prompt_for_rscmgr_filename(
        log_callback=lambda message: None,
        prompt_filename_callback=lambda title, message, initial: "rscmgr_custom.rc",
    )

    assert result == "rscmgr_custom.rc"


def test_preview_helpers_generate_diff():
    diff = build_unified_diff("a=1\n", "a=2\n", fromfile="old", tofile="new")
    preview = preview_text_change("demo.txt", "a=1\n", "a=2\n")

    assert "--- old" in diff
    assert "+++ new" in diff
    assert preview.changed is True
    assert "demo.txt (before)" in preview.diff

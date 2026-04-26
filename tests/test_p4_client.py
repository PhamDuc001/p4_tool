import subprocess

import pytest

from config.settings import Settings
from core.p4_client import P4Client, P4CommandError


def completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_builds_argument_list_without_shell(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return completed(cmd, stdout="//depot/path/file#1 - edit change 1 (text)\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = P4Client(Settings(p4port="test:1666", p4user="user", p4client="client"))
    output = client.run(["files", "//depot/path/file"])

    assert output.startswith("//depot/path/file#1")
    assert calls[0][0] == ["p4", "files", "//depot/path/file"]
    assert "shell" not in calls[0][1]
    assert calls[0][1]["env"]["P4PORT"] == "test:1666"


def test_run_raises_detailed_error(monkeypatch):
    def fake_run(cmd, **kwargs):
        return completed(cmd, returncode=1, stdout="out", stderr="bad")

    monkeypatch.setattr(subprocess, "run", fake_run)

    client = P4Client(Settings())
    with pytest.raises(P4CommandError) as exc:
        client.run(["sync", "//missing/file"])

    assert exc.value.command == ["p4", "sync", "//missing/file"]
    assert exc.value.returncode == 1
    assert exc.value.stdout == "out"
    assert exc.value.stderr == "bad"


def test_fetch_client_spec_parses_view(monkeypatch):
    spec = """Client: demo_client
Root: C:\\ws

View:
\t//depot/project/... //demo_client/project/...
\t//depot/vendor/device/a_common/... //demo_client/vendor/device/a_common/...
"""

    def fake_run(cmd, **kwargs):
        return completed(cmd, stdout=spec)

    monkeypatch.setattr(subprocess, "run", fake_run)

    parsed = P4Client(Settings()).fetch_client_spec("demo_client")

    assert parsed["Client"] == "demo_client"
    assert parsed["Root"] == "C:\\ws"
    assert parsed["View"][1].startswith("//depot/vendor")

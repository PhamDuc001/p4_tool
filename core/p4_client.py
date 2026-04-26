"""
Centralized Perforce subprocess access.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Any

from config.settings import Settings, load_settings


@dataclass
class P4CommandError(RuntimeError):
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def __str__(self) -> str:
        joined = " ".join(self.command)
        return (
            f"P4 command failed: {joined}\n"
            f"returncode={self.returncode}\n"
            f"stdout={self.stdout}\n"
            f"stderr={self.stderr}"
        )


class P4Client:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()

    def _build_env(self) -> dict[str, str]:
        return self.settings.p4_env()

    def run(
        self,
        args: list[str],
        input_text: str | None = None,
        check: bool = True,
    ) -> str:
        cmd = ["p4", *args]
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            env=self._build_env(),
            encoding="utf-8",
            errors="replace",
        )
        if check and result.returncode != 0:
            raise P4CommandError(
                command=cmd,
                returncode=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
            )
        return result.stdout.strip()

    def run_with_result(
        self,
        args: list[str],
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["p4", *args],
            input=input_text,
            capture_output=True,
            text=True,
            env=self._build_env(),
            encoding="utf-8",
            errors="replace",
        )

    def files(self, depot_path: str) -> bool:
        result = self.run_with_result(["files", depot_path])
        if result.returncode != 0:
            stderr = (result.stderr or "").lower()
            stdout = (result.stdout or "").lower()
            if "no such file" in stderr or "no such file" in stdout:
                return False
            return False
        return True

    def sync(self, depot_path: str) -> None:
        self.run(["sync", depot_path])

    def edit(self, depot_path: str, changelist_id: str) -> None:
        self.run(["edit", "-c", str(changelist_id), depot_path])

    def reopen(self, depot_path: str, changelist_id: str) -> None:
        self.run(["reopen", "-c", str(changelist_id), depot_path])

    def add(self, depot_path: str, changelist_id: str) -> None:
        self.run(["add", "-c", str(changelist_id), depot_path])

    def opened(self, depot_path: str) -> subprocess.CompletedProcess[str]:
        return self.run_with_result(["opened", depot_path])

    def filelog(self, depot_path: str) -> str:
        return self.run(["filelog", "-i", depot_path])

    def create_changelist(self, description: str) -> str:
        changelist_spec = self.run(["change", "-o"])
        lines = changelist_spec.splitlines()
        new_lines: list[str] = []
        for line in lines:
            if line.strip() == "<enter description here>":
                new_lines.append(f"\t{description}")
            elif line.strip() == "[Title]":
                new_lines.append(f"\t[Title] {description}")
            else:
                new_lines.append(line)
        changelist_result = self.run(["change", "-i"], input_text="\n".join(new_lines))
        match = re.search(r"Change (\d+)", changelist_result)
        if not match:
            raise RuntimeError(f"Unable to parse changelist id from output: {changelist_result}")
        return match.group(1)

    def fetch_client_spec(self, workspace: str | None = None) -> dict[str, Any]:
        args = ["client", "-o"]
        if workspace:
            args.append(workspace)
        spec_text = self.run(args)
        return self._parse_spec(spec_text)

    def client_spec_text(self) -> str:
        return self.run(["client", "-o"])

    def update_client_spec(self, spec_text: str) -> None:
        self.run(["client", "-i"], input_text=spec_text)

    def login_status(self) -> subprocess.CompletedProcess[str]:
        return self.run_with_result(["login", "-s"])

    def login(self, password: str) -> subprocess.CompletedProcess[str]:
        return self.run_with_result(["login"], input_text=password)

    def set_variable(self, key: str, value: str) -> None:
        subprocess.run(
            ["p4", "set", f"{key}={value}"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def set_output(self) -> str:
        result = subprocess.run(
            ["p4", "set"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip()

    def list_clients_for_user(self, username: str, port: str | None = None) -> str:
        args = []
        if port:
            args.extend(["-p", port])
        args.extend(["-u", username, "clients", "-u", username])
        return self.run(args)

    @staticmethod
    def _parse_spec(spec_text: str) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        current_key: str | None = None
        for raw_line in spec_text.splitlines():
            if not raw_line.strip():
                continue
            if not raw_line.startswith("\t") and ":" in raw_line:
                key, value = raw_line.split(":", 1)
                key = key.strip()
                value = value.strip()
                current_key = key
                if value:
                    parsed[key] = value
                else:
                    parsed[key] = []
            elif current_key and isinstance(parsed.get(current_key), list):
                parsed[current_key].append(raw_line.strip())
        return parsed


_DEFAULT_CLIENT: P4Client | None = None


def get_default_p4_client() -> P4Client:
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = P4Client()
    return _DEFAULT_CLIENT

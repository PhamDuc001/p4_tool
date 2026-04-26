"""
Application settings with environment-first P4 configuration.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


DEFAULT_P4PORT = "107.113.53.156:1716"
APP_NAME = "P4 Tool"


def _config_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / f".{APP_NAME.lower().replace(' ', '_')}"


def _config_path() -> Path:
    return _config_dir() / "settings.json"


@dataclass
class Settings:
    p4port: str = DEFAULT_P4PORT
    p4user: str = ""
    p4client: str = ""
    default_changelist_description: str = "Auto changelist"
    recent_workspaces: list[str] = field(default_factory=list)
    recent_depot_paths: list[str] = field(default_factory=list)

    def p4_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self.p4port:
            env["P4PORT"] = self.p4port
        if self.p4user:
            env["P4USER"] = self.p4user
        if self.p4client:
            env["P4CLIENT"] = self.p4client
        return env


def load_settings() -> Settings:
    settings = Settings()
    path = _config_path()

    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        for field_name in Settings.__dataclass_fields__:
            if field_name in payload:
                setattr(settings, field_name, payload[field_name])

    settings.p4port = os.getenv("P4PORT", settings.p4port)
    settings.p4user = os.getenv("P4USER", settings.p4user)
    settings.p4client = os.getenv("P4CLIENT", settings.p4client)
    return settings


def save_settings(settings: Settings) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")

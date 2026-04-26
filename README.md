# P4 Tool

Tkinter desktop tool for Perforce workflows used by bring-up, tuning property updates,
library parsing, readahead configuration, and LoadApkAsset updates.

## Requirements

- Windows with Python 3.10 or newer
- Perforce CLI (`p4`) available on `PATH`
- Access to the required Perforce server, workspaces, and depot paths

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

P4 settings are read from environment variables first, then from the local user
settings file, then from defaults.

Useful environment variables:

```powershell
$env:P4PORT="107.113.53.156:1716"
$env:P4USER="<your-user>"
$env:P4CLIENT="<your-workspace>"
```

## Run

```powershell
python main.py
```

The application expects P4 authentication to be valid. If login is required,
the GUI prompts for a password.

## Test

```powershell
python -m compileall -q .
pytest
```

The pytest suite uses temporary files and mocked P4 subprocess calls. It should
not require real P4 access.

## Build

```powershell
pyinstaller main.spec
```

Generated `build/` and `dist/` output should be treated as build artifacts.

## Current Workflows

- Bring up: compare VINCE source properties against target branches and apply
  LMKD/Chimera updates.
- Tuning value: load, add, edit, and delete LMKD/Chimera properties in
  `device_common.mk`.
- Parse: collect library data from an attached Android device through ADB.
- Readahead: update `device_common.mk`, `Android.mk`, and `rscmgr.rc` resources.
- LoadApkAsset: update chipset asset configuration in `ReadaheadManager.java`.

Inputs are usually either a depot path such as `//depot/.../device_common.mk`
or a workspace name beginning with `TEMPLATE`.

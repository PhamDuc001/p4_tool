# Build Guide

## Prerequisites

- Windows with Python 3.10 or newer
- Perforce CLI (`p4`) on `PATH`
- Runtime dependencies from `requirements.txt`
- Build dependency: `pyinstaller`

## Clean Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

## Verify Before Build

```powershell
python -m compileall -q .
python -m pytest
```

## Build Executable

```powershell
pyinstaller main.spec
```

The executable is written to `dist\P4Tool.exe`.

## Release Smoke Test

1. Confirm `p4` is available on `PATH`.
2. Launch `dist\P4Tool.exe`.
3. Confirm the login/config flow opens.
4. Open each tab once.
5. Run pytest from source after the build to confirm no generated artifacts changed source behavior.

## Artifacts

- `build/` and `dist/` are generated artifacts and are ignored by git.
- Do not commit generated executables unless a release process explicitly requires it.

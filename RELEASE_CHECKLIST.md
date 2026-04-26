# Release Checklist

1. Update `config/version.py`.
2. Update `CHANGELOG.md`.
3. Run:

```powershell
python -m compileall -q .
python -m pytest
```

4. Build:

```powershell
pyinstaller main.spec
```

5. Smoke test `dist\P4Tool.exe`.
6. Confirm `git status --short` contains only intended source/doc changes.
7. Tag the release after merge:

```powershell
git tag v0.2.0
git push origin v0.2.0
```

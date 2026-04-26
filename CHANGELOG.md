# Changelog

## 0.2.0 - 2026-04-26

- Added service-layer boundaries for tuning, bring-up, readahead, LoadApkAsset, and parse workflows.
- Moved the active tuning workflow into `TuningService`.
- Added callback-based GUI confirmations so process/core modules no longer import Tkinter dialogs.
- Added dry-run preview primitives and tuning dry-run support.
- Added operation logging helpers.
- Added focused service tests and packaging documentation.

## 0.1.0 - 2026-04-26

- Added project setup and test documentation.
- Centralized P4 subprocess execution in `core.p4_client`.
- Extracted property parsing, comparison, and writing into `core.properties`.
- Added pytest coverage for property and P4 client behavior.

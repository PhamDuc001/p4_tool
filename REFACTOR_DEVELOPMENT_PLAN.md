# P4 Tool Refactor And Development Plan

Last updated: 2026-04-26

## Current Status

The first refactor pass was implemented and pushed to `main` in commit `dcb6db4`.
The current working tree starts Phase 4 by extracting the tuning workflow into a service layer.

Completed:

- Added project setup documentation in `README.md`.
- Added `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml`.
- Added pytest coverage under `tests/`.
- Added centralized P4 subprocess layer in `core/p4_client.py`.
- Added environment/local-file settings in `config/settings.py`.
- Reworked P4 config/bootstrap code to use the centralized client.
- Extracted property logic into focused modules:
  - `core/properties/parser.py`
  - `core/properties/comparer.py`
  - `core/properties/writer.py`
- Reduced `core/file_operations.py` to compatibility wrappers plus bring-up block helpers and GUI conditional-analysis helpers.
- Updated low-risk process imports to use canonical property modules.
- Created initial `services/` package with shared result and confirmation models.
- Extracted the tuning workflow into `services/tuning_service.py`.
- Updated the tuning GUI to call `TuningService` directly.
- Converted `processes/tuning_process.py` into a compatibility wrapper around the service layer.
- Added focused service-level tuning tests.

Verified:

```powershell
python -m compileall -q .
python -m pytest
```

Current result: `20 passed`.

## Current Architecture

```text
P4_Tool/
  main.py
  config/
    p4_config.py
    settings.py
  core/
    p4_client.py
    p4_operations.py
    file_operations.py          # compatibility and bring-up block helpers
    properties/
      __init__.py
      parser.py
      comparer.py
      writer.py
  services/
    __init__.py
    models.py
    tuning_service.py
  processes/
  gui/
  tests/
```

## Phase Status

### Phase 1: Stabilize And Document

Status: Complete

Completed:

- Added setup/run/build/test instructions in `README.md`.
- Added runtime and dev dependency files.
- Added pytest config.
- Added smoke tests and focused P4/property tests.
- Test suite runs without real P4 access.

Acceptance criteria:

- A new developer can install dependencies and run tests: met.
- `python -m compileall -q .` passes: met.
- `pytest` runs without real P4 access: met.

### Phase 2: P4 Layer Refactor

Status: Substantially complete

Completed:

- Created `core/p4_client.py`.
- Added `P4Client` with argument-list subprocess execution.
- Added `P4CommandError` with command, return code, stdout, and stderr.
- Routed `core/p4_operations.py`, `config/p4_config.py`, and `main.py` through the centralized client.
- Removed direct `shell=True` P4 calls from the main P4 operation layer.
- Moved configurable P4 values into `config/settings.py`.
- Added mocked P4 command construction tests.

Remaining:

- Some transitional wrappers still accept string commands such as `run_cmd("p4 client -o")`, but execution is routed through `P4Client`.
- Non-P4 subprocess use remains in parse/ADB workflows and is out of scope for the P4 layer.
- Some process modules still own workflow-specific P4 behavior and should eventually move into service classes.

Acceptance criteria:

- P4 commands are executed with argument lists: met for centralized P4 path.
- P4 command errors include command, return code, stdout, and stderr: met.
- No direct P4 subprocess calls outside approved transitional wrappers: mostly met; keep checking during service extraction.

### Phase 3: Property Engine Refactor

Status: Complete enough for current refactor milestone

Completed:

- Extracted property parser to `core/properties/parser.py`.
- Extracted property comparer to `core/properties/comparer.py`.
- Extracted property writer to `core/properties/writer.py`.
- Removed duplicate production comparer override from `core/file_operations.py`.
- Converted `core/file_operations.py` into a compatibility surface for old imports.
- Added tests for:
  - flat properties
  - conditional `ifneq`
  - `else`
  - DHA fallback
  - conditional structure mismatch
  - selected-context writes
  - flat writes
  - P4 client behavior

Remaining:

- Add dataclasses/models only if they reduce complexity in later service work.
- Add more edge-case tests for nested conditionals, missing block behavior, preserving comments, preserving backslashes, and delete/add behavior.
- Decide whether `analyze_conditional_structure` should move from `core/file_operations.py` into `core/properties/parser.py` or a GUI-facing view-model helper.

Acceptance criteria:

- Property logic lives in focused modules: met.
- Existing conditional-aware behavior remains covered by tests: met for high-risk paths.
- No duplicate parser/comparer definitions remain on the active path: met.

### Phase 4: Service Layer

Status: Started

Goal:

Move workflow logic out of GUI/process modules and make behavior testable without Tkinter.

Tasks:

- Create `services/` package: complete.
- Add shared result models, for example:

```python
@dataclass
class OperationResult:
    success: bool
    message: str
    changelist_id: str | None = None
    changed_files: list[str] = field(default_factory=list)

@dataclass
class ConfirmationRequest:
    title: str
    message: str
    options: list[str]
```

- Move tuning workflow into `TuningService`: complete for the active tuning GUI path.
- Move bring-up workflow into `BringupService`.
- Move readahead workflow into `ReadaheadService`.
- Move LoadApkAsset workflow into `LoadApkAssetService`.
- Move parse/library workflow into `ParseService`.
- Inject dependencies such as `P4Client`, parser, writer, comparer, and logger.
- Keep GUI tabs responsible for rendering dialogs and messages.

Completed:

- Added `services/models.py` with `OperationResult`, `ConfirmationRequest`, and `TuningLoadResult`.
- Added `services/tuning_service.py` with load, comparison, confirmation-summary, auto-resolve, and apply methods.
- Moved tuning change detection and confirmation message construction out of `gui/tuning_tab.py`.
- Updated `gui/tuning_tab.py` to handle input validation, dialogs, table rendering, and service result display for tuning operations.
- Added an optional reopen-confirmation callback to `checkout_file_silent` so migrated workflows can keep Tkinter prompts in the GUI layer.
- Added `tests/test_tuning_service.py`.

Known blockers/risk:

- `processes/readahead_process.py`, `processes/system_process.py`, and `processes/loadapkasset_process.py` still call Tkinter dialogs directly.
- `core/p4_operations.py` still has a legacy Tkinter fallback when `checkout_file_silent` is called without a confirmation callback.
- Some process functions combine validation, P4 access, file mutation, logging, and UI confirmation.

Acceptance criteria:

- GUI classes mostly collect inputs and render results.
- Services can be tested without Tkinter: met for `TuningService`.
- Process/service code no longer calls `messagebox` or `simpledialog` directly: met for the migrated tuning service path, not yet met for the remaining workflows.

### Phase 5: GUI Cleanup

Status: Not started

Tasks:

- Create reusable input components.
- Create reusable log/progress panel.
- Standardize validation messages.
- Standardize button enable/disable behavior during background work.
- Add preview/diff dialog.
- Add settings dialog.
- Add recent workspace/path history.

Acceptance criteria:

- Tabs are easier to scan and maintain.
- Common UI patterns are reused.
- Background operations consistently disable buttons and restore state.

### Phase 6: Preview And Dry Run

Status: Not started

Goal:

Reduce risk before editing Perforce-managed files.

Tasks:

- Add dry-run mode to service methods.
- Compute planned file changes without writing.
- Generate unified diffs.
- Show preview before apply.
- Let users confirm or cancel.
- Log all planned and applied actions.

Acceptance criteria:

- User can inspect changes before `p4 edit` and file write.
- Canceling preview leaves files unchanged.
- Applied operations produce a clear summary.

### Phase 7: Reliability And Observability

Status: Not started

Tasks:

- Add structured application logging.
- Save logs to a local file.
- Include operation ID/timestamp in logs.
- Include changelist IDs and changed files in result summaries.
- Add explicit domain exceptions beyond `P4CommandError`, such as:
  - `DepotPathError`
  - `PropertyParseError`
  - `PropertyWriteError`
- Add retry handling only where safe.

Acceptance criteria:

- Users can provide a log file after failure.
- Errors identify the failed command or file operation clearly.

### Phase 8: Packaging And Release

Status: Partially started

Completed:

- Added dependency files.
- Documented basic PyInstaller build command in `README.md`.

Remaining:

- Clean up `main.spec`.
- Add app version metadata.
- Add `BUILD.md`.
- Add changelog.
- Add release checklist.
- Confirm generated artifacts are ignored or intentionally versioned.

Acceptance criteria:

- Build process is repeatable from a clean checkout.
- Release artifact can be created and tested consistently.

## Recommended Next Implementation Order

1. Extract `BringupService`.
2. Extract `ReadaheadService`, then `LoadApkAssetService`.
3. Remove remaining process-level `messagebox` and `simpledialog` calls.
4. Add service-level tests with fake `P4Client` for bring-up, readahead, and LoadApkAsset.
5. Add dry-run/preview support to service methods.
6. Add settings GUI after service boundaries are stable.
7. Add structured logging.
8. Improve packaging and release docs.

## High-Risk Areas To Keep Testing

- Conditional property parsing.
- Conditional property writing.
- DHA vs LMKD fallback behavior.
- Preserving `PRODUCT_PROPERTY_OVERRIDES += \`.
- Preserving line continuation backslashes.
- Add/modify/delete behavior.
- Changelist creation and file checkout logic.
- Workspace-to-depot path resolution.
- Auto-resolve through integration history.
- Readahead file path discovery.
- LoadApkAsset insertion position and duplicate handling.

## Known Technical Debt

- `testing/` still contains old script-style checks. The active pytest suite is under `tests/`; old scripts should be reviewed and either converted or removed.
- `core/file_operations.py` is intentionally retained for compatibility, but new property code should import from `core.properties.*`.
- `processes/tuning_process.py` is intentionally retained as compatibility wrappers around `TuningService`.
- Several process modules still call `messagebox`/`simpledialog` directly.
- Service layer exists for tuning only.
- Dry-run/preview mode does not exist yet.

## Definition Of Done For Current Milestone

This milestone is considered OK because:

- The application compiles.
- The test suite passes.
- P4 command execution is centralized for the main P4 path.
- Property parsing/comparison/writing has canonical modules and tests.
- Compatibility imports remain available for existing GUI/process code.

Next milestone should focus on extracting bring-up/readahead/loadapkasset services and finishing Tkinter decoupling outside the tuning path.

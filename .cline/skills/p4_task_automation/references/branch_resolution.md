# Branch Resolution Logic

## Overview

This document describes how to resolve a workspace name (e.g., `TEMPLATE_ABC_REL`) into depot paths for `device_common.mk` and other target files, then cascade to find the corresponding files in other branches.

## Step 1: Resolve Workspace to device_common.mk

### 1.1 Use find_device_common.py Script

Instead of manually parsing the View section, use the provided script to resolve workspace names to device_common.mk paths:

```bash
# Script location: .cline/skills/p4_task_automation/scripts/find_device_common.py
python .cline/skills/p4_task_automation/scripts/find_device_common.py <workspace_name>
```

If the script returns a path, that is the device_common.mk depot path. If it returns nothing (empty), the workspace does not contain a valid device_common.mk path.

### 1.2 Manual Resolution (Fallback)

If the script is not available, manually resolve the workspace:

```bash
p4 client -o <workspace_name>
```

This returns the full client spec. The key section is **View**, which contains mappings from depot paths to client paths.

Look through each line in the `View:` section for a depot path matching the pattern:
```
/device/<model>_common/...
```

Example View line:
```
//depot/vendor/samsung/exynos850_beni/device/exynos850_common/... //client_name/vendor/samsung/...
```

From the matched View line:
1. Extract the depot path prefix up to and including the `device/<model>_common/` segment
2. Append `device_common.mk`

Example:
- View line depot: `//depot/vendor/samsung/exynos850_beni/device/exynos850_common/...`
- Extracted base: `//depot/vendor/samsung/exynos850_beni/device/exynos850_common/`
- Result: `//depot/vendor/samsung/exynos850_beni/device/exynos850_common/device_common.mk`

### 1.4 Validate the Path

```bash
p4 files //depot/vendor/samsung/.../device_common.mk
```

If the command returns a valid file entry, the path exists. If it returns "no such file", the path is invalid.

### 1.5 Map the Path to Client Spec

After resolving and validating the path, map it to the client spec using the `map_path.py` script:

```bash
# Script location: .cline/skills/p4_task_automation/scripts/map_path.py
python .cline/skills/p4_task_automation/scripts/map_path.py <depot_path>
```

This ensures the file is accessible locally for subsequent operations.

## Step 2: Find vendor/samsung Base Path

The Samsung vendor base path is needed for finding other files like `rscmgr.rc`, `Android.mk`, and `ReadaheadManager.java`.

### 2.1 Parse from View Section

Look through View mappings for a path containing `/vendor/samsung/`:

```
//depot/vendor/samsung/<model_branch>/...
```

Extract everything up to and including `/vendor/samsung/`:

Example:
- View: `//depot/vendor/samsung/exynos850_beni/system/...`
- Samsung path: `//depot/vendor/samsung/exynos850_beni/`

> **Note**: There may be multiple `vendor/samsung/` paths. Use the first match that validates.

## Step 3: Auto-Resolve Branch Cascade

When the user provides a workspace for only ONE branch, auto-resolve the remaining branches using P4 integration history.

### 3.1 Integration History Command

```bash
p4 filelog -i <depot_path>#1
```

This shows the integration history for version #1 of the file. Look for the `branch from` line:

```
... ... branch from //depot/vendor/samsung/exynos850_flumen/device/exynos850_common/device_common.mk#1
```

### 3.2 Parse Source Path

Extract the depot path from the `branch from` line:

```
Pattern: "... ... branch from <source_depot_path>#<version>"
```

- Remove the `... ... branch from ` prefix
- Remove the `#<version>` suffix
- Remove any `,<range>` suffix if present

Result is the parent branch's depot path for the same file.

### 3.3 Cascade Rules

```
IF user provides REL workspace:
  1. Resolve REL → device_common.mk depot path
  2. Run: p4 filelog -i <REL_device_common.mk>#1
  3. Parse "branch from" → get FLUMEN device_common.mk path
  4. Map & sync FLUMEN path
  5. Run: p4 filelog -i <FLUMEN_device_common.mk>#1
  6. Parse "branch from" → get BENI device_common.mk path

IF user provides FLUMEN workspace:
  1. Resolve FLUMEN → device_common.mk depot path
  2. Run: p4 filelog -i <FLUMEN_device_common.mk>#1
  3. Parse "branch from" → get BENI device_common.mk path

IF user provides BENI workspace:
  1. Resolve BENI → device_common.mk depot path
  2. No further resolution needed (BENI is the base branch)
```

### 3.4 Important: Map and Sync Before Filelog

Before running `p4 filelog -i` on a resolved path, you must:
1. **Map** the depot path into the client spec (see SKILL.md Step 5)
2. **Sync** the file (`p4 sync <path>`)

This ensures the file is accessible locally and P4 can trace its integration history.

### 3.5 Validation

After resolving each path, validate it exists:

```bash
p4 files <resolved_path>
```

If it returns "no such file", the integration chain is broken. Report the error and stop cascade.

## Step 4: Resolve Other Files from device_common.mk Path

Once you have a `device_common.mk` depot path for a branch, you can derive paths to related files:

### Samsung Vendor Path
```
device_common.mk: //depot/vendor/samsung/<model_branch>/device/<model>_common/device_common.mk
Samsung base:     //depot/vendor/samsung/<model_branch>/
```

### rscmgr.rc File
```
//depot/vendor/samsung/<model_branch>/system/rscmgr/<rscmgr_filename>
```

### Android.mk File
```
//depot/vendor/samsung/<model_branch>/system/rscmgr/Android.mk
```

### ReadaheadManager.java File
```
//depot/vendor/samsung/<model_branch>/frameworks/sdhms/java/com/sec/android/sdhms/performance/module/readahead/ReadaheadManager.java
```

### Derivation Logic

From a `device_common.mk` path like:
```
//depot/vendor/samsung/exynos850_beni/device/exynos850_common/device_common.mk
```

Extract the vendor samsung base path:
```
//depot/vendor/samsung/exynos850_beni/
```

Then append the target file's relative path.

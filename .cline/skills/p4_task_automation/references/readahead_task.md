# Readahead Task — Detailed Instructions

## Overview

The Readahead task adds library paths to the `rscmgr.rc` file(s) across branches (REL → Flumen → Beni). The user provides workspaces and library paths with their resource types. **This task does NOT use a VINCE reference branch** — it processes target branches directly.

## Input Required

1. **Workspace(s)** — At least ONE of: REL, Flumen, or Beni workspace (e.g., `TEMPLATE_ABC_REL`)
2. **Library paths** — System paths to add to the rscmgr.rc file (e.g., `dev/cpuset/sf/cpus`)
3. **Resource type for each library** — Either `Resource=1` or `Resource=2`

> **IMPORTANT**: If the user does not specify the resource type (1 or 2) for each library, you MUST ask them before proceeding. This is a required field.

### Library Path Examples

```
dev/cpuset/sf/cpus
dev/cpuset/foreground/cpus
sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
proc/sys/vm/dirty_ratio
```

## Target Files

### Primary: rscmgr.rc
Located at:
```
//depot/vendor/samsung/<model_branch>/system/rscmgr/<rscmgr_filename>
```

Where `<rscmgr_filename>` follows the pattern `rscmgr*.rc` (e.g., `rscmgr.rc`, `rscmgr_model.rc`).

### Secondary: device_common.mk
Located at:
```
//depot/vendor/samsung/<model_branch>/device/<model>_common/device_common.mk
```

Used to detect the rscmgr filename. If no rscmgr reference is found here, the user must provide the filename.

## rscmgr.rc File Format

The rscmgr.rc file defines readahead resources with entries like:

```
service rscmgr /system/bin/rscmgr
    class main
    user root
    group root

on property:sys.boot_completed=1
    write /dev/cpuset/sf/cpus 0-3
    write /dev/cpuset/foreground/cpus 0-7
```

Libraries are added as `write` directives with their paths. The `Resource` type determines which section/block the library belongs to.

### Resource Types

- **Resource=1**: Libraries that are written once at boot (e.g., CPU frequency limits, cpuset configurations)
- **Resource=2**: Libraries that need continuous monitoring/management

## Detailed Workflow

### Step 1: Receive and Validate Input

Required from user:
- At least ONE workspace (REL, Flumen, or Beni)
- At least ONE library path
- Resource type (1 or 2) for each library

If user provides libraries but NOT resource type → **Ask the user** which resource type to use.

### Step 2: Resolve Workspace → Find rscmgr Path

For each provided workspace:

#### 2.1 Find device_common.mk
```bash
p4 client -o <workspace_name>
# Parse View section → find device_common.mk depot path
# (See branch_resolution.md for details)
```

#### 2.2 Find Samsung Vendor Path
From the workspace's View section, find the `vendor/samsung/` base path.

#### 2.3 Check for Existing rscmgr Filename
```bash
p4 sync <device_common_mk_path>
```

Read the local file and search for rscmgr pattern:
```regex
rscmgr(?:_\w+)?\.rc
```

**Two outcomes:**

- **Found** (e.g., `rscmgr_model.rc`): Use this filename to construct the rscmgr file path:
  ```
  <samsung_path>/system/rscmgr/<rscmgr_filename>
  ```

- **NOT found**: The device_common.mk does not have a readahead feature yet. **Ask the user** what filename to use for the rscmgr file. The filename must:
  - Start with `rscmgr`
  - End with `.rc`
  - Example: `rscmgr.rc` or `rscmgr_model.rc`

### Step 3: Auto-Resolve Remaining Branches

If user provides only ONE workspace, auto-resolve others using integration history:

```
IF user provides REL → auto-resolve Flumen → auto-resolve Beni
IF user provides Flumen → auto-resolve Beni
IF user provides Beni → no further resolution
```

For rscmgr files specifically, cascade using `p4 filelog -i` on the rscmgr path:
```bash
p4 filelog -i <current_rscmgr_path>#1
# Parse "branch from" → get parent branch's rscmgr path
```

See [branch_resolution.md](branch_resolution.md) for detailed cascade logic.

### Step 4: Create Pending Changelist

```bash
p4 change -o
# Replace "<enter description here>" with: "Readahead - Add library paths to rscmgr"
p4 change -i
```

If user already provided a changelist ID, use that instead.

### Step 5: Process Each Branch

For each branch (in cascade order), process the rscmgr.rc file:

#### 5.1 Check if rscmgr File Exists

```bash
p4 files <rscmgr_path>
```

**If file EXISTS:**
```bash
p4 sync <rscmgr_path>
p4 edit -c <CL_NUMBER> <rscmgr_path>
# Edit the file to add new library entries
```

**If file DOES NOT EXIST:**
1. Need to create the file — also update device_common.mk and Android.mk:

   **Create rscmgr.rc:**
   ```bash
   # Sync rscmgr folder
   p4 sync <samsung_path>/system/rscmgr/...
   # Create new file locally with library entries
   # Add to P4
   p4 add -c <CL_NUMBER> <rscmgr_path>
   ```

   **Update device_common.mk** (add rscmgr reference):
   ```bash
   p4 edit -c <CL_NUMBER> <device_common_path>
   ```
   Append to file:
   ```makefile

   # Rscmgr 
   PRODUCT_PACKAGES += \
       <rscmgr_filename>
   ```

   **Update Android.mk** (add module definition):
   ```bash
   p4 edit -c <CL_NUMBER> <android_mk_path>
   ```
   Append module block:
   ```makefile

   include $(CLEAR_VARS)
   LOCAL_MODULE := <rscmgr_filename>
   LOCAL_MODULE_TAGS := optional
   LOCAL_MODULE_CLASS := ETC
   LOCAL_MODULE_PATH := $(TARGET_OUT)/etc/init
   LOCAL_SRC_FILES := $(LOCAL_MODULE)
   include $(BUILD_PREBUILT)
   ```

#### 5.2 Edit rscmgr.rc — Add Library Entries

Add library paths to the appropriate section based on resource type.

**For Resource=1 libraries**, add entries like:
```
    write /<library_path> <value>
```

**For Resource=2 libraries**, add entries like:
```
    write /<library_path> <value>
```

> **Note**: The exact format depends on the existing file structure. Read the current file content and follow the same pattern for new entries. Maintain consistent indentation (typically 4 spaces).

#### 5.3 Repeat for Each Branch

Apply the same library additions to each branch's rscmgr file.

### Step 6: Report Summary

```
[SUMMARY] Readahead process completed
[SUMMARY] Libraries added:
[SUMMARY]   Resource=1: dev/cpuset/sf/cpus, dev/cpuset/foreground/cpus
[SUMMARY]   Resource=2: proc/sys/vm/dirty_ratio
[SUMMARY] Branches processed: REL → FLUMEN → BENI
[SUMMARY] Changelist: <CL_NUMBER>
```

## Key Differences from Other Tasks

| Aspect | Readahead | Other Tasks |
|--------|-----------|-------------|
| VINCE reference | ❌ Not used | ✅ Used by Bringup & old System |
| Primary target file | `rscmgr.rc` | `device_common.mk` / `ReadaheadManager.java` |
| User provides | Library paths + resource type | Property values / asset names |
| May create new files | ✅ Yes (rscmgr.rc, device_common.mk ref, Android.mk module) | ❌ Usually edits existing |

## Error Handling

- No workspace provided → Report error
- No libraries provided → Report error
- Resource type not specified → **Ask user** (do NOT guess)
- rscmgr filename not detected → **Ask user** for filename
- rscmgr file doesn't exist → Create new file + update device_common.mk + Android.mk
- Integration cascade fails → Ask user whether to continue with remaining branches

## Changelist Description

When creating the pending changelist, preserve the full template structure and only modify the [Title] field:

**For Readahead tasks, set the [Title] field to:**
```
[Title] Readahead - Add library paths to rscmgr
```

**Example of correct changelist template:**
```
Change:	new

Client:	<client_name>

User:	<user_name>

Status:	new

Description:
	[Title] Readahead - Add library paths to rscmgr
	[Module] 
	[Model] 
	[Chipset] 
	[Region] 
	[Customer] 
	[Type] 
	[Issue#] 
	[Problem] 
	[Cause] 
	[Measure] 
	[Checking Method] 
	[Developer]
```

**DO NOT replace the entire template with just "Readahead - Add library paths to rscmgr" - this is incorrect.**

If user provides their own changelist ID, use that instead of creating a new one.

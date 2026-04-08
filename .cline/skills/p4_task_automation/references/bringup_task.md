# Bringup Task — Detailed Instructions

## Overview

The Bringup task synchronizes LMKD and Chimera property blocks from a VINCE (reference) branch to one or more target branches (BENI, Flumen, REL). It compares properties first and only creates a changelist if there are actual differences.

## Input Required

1. **VINCE workspace or depot path** (mandatory) — The reference source for property values
2. **Target branches** — At least one of:
   - **BENI** workspace or depot path
   - **Flumen** workspace or depot path
   - **REL** workspace or depot path

> **Note**: Unlike other tasks, Bringup does NOT cascade. Each target branch must be provided explicitly. The user can provide any combination of 1-3 target branches.

## Target File

`device_common.mk` — Located at:
```
//depot/vendor/samsung/<model_branch>/device/<model>_common/device_common.mk
```

## Detailed Workflow

### Step 1: Validate and Resolve All Inputs

For each input (VINCE + targets):

**If workspace name** (starts with `TEMPLATE`):
```bash
# Use find_device_common.py script to resolve workspace to device_common.mk path
python .cline/skills/p4_task_automation/scripts/find_device_common.py <workspace_name>
```

**If depot path** (starts with `//`):
```bash
p4 files <depot_path>  # Validate it exists
```

Skip any target that fails validation (log warning, continue with others).

### Step 2: Map and Sync All Files

Map all valid depot paths into the client spec:

```bash
# Use map_path.py script to map each depot path
python .cline/skills/p4_task_automation/scripts/map_path.py <depot_path>
```

Sync all files (NO checkout yet — we compare first):
```bash
p4 sync <vince_depot_path>
p4 sync <beni_depot_path>      # if provided
p4 sync <flumen_depot_path>    # if provided
p4 sync <rel_depot_path>       # if provided
```

### Step 3: Validate VINCE Has Properties

Read the VINCE local file and check for property blocks:

- Look for `# LMKD property` or `# DHA property` header
- Look for `# Chimera property` header

If NEITHER block exists in VINCE → **Stop and report error**: "VINCE file does not contain LMKD or Chimera properties"

### Step 4: Compare Properties (Key Step)

For each target file, compare properties with VINCE:

#### 4.1 Extract Property Blocks

From both VINCE and target files, extract:

**LMKD/DHA block**:
1. Find header line: `# LMKD property` or `# DHA property` (case-insensitive)
2. Read lines below until next `#` comment or empty line
3. Parse `key=value` pairs (skip PRODUCT_PROPERTY_OVERRIDES lines, comment lines, empty lines)
4. Strip backslash continuation (`\`)

**Chimera block**:
1. Find header line: `# Chimera property` (case-insensitive)
2. Read lines below until next `#` comment, empty line, or `# Nandswap`
3. Parse `key=value` pairs same as above

#### 4.2 Compare Property Dictionaries

Compare extracted properties between VINCE and target:

- **Same key, different value** → Mark as "needs update"
- **Key in VINCE but not in target** → Mark as "needs add"
- **Key in target but not in VINCE** → Mark as "needs delete"

If there are NO differences → Target is in sync, skip it.

### Step 5: Create Changelist (Only If Needed)

If ALL targets are in sync → **Report success, no changes needed. Stop here.**

If any target has differences → Create changelist:
```
Create Changelist for Bringup Process
```

### Step 6: Checkout and Update Files

For each target file that has differences:

#### 6.1 Checkout
```bash
p4 edit -c <CL_NUMBER> <target_depot_path>
```

#### 6.2 Copy Property Blocks from VINCE

The update is a **block-level copy** from VINCE to target — replacing the entire content between the header and the block boundary while keeping the header.

**For LMKD/DHA block**:
1. In the target file, find `# LMKD property` (or `# DHA property`) header
2. Find the block boundary (empty line or next `#` comment)
3. Extract the CONTENT lines from VINCE's LMKD/DHA block (everything after the header line, before boundary)
4. Replace the target's block content with VINCE's content
5. Keep the target's header line intact (preserve `# LMKD property` vs `# DHA property` naming)

**For Chimera block**:
1. Same process as above but for `# Chimera property` header

#### 6.3 Write Updated File

Write the modified content back to the local file.

### Step 7: Report Summary

```
[SUCCESS] Bringup process completed successfully!
[SUMMARY] Updated targets: BENI, FLUMEN
[SUMMARY] All changes are in shared changelist: <CL_NUMBER>
```

If some targets were already in sync:
```
[OK] REL properties are identical to VINCE (no changes needed)
[DIFF] BENI has 5 property differences → Updated
[DIFF] FLUMEN has 3 property differences → Updated
```

## Property Block Replacement — Detailed Example

### VINCE file (source):
```makefile
# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \
    ro.lmk.critical=0 \
    ro.lmk.low=1001 \
    ro.lmk.medium=800

# Chimera property
PRODUCT_PROPERTY_OVERRIDES += \
    persist.sys.chimera.memory_tier=low \
    persist.sys.chimera.cfg_enable=true
```

### Target file (BENI) BEFORE:
```makefile
# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \
    ro.lmk.critical=50 \
    ro.lmk.low=900

# Chimera property
PRODUCT_PROPERTY_OVERRIDES += \
    persist.sys.chimera.memory_tier=high
```

### Target file (BENI) AFTER update:
```makefile
# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \
    ro.lmk.critical=0 \
    ro.lmk.low=1001 \
    ro.lmk.medium=800

# Chimera property
PRODUCT_PROPERTY_OVERRIDES += \
    persist.sys.chimera.memory_tier=low \
    persist.sys.chimera.cfg_enable=true
```

The ENTIRE content of each block is replaced — the header line is preserved, but all properties below it come from VINCE.

## Error Handling

- VINCE has no properties → Stop with error
- Target validation fails → Skip that target, continue with others
- Target has no property blocks → Still update (add blocks from VINCE)
- All targets already in sync → Report success with "No changes needed"

## Changelist Description

When creating the pending changelist, preserve the full template structure and only modify the [Title] field:

**For Bringup tasks, set the [Title] field to:**
```
[Title] Create Changelist for Bringup Process
```

**Example of correct changelist template:**
```
Change:	new

Client:	<client_name>

User:	<user_name>

Status:	new

Description:
	[Title] Create Changelist for Bringup Process
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

**DO NOT replace the entire template with just "Create Changelist for Bringup Process" - this is incorrect.**

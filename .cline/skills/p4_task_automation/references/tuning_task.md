# Tuning Task — Detailed Instructions

## Overview

The Tuning task edits LMKD and Chimera property values in `device_common.mk` files across multiple branches (REL, Flumen, Beni). The user provides property values to change, and the Agent applies them to all resolved branches.

## Input Required

1. **Workspace name** (e.g., `TEMPLATE_ABC_REL`) and which branch it belongs to
2. **Property changes**: Key-value pairs to modify, add, or delete
   - Example: "Change `ro.lmk.critical` to `100`, add `ro.lmk.debug` = `true`"

## Target File

`device_common.mk` — Located at:
```
//depot/vendor/samsung/<model_branch>/device/<model>_common/device_common.mk
```

## File Format

The `device_common.mk` file contains property blocks with this structure:

```makefile
# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \
    ro.lmk.critical=0 \
    ro.lmk.low=1001 \
    ro.lmk.medium=800 \
    ro.lmk.psi_partial_stall_ms=70 \
    ro.lmk.swap_free_low_percentage=20

# Chimera property
PRODUCT_PROPERTY_OVERRIDES += \
    persist.sys.chimera.memory_tier=low \
    persist.sys.chimera.cfg_enable=true \
    persist.sys.chimera.cpulimit_enable=true
```

### Property Block Structure

- **Header line**: `# LMKD property` or `# DHA property` or `# Chimera property`
- **PRODUCT_PROPERTY_OVERRIDES line**: `PRODUCT_PROPERTY_OVERRIDES += \`
- **Property lines**: `    key=value \` (4-space indent, backslash continuation)
- **Last property line**: `    key=value` (no backslash)
- **Block boundary**: Empty line or next `#` comment line

> **Note**: Some files use `# DHA property` instead of `# LMKD property`. They are equivalent — treat them the same way.

## Detailed Workflow

### Step 1: Common Steps (See SKILL.md)

Follow SKILL.md Steps 1–5:
1. Resolve workspace → depot path (Use find_device_common.py script)
2. Auto-resolve remaining branches
3. Create pending changelist with description: **"Tuning - Apply property changes to all paths"**
4. Map all depot paths (Use map_path.py script for each path)

### Step 2: For Each Branch (REL, Flumen, Beni)

#### 2.1 Sync and Checkout
```bash
p4 sync <device_common_mk_depot_path>
p4 edit -c <CL_NUMBER> <device_common_mk_depot_path>
```

#### 2.2 Read Current Properties

Read the local file and extract property blocks:

1. Find the `# LMKD property` (or `# DHA property`) header line
2. Read all lines below until an empty line or another `#` comment line
3. Parse each property line:
   - Strip leading whitespace
   - Remove trailing ` \` (backslash with optional space)
   - Split by `=` to get key and value
   - Skip lines with `PRODUCT_PROPERTY_OVERRIDES`
   - Skip comment lines starting with `#`
4. Repeat for `# Chimera property` block

#### 2.3 Apply Property Changes

For each property change requested by the user:

**Modify existing value**:
- Find the line containing the property key
- Replace the value in-place
- Preserve the original indentation and backslash continuation

**Add new property**:
- Add the new `key=value` line before the last property in the block
- Add ` \` to what was previously the last line
- The new line becomes the last line (no backslash)

**Delete property**:
- Remove the line containing the property key
- Fix backslash continuation on the new last line (remove `\` from it)
- If the property was in the middle, keep the `\` continuation

#### 2.4 Write Updated File

Write the modified content back to the local file path.

### Step 3: Report

Report:
- Changelist number
- Properties changed (old value → new value for each)
- Branches processed
- Files modified

## Property Editing Rules

### Preserving Format

1. **Indentation**: Properties inside `PRODUCT_PROPERTY_OVERRIDES +=` blocks typically use 4-space indentation. Preserve the existing indentation.
2. **Backslash continuation**: All lines except the last in a `PRODUCT_PROPERTY_OVERRIDES +=` block end with ` \`
3. **Multiple override blocks**: A single property block (e.g., LMKD) may contain multiple `PRODUCT_PROPERTY_OVERRIDES +=` sub-blocks. Process each independently.
4. **Comments**: Preserve any inline comments (e.g., `key=value # comment`)

### Example Edit

**Before** (LMKD block):
```makefile
# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \
    ro.lmk.critical=0 \
    ro.lmk.low=1001 \
    ro.lmk.medium=800
```

**User request**: Change `ro.lmk.critical` to `100`, delete `ro.lmk.low`

**After**:
```makefile
# LMKD property
PRODUCT_PROPERTY_OVERRIDES += \
    ro.lmk.critical=100 \
    ro.lmk.medium=800
```

Note: `ro.lmk.medium` lost its position as last item — backslash on `ro.lmk.critical` remains because it's no longer the last property.

## Changelist Description

When creating the pending changelist, preserve the full template structure and only modify the [Title] field:

**For Tuning tasks, set the [Title] field to:**
```
[Title] Tuning - Apply property changes to all paths
```

**Example of correct changelist template:**
```
Change:	new

Client:	<client_name>

User:	<user_name>

Status:	new

Description:
	[Title] Tuning - Apply property changes to all paths
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

**DO NOT replace the entire template with just "Tuning - Apply property changes to all paths" - this is incorrect.**

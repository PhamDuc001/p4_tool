---
name: p4_task_automation
description: Automate Perforce (P4) tasks for Samsung performance tuning workflows including Tuning, Readahead, LoadApkAsset, and Bringup. Handles workspace resolution, branch cascading (REL → Flumen → Beni), file editing, and pending changelist creation.
---

# P4 Task Automation Skill

## Overview

This skill enables the AI Agent to perform automated Perforce (P4) tasks for Samsung device performance tuning workflows. The Agent executes P4 commands and edits files directly on the user's local machine.

## Supported Tasks

| Task | Description | Keywords to Detect |
|------|-------------|-------------------|
| **Tuning** | Edit LMKD/Chimera properties in `device_common.mk` | tuning, tunning, LMKD, chimera, property, beks |
| **Readahead** | Add library paths to `rscmgr.rc` across branches (no VINCE reference) | readahead, rscmgr, lib, library, resource |
| **LoadApkAsset** | Add asset apps to chipset in `ReadaheadManager.java` | loadapkasset, asset, gallery, camera, app |
| **Bringup** | Sync LMKD/Chimera properties from VINCE to other branches | bringup, sync property, sync tuning |

## Branch Hierarchy

The Samsung vendor branches follow this integration hierarchy:

```
REL (Release) → Flumen (Development) → Beni (Base)
```

- **VINCE**: Reference/source branch (read-only, provides the "golden" values)
- **REL**: Release branch (closest to VINCE)
- **Flumen**: Development branch (integrated from REL)
- **Beni**: Base branch (integrated from Flumen)

When the user provides a workspace for ONE branch, the Agent auto-resolves the remaining branches by tracing the P4 integration history (`p4 filelog -i <path>#1` → parse `branch from` line).

## Workspace Identification

User workspaces follow the naming pattern: `TEMPLATE_*` (e.g., `TEMPLATE_ABC_REL`, `TEMPLATE_XYZ_FLUMEN`).

If the user's input starts with `TEMPLATE`, treat it as a workspace name. If it starts with `//`, treat it as a depot path.

## Resolving Workspace to device_common.mk Path

When a workspace name is provided, use the `find_device_common.py` script to resolve it to the `device_common.mk` depot path:

```bash
# Script location: .cline/skills/p4_task_automation/scripts/find_device_common.py
python .cline/skills/p4_task_automation/scripts/find_device_common.py <workspace_name>
```

If the script returns a path, use it as the `device_common.mk` depot path. If it returns nothing (empty), the workspace does not contain a valid `device_common.mk` path.

## Mapping Depot Paths

When a depot path needs to be mapped to the client spec, use the `map_path.py` script:

```bash
# Script location: .cline/skills/p4_task_automation/scripts/map_path.py
python .cline/skills/p4_task_automation/scripts/map_path.py <depot_path>
```

The script will map the depot path to the current client spec and return success or failure.

## Common Workflow (All Tasks)

Every task follows this general workflow. Read the **task-specific reference** for detailed file editing instructions.

### Step 1: Receive Input from User
- **Workspace name** (e.g., `TEMPLATE_ABC_REL`) — OR — **depot path** (e.g., `//depot/.../device_common.mk`)
- **Branch type**: REL, Flumen, or Beni
- **Task-specific parameters** (property values, asset names, chipset, etc.)

### Step 2: Resolve Workspace to Depot Paths
If the input is a workspace name, resolve it to the `device_common.mk` depot path.

👉 **Read**: [references/branch_resolution.md](references/branch_resolution.md) for detailed resolution logic.

**Quick summary**:
```bash
# Get workspace client spec
p4 client -o <workspace_name>

# Parse the View section to find device_common.mk path
# Look for pattern: /device/<model>_common/...
# Construct: <base_path>/device/<model>_common/device_common.mk
```

### Step 3: Auto-Resolve Remaining Branches
Use integration history to cascade and find depot paths for other branches.

👉 **Read**: [references/branch_resolution.md](references/branch_resolution.md) for cascade logic.

**Quick summary**:
```bash
# Get integration source from version #1
p4 filelog -i <depot_path>#1

# Parse output for "... ... branch from <source_path>#<version>"
# Extract <source_path> as the parent branch's depot path
```

**Cascade direction**:
- REL input → resolve Flumen → resolve Beni
- Flumen input → resolve Beni
- Beni input → no further resolution needed

### Step 4: Create Pending Changelist
```bash
# Get changelist template
p4 change -o

# Replace "<enter description here>" with task-specific description
# Submit via stdin
p4 change -i
# Output: "Change <CL_NUMBER> created."
```

### Step 5: Map Depot Paths to Client Spec
```bash
# Get current client spec
p4 client -o

# Add View mappings for each depot path (if not already mapped):
#   <depot_path>   //<client_name>/<depot_path_without_//>

# Save updated spec
p4 client -i
```

### Step 6: Sync, Checkout, and Edit Files
For each target file in each branch:
```bash
# Sync latest version
p4 sync <depot_path>

# Checkout into the pending changelist
p4 edit -c <CL_NUMBER> <depot_path>

# Edit the local file using file editing tools
# (task-specific editing logic - see reference docs)
```

### Step 7: Report Summary
After completing all edits, report:
- Pending changelist number
- List of files modified
- Branches processed
- What was changed

## Task-Specific References

Based on the user's request, read the appropriate reference document:

| User Request | Reference Document |
|-------------|-------------------|
| Tuning / LMKD / Chimera properties | [references/tuning_task.md](references/tuning_task.md) |
| Readahead / rscmgr / library bringup | [references/readahead_task.md](references/readahead_task.md) |
| LoadApkAsset / add app assets | [references/loadapkasset_task.md](references/loadapkasset_task.md) |
| Bringup / sync properties from VINCE | [references/bringup_task.md](references/bringup_task.md) |

## P4 Command Reference

👉 **Read**: [references/p4_commands.md](references/p4_commands.md) for complete P4 command patterns.

## Important Rules

1. **Always create a pending changelist BEFORE checking out files.** Never checkout files to the default changelist.
2. **Always sync files BEFORE checking out.** This ensures you're editing the latest version.
3. **Check if a file is already opened** before checkout (`p4 opened <path>`). If already opened in another CL, ask the user whether to move it.
4. **Validate depot paths** before operations (`p4 files <path>`). If the path doesn't exist, report the error.
5. **Preserve file formatting** when editing. Maintain indentation, line endings, and comment structure.
6. **Report all actions taken** with clear log-style output so the user can verify.
7. **Handle errors gracefully**. If one branch fails, ask the user whether to continue with remaining branches.
8. **DO NOT create temporary files** - All operations should be performed directly using P4 commands and in-memory processing.
9. **Use P4 commands directly** - Avoid creating intermediate files. Use stdin/stdout piping for P4 command operations.
10. **Follow the established workflow** - Each task has a specific workflow that must be followed exactly.
11. **Preserve changelist template structure** - When creating a changelist, ALWAYS keep the full template structure with all fields ([Title], [Module], [Model], etc.). Only modify the [Title] field based on the task type. DO NOT replace the entire template with a simple description.

## Depot Path to Local Path Conversion

The local file path is constructed by joining the workspace root with the relative depot path:

```
Local Path = <WORKSPACE_ROOT> + <depot_path without "//depot/">
```

To find the workspace root:
```bash
p4 client -o
# Parse "Root:" field from output
```

Example:
- Depot: `//depot/vendor/samsung/.../device_common.mk`
- Root: `D:\workspace`
- Local: `D:\workspace\vendor\samsung\...\device_common.mk`
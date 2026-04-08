# P4 Command Reference

## Quick Reference Table

| Command | Purpose |
|---------|---------|
| `p4 client -o <name>` | Get client spec (read View mappings, Root) |
| `p4 client -i` | Save modified client spec (via stdin) |
| `p4 change -o` | Get changelist template |
| `p4 change -i` | Create changelist from template (via stdin) |
| `p4 sync <path>` | Sync file from depot to local |
| `p4 edit -c <CL> <path>` | Checkout file for editing in a specific CL |
| `p4 files <path>` | Check if depot path exists |
| `p4 filelog -i <path>#1` | Get integration history (for branch resolution) |
| `p4 add -c <CL> <path>` | Add a new file to P4 |
| `p4 opened <path>` | Check if file is already checked out |
| `p4 reopen -c <CL> <path>` | Move opened file to different CL |

---

## Detailed Command Patterns

### 1. Get Client Spec (Read Workspace Info)

```bash
p4 client -o <workspace_name>
```

**Output format**:
```
Client: TEMPLATE_ABC_REL
Root:   D:\workspace\abc
...
View:
    //depot/vendor/samsung/model_rel/... //TEMPLATE_ABC_REL/vendor/samsung/model_rel/...
    //depot/vendor/samsung/model_rel/device/model_common/... //TEMPLATE_ABC_REL/vendor/samsung/...
```

**Key fields to parse**:
- `Client:` — Workspace name
- `Root:` — Local filesystem root path
- `View:` — Depot-to-client path mappings (one per line, indented with tab)

### 2. Modify Client Spec (Add View Mappings)

```bash
# Step 1: Get current spec
p4 client -o > spec.txt

# Step 2: Modify spec (add/update View lines)
# Each View line format:
#   <tab><depot_path><tab>//<client_name>/<relative_path>

# Step 3: Save modified spec via stdin
p4 client -i < spec.txt
```

**In practice** (as a single command pipeline):
```bash
# Get spec, pipe through edit, save back
p4 client -o | <modify View section> | p4 client -i
```

**Agent approach**: Use `run_command` to get the spec, then modify it in memory, then pipe back via `p4 client -i` with stdin input.

### 3. Create Pending Changelist

```bash
# Step 1: Get template
p4 change -o
```

**Template output** (relevant part):
```
Change: new
Description:
    <enter description here>
```

**Step 2**: Replace `<enter description here>` with the task description.

**Step 3**: Submit via stdin:
```bash
echo "<modified_spec>" | p4 change -i
```

**Output**: `Change 12345678 created.`

Parse the CL number from this output using regex: `Change (\d+)`

### 4. Sync File from Depot

```bash
p4 sync <depot_path>
```

Example:
```bash
p4 sync //depot/vendor/samsung/.../device_common.mk
```

### 5. Checkout File for Editing

```bash
p4 edit -c <changelist_number> <depot_path>
```

**Before checkout**, check if the file is already opened:
```bash
p4 opened <depot_path>
```

**Output when not opened**: Contains "not opened on this client"
**Output when opened**: `//depot/.../file#6 - edit change 32339139 (text)`

If the file is already opened in a different CL, use reopen:
```bash
p4 reopen -c <target_CL> <depot_path>
```

### 6. Validate Depot Path Exists

```bash
p4 files <depot_path>
```

**If exists**: Returns file info like `//depot/.../file#3 - edit change 12345 (text)`
**If not exists**: Returns error containing "no such file"

### 7. Get Integration History

```bash
p4 filelog -i <depot_path>#1
```

**Output format**:
```
//depot/.../device_common.mk
... #1 change 1234567 branch on 2024/01/15 by user@workspace (text) 'Initial branch'
... ... branch from //depot/.../device_common.mk#1
```

**Parse target**: The `... ... branch from <source_path>#<version>` line.

Extract `<source_path>` by:
1. Finding the line starting with `... ... branch from `
2. Removing the prefix `... ... branch from `
3. Removing `#<version>` suffix (everything after last `#`)
4. Removing `,<range>` suffix if present (everything after `,` if before `#`)

### 8. Add New File to P4

```bash
p4 add -c <changelist_number> <depot_path>
```

Used when creating a new file (e.g., new rscmgr.rc) that doesn't exist in the depot yet.

---

## Depot Path to Local Path Conversion

```
local_path = <workspace_root> + <relative_depot_path>
```

Where:
- `<workspace_root>` = `Root:` field from `p4 client -o`
- `<relative_depot_path>` = depot path with `//depot/` prefix removed, and `/` converted to `\` on Windows

**Example**:
```
Depot path:  //depot/vendor/samsung/model_beni/device/model_common/device_common.mk
Root:        D:\workspace\abc
Relative:    vendor\samsung\model_beni\device\model_common\device_common.mk
Local path:  D:\workspace\abc\vendor\samsung\model_beni\device\model_common\device_common.mk
```

---

## Error Handling

- If any `p4` command returns non-zero exit code, check `stderr` for error messages
- Common errors:
  - `"not opened on this client"` — File not checked out (safe to proceed with checkout)
  - `"no such file"` — Depot path doesn't exist (path validation failure)
  - `"can't edit (already opened"` — File is already checked out in another CL
  - `"must refer to client"` — View mapping not set up (need to map first)

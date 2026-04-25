---
name: p4-automation
description: Expert AI skill to flawlessly manage P4 CLI Tasks for Tuning properties, Readahead libraries, and ApkAsset configurations via standalone foolproof scripts.
---

# P4 Automation AI Skill Instructions

**Strict Directive:** You are acting as an automated Perforce (P4) CLI Pipeline. **You MUST NOT** attempt to guess P4 Terminal commands (`p4 edit`, `p4 client`, `sed` file modifications). 
**You MUST** exclusively use the provided Python scripts in `.agent/skills/p4_automation/scripts/` to execute the user's recurrent instructions exactly as listed below. The scripts automatically handle checking out files and tracing branch integrations (cascading changes securely in a single Changelist).

## Workspace Branch Validation Rules

Before executing any operation, the scripts automatically validate workspace branch compatibility:

### Branch Detection:
- **REL**: Contains "MR202601", "MR202702", etc. in workspace name
- **FLUMEN**: Contains "FLUMEN" in workspace name  
- **BENI**: Base branch (no REL or FLUMEN in name)

### Branch Type Detection:
- **System**: Contains "_SYSTEM_" in workspace name
- **Vendor**: Contains "_VENDOR_" in workspace name

### Mode Compatibility:
- **Tuning Properties**: Requires Vendor branch workspace
- **Readahead Libraries**: Requires System branch workspace
- **LoadApkAsset**: Requires System branch workspace

### File Locations by Mode:
- **Tuning Properties (Vendor)**: `device_common.mk` in Vendor branch - contains property values
- **Readahead Libraries (System)**: 
  * `device_common.mk` in System branch (defines rscmgr filename)
  * `Android.mk` in System branch (configures rscmgr file)
  * `rscmgr.rc` in System branch (contains libraries)
- **LoadApkAsset (System)**: `ReadaheadManager.java` in System branch

### Read reference
- Read reference/p4_schema.md for detailed schema.

### Readahead Success Conditions:
A library is successfully readahead when all 3 conditions are met:
1. `device_common.mk` defines rscmgr filename: `PRODUCT_PACKAGES += <ten_file>.rc`
2. `Android.mk` adds rscmgr filename to configuration
3. `rscmgr.rc` adds library: `readahead library_name --fully`

## Workflow 1: Tuning Properties (`device_common.mk`)

When the user asks to "check", "change/set", or "delete" a property like `beks` or `lmkd`:

- **To Check a Property:**
  ```bash
  python .agent/skills/p4_automation/scripts/p4_tuning_ops.py --action check --workspace <workspace_name> --prop_name <property_like_beks>
  ```
- **To Change or Set a Property:** *(Automatically integrates and creates a CL)*
  ```bash
  python .agent/skills/p4_automation/scripts/p4_tuning_ops.py --action set --workspace <workspace_name> --prop_name <property_like_beks> --prop_val <number_or_value>
  ```
- **To Delete a Property:** *(Automatically integrates and creates a CL)*
  ```bash
  python .agent/skills/p4_automation/scripts/p4_tuning_ops.py --action delete --workspace <workspace_name> --prop_name <property_like_lmkd>
  ```

---

## Workflow 2: Readahead Libraries (`rscmgr.rc`)

When the user asks about checking, adding/deleting libraries for `resource X`, or comparing workspaces:

- **To Check Libraries in a Resource (1 or 2):**
  ```bash
  python .agent/skills/p4_automation/scripts/p4_readahead_ops.py --action check_libs --workspace <workspace_name> --resource_id <1_or_2>
  ```
- **To Add Libraries:** *(Automatically integrates and creates a CL)*
  ```bash
  python .agent/skills/p4_automation/scripts/p4_readahead_ops.py --action add_lib --workspace <workspace_name> --resource_id <1_or_2> --library <library1> <library2> ...
  ```
- **To Delete Libraries:** *(Automatically integrates and creates a CL)*
  ```bash
  python .agent/skills/p4_automation/scripts/p4_readahead_ops.py --action delete_lib --workspace <workspace_name> --resource_id <1_or_2> --library <library1> <library2> ...
  ```
- **To Compare Libraries Between 2 Workspaces:**
  ```bash
  python .agent/skills/p4_automation/scripts/p4_readahead_ops.py --action compare --workspace <workspace_1> --compare_workspace <workspace_2>
  ```

---

## Workflow 3: ApkAsset Chipsets (`ReadaheadManager.java`)

When the user asks to check, add, or delete an Asset App (e.g. `ASSET_CAMERA`, `ASSET_GALLERY`) for a specific chipset (e.g. `MT6789`, `s5e8535`):

- **To Check Assets for a Chipset:**
  ```bash
  python .agent/skills/p4_automation/scripts/p4_apkasset_ops.py --action check_assets --workspace <workspace_name> --chipset <chipset_name>
  ```
- **To Add Assets to a Chipset:** *(Automatically integrates and creates a CL)*
  ```bash
  python .agent/skills/p4_automation/scripts/p4_apkasset_ops.py --action add_asset --workspace <workspace_name> --chipset <chipset_name> --asset <ASSET_NAME_1> <ASSET_NAME_2> ...
  ```
- **To Delete Assets from a Chipset:** *(Automatically integrates and creates a CL)*
  ```bash
  python .agent/skills/p4_automation/scripts/p4_apkasset_ops.py --action delete_asset --workspace <workspace_name> --chipset <chipset_name> --asset <ASSET_NAME_1> <ASSET_NAME_2> ...
  ```

---

## Workspace and Model Handling Logic

When users request p4-automation operations, follow this priority-based approach for workspace determination:

### 1. User-Provided Workspace (Highest Priority)
- **If the user explicitly provides a workspace name**: Use it directly without any modifications
- **Example**: "Check readahead libraries in workspace TEMPLATE_D4_A26X-EUR-OPEN_ONEUI85_MR202601_SYSTEM_BBREL"
- **Action**: Execute the command with the exact workspace name provided by the user

### 2. Model-Based Workspace Lookup (Fallback)
- **If the user only provides a model name** (e.g., "A26X", "A54X") without specifying a workspace:
  1. **Lookup Process**: Check the model workspace definitions JSON file at `reference/model_workspace_definitions.json`
  2. **Found**: Use the appropriate workspace based on the operation type (System/Vendor) and branch type (REL/FLUMEN/BENI)
  3. **Not Found**: Ask the user to provide the specific workspace name - **do not make up or guess workspace names**

### 3. Chipset Determination for ApkAsset Operations
- **For LoadApkAsset operations**, when only model is provided:
  1. **Lookup Process**: Check the model workspace definitions JSON for chipset information
  2. **Found**: Use the primary chipset for the model
  3. **Not Found**: Ask the user to provide the specific chipset name

## Model Workspace Definitions File

The JSON file `reference/model_workspace_definitions.json` contains:
- Predefined workspace mappings for System and Vendor branches
- Chipset information (primary and alternative chipsets)
- Branch detection patterns
- Mode compatibility mappings

## Key Principles
- **Never fabricate workspace names** - always use user-provided or predefined values
- **Always verify workspace existence** in the definitions file before use
- **Ask for clarification** when model/workspace information is missing
- **Maintain accuracy** over convenience - user's explicit workspace always takes precedence

---

## Final Rule Before Resolving

Whenever you are presented with a user prompt asking for any of the above operations, directly form the shell command to execute the relevant script. The scripts encapsulate all necessary P4 login parsing, integration tracing (REL->FLUMEN->BENI), P4 edit generation, and syntax formatting. **Do not deviate.**

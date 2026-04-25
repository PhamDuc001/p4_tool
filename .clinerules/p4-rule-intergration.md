# P4 Integration Rules for Workspace Detection

## Branch Hierarchy
The correct integration flow is: **BENI → FLUMEN → REL**

This means:
- BENI is the base branch (earliest)
- FLUMEN is integrated from BENI  
- REL is integrated from FLUMEN (latest)

## Workspace Detection Rules

### 1. When User Provides REL Workspace
**Detect in CL:** REL branch only (have "MR202601, MR202702, etc." in path)
- Path pattern: `//PROD_BENI/ONEUI_8_5/ONEUI_8_5_MR202601/SYSTEM/...`

### 2. When User Provides FLUMEN Workspace  
**Detect in CL:** FLUMEN and REL branches
- FLUMEN path pattern (have FLUMEN in path): `//PROD_BENI/ONEUI_8_5/FLUMEN/SYSTEM/...`
- REL path pattern (have REL in path): `//PROD_BENI/ONEUI_8_5/ONEUI_8_5_MR202601/SYSTEM/...`

### 3. When User Provides BENI Workspace
**Detect in CL:** BENI, FLUMEN, and REL branches
- BENI path pattern: `//BENI/SYSTEM/...`
- FLUMEN path pattern: `//PROD_BENI/ONEUI_8_5/FLUMEN/SYSTEM/...`  
- REL path pattern: `//PROD_BENI/ONEUI_8_5/ONEUI_8_5_MR202601/SYSTEM/...`

## Mandatory User Confirmation Rules

### 1. Workspace Branch Clarification
**When creating a CL, if the user provides a workspace but does not specify which branch it belongs to (REL, FLUMEN, or BENI), you MUST immediately ask the user to clarify the workspace branch before proceeding.**

### 2. Command Execution Permission
**You MUST NOT execute any commands or make assumptions without explicit user permission. If there are any questions, issues, or uncertainties when running p4-automation skills, you MUST ask the user for confirmation before proceeding.**

### 3. Script Execution Waiting
**You MUST wait for p4-automation Python scripts to complete execution and return actual results. You MUST NOT fabricate, invent, or make up content in this file or any other files. All changes must be based on actual script execution results and user confirmation.**

## Example File Paths for rscmgr
- **BENI Branch:** `//BENI/SYSTEM/Cinnamon/vendor/samsung/system/rscmgr/rscmgr.rc`
- **FLUMEN Branch:** `//PROD_BENI/ONEUI_8_5/FLUMEN/SYSTEM/Cinnamon/vendor/samsung/system/rscmgr/rscmgr.rc`
- **REL Branch:** `//PROD_BENI/ONEUI_8_5/ONEUI_8_5_MR202601/SYSTEM/Cinnamon/vendor/samsung/system/rscmgr/rscmgr.rc`

## Applies To
These rules apply to all p4-automation operations:
- Tuning Properties (`device_common.mk`)
- Readahead Libraries (`rscmgr.rc`)
- ApkAsset Chipsets (`ReadaheadManager.java`)

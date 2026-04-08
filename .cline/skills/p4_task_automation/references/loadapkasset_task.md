# LoadApkAsset Task — Detailed Instructions

## Overview

The LoadApkAsset task adds asset app entries to specific chipset blocks in `ReadaheadManager.java`. This enables readahead preloading for specific apps on specific chipsets. The changes cascade across branches (REL → Flumen → Beni).

## Input Required

1. **Workspace name** — At least one of REL, Flumen, or Beni workspace (e.g., `TEMPLATE_ABC_REL`)
2. **Chipset name** — Target chipset (e.g., `EXYNOS850`, `EXYNOS990`, `S5E8825`)
3. **Asset apps to add** — One or more from the available list

## Available Asset Apps

| Asset Constant | App |
|----------------|-----|
| `ASSET_CAMERA` | Camera |
| `ASSET_DIAL` | Dial/Phone |
| `ASSET_CLOCK` | Clock |
| `ASSET_CONTACT` | Contacts |
| `ASSET_CALENDAR` | Calendar |
| `ASSET_CALCULATOR` | Calculator |
| `ASSET_GALLERY` | Gallery |
| `ASSET_MESSAGE` | Messages |
| `ASSET_MYFILE` | My Files |
| `ASSET_SBROWSER` | Samsung Browser |
| `ASSET_NOTE` | Notes |
| `ASSET_SETTINGS` | Settings |
| `ASSET_VOICENOTE` | Voice Recorder |

> **Tip**: If the user says "add Gallery", map it to `ASSET_GALLERY`. If they say "Camera and Gallery", map to `ASSET_CAMERA` and `ASSET_GALLERY`.

## Target File

`ReadaheadManager.java` — Located at:
```
//depot/vendor/samsung/<model_branch>/frameworks/sdhms/java/com/sec/android/sdhms/performance/module/readahead/ReadaheadManager.java
```

## File Structure

The relevant part of `ReadaheadManager.java` is the `initModel()` method, which contains chipset-specific blocks:

```java
private void initModel() {
    if (PerformanceFeature.CHIP_EXYNOS850) {
        mReadahead.updateModel((byte) 0x02);
        mReadahead.updateDiskType(DISK_UFS);
        mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_GALLERY | ASSET_MESSAGE);
    } else if (PerformanceFeature.CHIP_EXYNOS990) {
        mReadahead.updateModel((byte) 0x03);
        mReadahead.updateDiskType(DISK_UFS);
        mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_DIAL | ASSET_CLOCK);
    } else if (PerformanceFeature.CHIP_S5E8825) {
        mReadahead.updateModel((byte) 0x04);
        mReadahead.updateDiskType(DISK_UFS);
        mReadahead.updateAssetKey(ASSET_CAMERA);
    }
}
```

### Key Observations

- Each chipset block starts with `if (PerformanceFeature.CHIP_<chipset>)` or `else if (...)`
- The `mReadahead.updateAssetKey(...)` call contains the asset list, separated by ` | `
- Assets are simple constants (no object prefix needed)

## Detailed Workflow

### Step 1: Determine Cascade Order

Based on which workspace the user provides:

| User Provides | Cascade Order |
|--------------|---------------|
| REL workspace | REL → FLUMEN → BENI |
| Flumen workspace | FLUMEN → BENI |
| Beni workspace | BENI only |

### Step 2: Create Changelist

```bash
# Create pending changelist
p4 change -o | <replace description> | p4 change -i
```

**Description**: `LoadApkAsset - Add asset apps to chipsets`

### Step 3: Process First Branch (From Workspace)

#### 3.1 Find ReadaheadManager.java

```bash
p4 client -o <workspace_name>
# Parse View section to find vendor/samsung/ base path
```

Construct the path:
```
<samsung_path>/frameworks/sdhms/java/com/sec/android/sdhms/performance/module/readahead/ReadaheadManager.java
```

#### 3.2 Validate, Sync, Checkout
```bash
p4 files <readahead_manager_path>     # Validate exists
p4 sync <readahead_manager_path>      # Sync latest
p4 edit -c <CL> <readahead_manager_path>  # Checkout
```

#### 3.3 Edit the File

1. **Find the chipset block**: Search for `if (PerformanceFeature.CHIP_<chipset_name>)` or `else if (PerformanceFeature.CHIP_<chipset_name>)`

2. **Find the updateAssetKey call** within that block:
   ```java
   mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_GALLERY)
   ```

3. **Extract current assets**: Parse the parameter string to get current asset list
   - Split by ` | ` to get individual constants
   - Example: `"ASSET_CAMERA | ASSET_GALLERY"` → `["ASSET_CAMERA", "ASSET_GALLERY"]`

4. **Check for duplicates**: Filter out any assets that already exist in the list

5. **Build new asset string**: Combine existing + new assets with ` | ` separator

6. **Replace the updateAssetKey call**:
   ```java
   // Before:
   mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_GALLERY)
   
   // After (adding ASSET_MESSAGE and ASSET_CLOCK):
   mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_GALLERY | ASSET_MESSAGE | ASSET_CLOCK)
   ```

7. **Write the modified content** back to the local file

### Step 4: Cascade to Remaining Branches

For each remaining branch in the cascade:

#### 4.1 Get Integration Source
```bash
p4 filelog -i <current_readahead_manager_path>#1
# Parse "branch from" → get parent branch's ReadaheadManager.java path
```

#### 4.2 Process the Cascaded Branch
```bash
p4 files <cascaded_path>        # Validate
p4 sync <cascaded_path>         # Sync
p4 edit -c <CL> <cascaded_path> # Checkout
```

Apply the same asset additions (Step 3.3) to this branch's file.

### Step 5: Report Summary

```
[SUMMARY] Chipset: <chipset_name>
[SUMMARY] Assets added: ASSET_GALLERY, ASSET_CLOCK
[SUMMARY] Changelist: <CL_NUMBER>
[SUMMARY] Cascaded branches: REL → FLUMEN → BENI
```

## Edit Example

### Before (CHIP_EXYNOS850 block):
```java
if (PerformanceFeature.CHIP_EXYNOS850) {
    mReadahead.updateModel((byte) 0x02);
    mReadahead.updateDiskType(DISK_UFS);
    mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_GALLERY);
}
```

### User Request: "Add ASSET_MESSAGE and ASSET_SETTINGS to EXYNOS850"

### After:
```java
if (PerformanceFeature.CHIP_EXYNOS850) {
    mReadahead.updateModel((byte) 0x02);
    mReadahead.updateDiskType(DISK_UFS);
    mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_GALLERY | ASSET_MESSAGE | ASSET_SETTINGS);
}
```

## Error Handling

- If chipset is not found in `initModel()` → Report error with list of available chipsets
- If all requested assets already exist → Report "No changes needed"
- If integration cascade fails → Ask user whether to continue with remaining branches
- If `ReadaheadManager.java` doesn't exist → Report error

## Changelist Description

When creating the pending changelist, preserve the full template structure and only modify the [Title] field:

**For LoadApkAsset tasks, set the [Title] field to:**
```
[Title] LoadApkAsset - Add asset apps to chipsets
```

**Example of correct changelist template:**
```
Change:	new

Client:	<client_name>

User:	<user_name>

Status:	new

Description:
	[Title] LoadApkAsset - Add asset apps to chipsets
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

**DO NOT replace the entire template with just "LoadApkAsset - Add asset apps to chipsets" - this is incorrect.**

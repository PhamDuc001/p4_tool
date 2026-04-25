# P4 Source Schema & Integration Reference

This document provides schema templates for the 3 core files manipulated by the P4 Automation Scripts. **Agents do not need to manually parse these files**, as the scripts in `scripts/` handle it automatically. This is strictly for context.

---

## 1. Tuning Properties (`device_common.mk`)

**Location Format:** `vendor/.../device_common.mk`
**Purpose:** Sets build-time configuration properties such as `lmkd` behavior, `beks` triggers, or `Chimera` thresholds.

**Schema Example:**
```makefile
# LMKD property
    PRODUCT_PROPERTY_OVERRIDES += \
    ro.lmkd.kill_heaviest_task=true \
    ro.lmkd.beks=4 \
    ro.lmkd.foo=true \

# Chimera property
    PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.chimera=true \
```

---

## 2. Readahead Libraries (`rscmgr.rc`)

**Location Format:** `vendor/samsung/.../system/rscmgr/rscmgr*.rc`
**Purpose:** Preloads heavy `.so` libraries strictly ordered into execution 'Resources' to improve app start latencies.

**Schema Example:**
```rc
# Resource 1 (First Phase)
on property:sys.readahead.resource=1
    readahead /vendor/lib64/libcamera_algo.so --fully
    readahead /vendor/lib64/libOpenCL.so --fully

# Resource 2 (Second Phase)
on property:sys.readahead.resource=2
    readahead /vendor/lib64/hw/camera.mt6789.so --fully
```

---

## 3. ApkAssets Chipset Assignments (`ReadaheadManager.java`)

**Location Format:** `frameworks/sdhms/java/com/sec/android/sdhms/performance/module/readahead/ReadaheadManager.java`
**Purpose:** Binds major system Android Apps (`ASSET_*`) directly to specific Hardware/Chip lines (e.g. `CHIP_MT6789`) ensuring the Readahead manager targets them optimally.

**Schema Example:**
```java
private void initModel() {
    if (PerformanceFeature.CHIP_MT6789) {
        mReadahead.updateAssetKey(ASSET_CAMERA | ASSET_GALLERY | ASSET_CALCULATOR);
    } else if (PerformanceFeature.CHIP_S5E8535) {
        mReadahead.updateAssetKey(ASSET_CONTACT | ASSET_MESSAGE);
    }
}
```

---

> [!NOTE]
> All changes made using the P4 Automation scripts are designed to auto-cascade. If a property/library/asset is requested to be changed on the `REL` (Release) branch, the scripts trace the P4 integration history and also checkout and commit the modification directly onto the upstream `FLUMEN` and `BENI` (Base Platform) branches inside the exact same Pending Changelist.

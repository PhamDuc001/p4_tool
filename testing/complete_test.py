import sys
import tempfile
import os
sys.path.insert(0, '.')

# Test the complete update flow
from core.file_operations import update_properties_in_file

# Test content with conditional blocks - original problematic case
test_content = """# LMKD property
ifneq ($(filter %zn %ctc %zm %zc %zcx, $(TARGET_PRODUCT)), )
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.enable_upgrade_criadj=true \\
    ro.slmk.use_bg_keeping_policy_light=true
else
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.use_bg_keeping_policy=true
endif

PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.dha_2ndprop_thMB=8192 \\
    ro.slmk.dha_cached_min=4 \\
    ro.slmk.dha_empty_min=8 \\
    ro.slmk.dha_empty_max=30 \\
    ro.slmk.2nd.dha_cached_min=4 \\
    ro.slmk.2nd.dha_empty_min=8 \\
    ro.slmk.freelimit_val=14 \\
    ro.slmk.psi_medium=70 \\
    ro.slmk.psi_critical=120 \\
    ro.slmk.swap_free_low_percentage=15 \\
    ro.slmk.2nd.swap_free_low_percentage=10 \\
    ro.slmk.use_lowmem_keep_except=true \\
    ro.slmk.dha_lmk_scale=2.0 \\
    ro.slmk.cam_dha_ver=3 \\
    ro.slmk.cam_kill_start_minutes=30 \\
    ro.slmk.add_bonusEFK=2 \\
    ro.slmk.v_bonusEFK=15692 \\
    ro.slmk.reentry_mode_enable=true \\
    ro.slmk.plg_key=97286 \\
    ro.slmk.2nd.dha_lmk_scale=3.0
	
# Chimera property
ifneq ($(filter usa%, $(PROJECT_REGION)), )
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.chimera_strategy_8gb=1024,24,10,2550 \\
    ro.slmk.chimera_strategy_12gb=1024,28,14,2857
else
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.chimera_strategy_8gb=1228,24,10,2550 \\
    ro.slmk.chimera_strategy_12gb=1228,28,14,2857
endif
"""

print("=== COMPLETE TEST: Property Update with Conditional Blocks ===")
print("Original content:")
print(test_content)
print("\n" + "="*60)

# Write to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
    f.write(test_content)
    temp_file = f.name

try:
    # Test property update: change ro.slmk.plg_key from 97286 to 1520
    properties_dict = {
        "LMKD": {
            "ro.slmk.plg_key": "1520"
        },
        "Chimera": {}
    }
    
    print("Updating property: ro.slmk.plg_key = 1520")
    success, error = update_properties_in_file(temp_file, properties_dict)
    
    if success:
        print("[SUCCESS] Update successful!")
        # Read and display result
        with open(temp_file, 'r') as f:
            result = f.read()
            print("\nResult content:")
            print(result)
            
            # Verify the change
            if "ro.slmk.plg_key=1520" in result:
                print("[SUCCESS] Property value updated correctly!")
            else:
                print("[ERROR] Property value not updated!")
                
            # Verify conditional structure preserved
            if "ifneq" in result and "else" in result and "endif" in result:
                print("[SUCCESS] Conditional structure preserved!")
            else:
                print("[ERROR] Conditional structure lost!")
                
            # Verify no duplicate properties
            plg_key_count = result.count("ro.slmk.plg_key")
            if plg_key_count == 1:
                print("[SUCCESS] No duplicate properties!")
            else:
                print(f"[ERROR] Found {plg_key_count} instances of ro.slmk.plg_key (should be 1)!")
                
    else:
        print(f"❌ Update failed: {error}")
        
finally:
    # Cleanup
    os.unlink(temp_file)

print("\n=== Test completed ===")
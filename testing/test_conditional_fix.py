#!/usr/bin/env python3
"""
Test script to verify conditional block handling fix
"""
import os
import sys
import tempfile
import shutil
sys.path.append('..')
from core.file_operations import update_properties_in_file

def test_case_1():
    """Test case 1: Original problematic file content"""
    print("=== Test Case 1: Original problematic file ===")
    
    # Create test file with original content
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
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        # Test property update
        properties_dict = {
            "LMKD": {
                "ro.slmk.plg_key": "1520"
            },
            "Chimera": {}
        }
        
        success, error = update_properties_in_file(temp_file, properties_dict)
        
        if success:
            print("✅ Update successful")
            # Read and display result
            with open(temp_file, 'r') as f:
                result = f.read()
                print("Result:")
                print(result)
        else:
            print(f"❌ Update failed: {error}")
            
    finally:
        # Cleanup
        os.unlink(temp_file)

def test_case_2():
    """Test case 2: Testing file from testing/device_common.mk"""
    print("\n=== Test Case 2: Testing file content ===")
    
    # Read the testing file
    test_file = "testing/device_common.mk"
    
    if os.path.exists(test_file):
        # Create a copy for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
            with open(test_file, 'r') as source:
                f.write(source.read())
            temp_file = f.name
        
        try:
            # Test property update
            properties_dict = {
                "LMKD": {
                    "ro.slmk.plg_key": "1024"
                },
                "Chimera": {}
            }
            
            success, error = update_properties_in_file(temp_file, properties_dict)
            
            if success:
                print("✅ Update successful")
                # Read and display result
                with open(temp_file, 'r') as f:
                    result = f.read()
                    print("Result:")
                    print(result)
            else:
                print(f"❌ Update failed: {error}")
                
        finally:
            # Cleanup
            os.unlink(temp_file)
    else:
        print(f"❌ Test file {test_file} not found")

if __name__ == "__main__":
    print("Testing conditional block handling fix...")
    test_case_1()
    test_case_2()
    print("\n=== Test completed ===")
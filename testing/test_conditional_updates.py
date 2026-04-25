import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.file_operations import update_properties_in_file, analyze_conditional_structure

# Test content với conditional structures
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
    ro.slmk.plg_key=97286

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

# Test case 1: Update chi ifneq context trong Chimera
def test_update_ifneq_context_only():
    print("=== TEST 1: Update chi ifneq context trong Chimera ===")
    
    # Tạo test file
    with open('test_device_common.mk', 'w') as f:
        f.write(test_content)
    
    # Properties dict mô phỏng enhanced dialog result
    properties_dict = {
        "Chimera": {
            "ro.slmk.chimera_strategy_8gb": {
                "values_by_context": {
                    "[ifneq ($(filter usa%, $(PROJECT_REGION)), )]": "2048,32,15,3000",
                    "[else]": "1228,24,10,2550"
                },
                "selected_contexts": ["[ifneq ($(filter usa%, $(PROJECT_REGION)), )]"]
            }
        }
    }
    
    # Update file
    success, error = update_properties_in_file('test_device_common.mk', properties_dict)
    
    if success:
        print("[OK] Update thanh cong")
        # Đọc file kết quả
        with open('test_device_common.mk', 'r') as f:
            result_content = f.read()
        
        print("Content sau khi update:")
        print(result_content)
        
        # Verify kết quả
        if "ro.slmk.chimera_strategy_8gb=2048,32,15,3000" in result_content:
            print("[OK] Value ifneq context da duoc update")
        else:
            print("[ERROR] Value ifneq context KHONG duoc update")
            
        if "ro.slmk.chimera_strategy_8gb=1228,24,10,2550" in result_content:
            print("[OK] Value else context duoc giu nguyen")
        else:
            print("[ERROR] Value else context BI THAY DOI")
    else:
        print(f"[ERROR] Update that bai: {error}")
    
    # Cleanup
    if os.path.exists('test_device_common.mk'):
        os.remove('test_device_common.mk')

# Test case 2: Update ca 2 contexts
def test_update_both_contexts():
    print("\n=== TEST 2: Update ca 2 contexts ===")
    
    # Tạo test file
    with open('test_device_common.mk', 'w') as f:
        f.write(test_content)
    
    # Properties dict update cả 2 contexts
    properties_dict = {
        "Chimera": {
            "ro.slmk.chimera_strategy_12gb": {
                "values_by_context": {
                    "[ifneq ($(filter usa%, $(PROJECT_REGION)), )]": "2048,32,15,3000",
                    "[else]": "2456,36,20,3500"
                },
                "selected_contexts": ["[ifneq ($(filter usa%, $(PROJECT_REGION)), )]", "[else]"]
            }
        }
    }
    
    # Update file
    success, error = update_properties_in_file('test_device_common.mk', properties_dict)
    
    if success:
        print("[OK] Update thanh cong")
        # Đọc file kết quả
        with open('test_device_common.mk', 'r') as f:
            result_content = f.read()
        
        print("Content sau khi update:")
        print(result_content)
        
        # Verify kết quả
        if "ro.slmk.chimera_strategy_12gb=2048,32,15,3000" in result_content:
            print("[OK] Value ifneq context da duoc update")
        else:
            print("[ERROR] Value ifneq context KHONG duoc update")
            
        if "ro.slmk.chimera_strategy_12gb=2456,36,20,3500" in result_content:
            print("[OK] Value else context da duoc update")
        else:
            print("[ERROR] Value else context KHONG duoc update")
    else:
        print(f"[ERROR] Update that bai: {error}")
    
    # Cleanup
    if os.path.exists('test_device_common.mk'):
        os.remove('test_device_common.mk')

# Test case 3: Mixed conditional va flat properties
def test_mixed_properties():
    print("\n=== TEST 3: Mixed conditional va flat properties ===")
    
    # Tạo test file
    with open('test_device_common.mk', 'w') as f:
        f.write(test_content)
    
    # Properties dict với cả conditional và flat
    properties_dict = {
        "Chimera": {
            "ro.slmk.chimera_strategy_8gb": {
                "values_by_context": {
                    "[ifneq ($(filter usa%, $(PROJECT_REGION)), )]": "2048,32,15,3000",
                    "[else]": "1228,24,10,2550"
                },
                "selected_contexts": ["[ifneq ($(filter usa%, $(PROJECT_REGION)), )]"]
            },
            "ro.slmk.chimera_strategy_12gb": "3000,40,20,4000"  # Flat property
        },
        "LMKD": {
            "ro.slmk.plg_key": "1520"  # Flat property
        }
    }
    
    # Update file
    success, error = update_properties_in_file('test_device_common.mk', properties_dict)
    
    if success:
        print("[OK] Update thanh cong")
        # Đọc file kết quả
        with open('test_device_common.mk', 'r') as f:
            result_content = f.read()
        
        print("Content sau khi update:")
        print(result_content)
        
        # Verify kết quả
        if "ro.slmk.chimera_strategy_8gb=2048,32,15,3000" in result_content:
            print("[OK] Conditional property ifneq context da duoc update")
        else:
            print("[ERROR] Conditional property ifneq context KHONG duoc update")
            
        if "ro.slmk.chimera_strategy_12gb=3000,40,20,4000" in result_content:
            print("[OK] Flat Chimera property da duoc update")
        else:
            print("[ERROR] Flat Chimera property KHONG duoc update")
            
        if "ro.slmk.plg_key=1520" in result_content:
            print("[OK] Flat LMKD property da duoc update")
        else:
            print("[ERROR] Flat LMKD property KHONG duoc update")
    else:
        print(f"[ERROR] Update that bai: {error}")
    
    # Cleanup
    if os.path.exists('test_device_common.mk'):
        os.remove('test_device_common.mk')

if __name__ == "__main__":
    print("BAT DAU TESTING CONDITIONAL-AWARE UPDATES")
    print("=" * 50)
    
    test_update_ifneq_context_only()
    test_update_both_contexts()
    test_mixed_properties()
    
    print("\n" + "=" * 50)
    print("TESTING HOAN TAT")

import sys
import tempfile
import os
sys.path.insert(0, '.')

from core.file_operations import update_properties_in_file

def test_complex_conditional_update():
    """Test complex conditional block handling"""
    print("=== FINAL VERIFICATION TEST ===")
    
    # Complex test content with multiple conditional blocks and properties
    test_content = """# LMKD property
ifneq ($(filter %zn %ctc %zm %zc %zcx, $(TARGET_PRODUCT)), )
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.enable_upgrade_criadj=true \\
    ro.slmk.use_bg_keeping_policy_light=true \\
    ro.slmk.plg_key=97286
else
PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.use_bg_keeping_policy=true \\
    ro.slmk.plg_key=74756
endif

PRODUCT_PROPERTY_OVERRIDES += \\
    ro.slmk.dha_2ndprop_thMB=8192 \\
    ro.slmk.plg_key=12345

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

    print("Original content:")
    print(test_content)
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
        f.write(test_content)
        temp_file = f.name

    try:
        # Test updating multiple properties in different conditional scopes
        properties_dict = {
            "LMKD": {
                "ro.slmk.plg_key": "1520",  # This should update in the global block
                "ro.slmk.dha_2ndprop_thMB": "4096"
            },
            "Chimera": {
                "ro.slmk.chimera_strategy_8gb": "2048,32,16,3000"
            }
        }
        
        print("\nUpdating properties:")
        print("- ro.slmk.plg_key = 1520 (should update in global block)")
        print("- ro.slmk.dha_2ndprop_thMB = 4096")
        print("- ro.slmk.chimera_strategy_8gb = 2048,32,16,3000")
        
        success, error = update_properties_in_file(temp_file, properties_dict)
        
        if success:
            print("\n[SUCCESS] Update successful!")
            
            # Read and display result
            with open(temp_file, 'r') as f:
                result = f.read()
                print("\nResult content:")
                print(result)
                
                # Verification checks
                checks = [
                    ("ro.slmk.plg_key=1520" in result, "Global plg_key updated"),
                    ("ro.slmk.dha_2ndprop_thMB=4096" in result, "dha_2ndprop_thMB updated"),
                    ("ro.slmk.chimera_strategy_8gb=2048,32,16,3000" in result, "chimera_strategy_8gb updated"),
                    (result.count("ifneq") == 2, "Conditional ifneq preserved"),
                    (result.count("else") == 2, "Conditional else preserved"), 
                    (result.count("endif") == 2, "Conditional endif preserved"),
                    (result.count("ro.slmk.plg_key") == 3, "All plg_key instances preserved (2 in conditional + 1 global)"),
                ]
                
                all_passed = True
                for check, description in checks:
                    if check:
                        print(f"[PASS] {description}")
                    else:
                        print(f"[FAIL] {description}")
                        all_passed = False
                
                if all_passed:
                    print("\n[SUCCESS] All verification checks passed!")
                else:
                    print("\n[WARNING] Some checks failed - review output above")
                    
        else:
            print(f"\n[ERROR] Update failed: {error}")
            
    finally:
        os.unlink(temp_file)

if __name__ == "__main__":
    test_complex_conditional_update()
    print("\n=== Final verification completed ===")
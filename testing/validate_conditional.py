import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.file_operations import analyze_conditional_structure

# Real-world content từ P4 file
content = """# LMKD property
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
endif"""

print("=== REAL-WORLD CONDITIONAL ANALYSIS ===")
result = analyze_conditional_structure(content)

for section, data in result.items():
    print(f"\n{section} Section:")
    for i, block in enumerate(data['blocks']):
        print(f"  Block {i+1}: {block['condition']}")
        print(f"    If Properties: {len(block['properties'])}")
        for prop in block['properties']:
            print(f"      {prop['key']} = {prop['value']}")
        if block['else_properties']:
            print(f"    Else Properties: {len(block['else_properties'])}")
            for prop in block['else_properties']:
                print(f"      {prop['key']} = {prop['value']}")

print("\n=== VALIDATION COMPLETE ===")
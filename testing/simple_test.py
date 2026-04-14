import sys
sys.path.insert(0, '.')

# Test the updated functions
from core.file_operations import analyze_product_override_blocks, update_product_override_block_with_deletions

# Test content with conditional blocks
test_lines = [
    "# LMKD property\n",
    "ifneq ($(filter %zn %ctc %zm %zc %zcx, $(TARGET_PRODUCT)), )\n",
    "PRODUCT_PROPERTY_OVERRIDES += \\\n",
    "    ro.slmk.enable_upgrade_criadj=true \\\n",
    "    ro.slmk.use_bg_keeping_policy_light=true\n",
    "else\n",
    "PRODUCT_PROPERTY_OVERRIDES += \\\n",
    "    ro.slmk.use_bg_keeping_policy=true\n",
    "endif\n",
    "\n",
    "PRODUCT_PROPERTY_OVERRIDES += \\\n",
    "    ro.slmk.plg_key=97286 \\\n",
    "    ro.slmk.dha_2ndprop_thMB=8192\n"
]

print("Testing analyze_product_override_blocks...")
blocks = analyze_product_override_blocks(test_lines)
print(f"Found {len(blocks)} blocks:")
for i, block in enumerate(blocks):
    print(f"  Block {i+1}: start={block['start']}, properties={block['properties']}")
    if 'conditional_context' in block:
        print(f"    Conditional context: {block['conditional_context']}")

print("\nTest completed successfully!")
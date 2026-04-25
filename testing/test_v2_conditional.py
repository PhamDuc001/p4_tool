#!/usr/bin/env python3
"""
Core logic test for conditional block fix
Tests:
1. extract_properties_from_file correctly separates if/else contexts
2. update_properties_in_file with v2 struct only changes what was actually modified
"""
import sys, tempfile, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.file_operations import (
    extract_properties_from_file,
    update_properties_in_file,
    get_flat_properties_for_display,
    validate_conditional_structure_match
)

TEST_CONTENT = r"""# LMKD property
ifneq ($(filter %zn %ctc, $(TARGET_PRODUCT)), )
PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.enable_upgrade_criadj=true \
    ro.slmk.use_bg_keeping_policy_light=true
else
PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.use_bg_keeping_policy=true
endif

PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.plg_key=97286 \
    ro.slmk.psi_medium=70

# Chimera property
ifneq ($(filter usa%, $(PROJECT_REGION)), )
PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.chimera_strategy_8gb=1024,24,10,2550 \
    ro.slmk.chimera_strategy_12gb=1024,28,14,2857
else
PRODUCT_PROPERTY_OVERRIDES += \
    ro.slmk.chimera_strategy_8gb=1228,24,10,2550 \
    ro.slmk.chimera_strategy_12gb=1228,28,14,2857
endif
"""

def make_tempfile(content):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name


def test_1_extraction():
    """Bug 1: GUI only shows else values. This test verifies we now correctly separate if/else."""
    print("=== TEST 1: Extraction correctly separates if/else contexts ===")
    tmp = make_tempfile(TEST_CONTENT)
    try:
        props = extract_properties_from_file(tmp)
        assert props is not None, "extract returned None"

        lmkd = props.get('LMKD', {})
        assert '_flat' in lmkd, "LMKD missing _flat"
        assert '_conditional' in lmkd, "LMKD missing _conditional"
        assert len(lmkd['_conditional']) == 1, f"Expected 1 LMKD conditional block, got {len(lmkd['_conditional'])}"

        lmkd_cond = lmkd['_conditional'][0]
        assert 'ro.slmk.enable_upgrade_criadj' in lmkd_cond['if_props'], "ifneq prop missing from LMKD if_props"
        assert 'ro.slmk.use_bg_keeping_policy' in lmkd_cond['else_props'], "else prop missing from LMKD else_props"
        assert 'ro.slmk.plg_key' in lmkd['_flat'], "Flat LMKD prop missing"
        assert lmkd['_flat']['ro.slmk.plg_key'] == '97286', "Wrong flat value"

        chimera = props.get('Chimera', {})
        assert len(chimera['_conditional']) == 1, f"Expected 1 Chimera conditional block, got {len(chimera['_conditional'])}"
        cond = chimera['_conditional'][0]
        assert cond['if_props'].get('ro.slmk.chimera_strategy_8gb') == '1024,24,10,2550', \
            f"Wrong ifneq value: {cond['if_props'].get('ro.slmk.chimera_strategy_8gb')}"
        assert cond['else_props'].get('ro.slmk.chimera_strategy_8gb') == '1228,24,10,2550', \
            f"Wrong else value: {cond['else_props'].get('ro.slmk.chimera_strategy_8gb')}"

        print("  [OK] LMKD conditional if_props correctly extracted")
        print("  [OK] LMKD conditional else_props correctly extracted")
        print("  [OK] LMKD flat props correctly extracted")
        print("  [OK] Chimera ifneq value = 1024 (NOT 1228)")
        print("  [OK] Chimera else value = 1228")
        print("TEST 1: PASSED")
        return props
    finally:
        os.unlink(tmp)


def test_2_apply_lmkd_only_chimera_preserved():
    """Bug 2: Applying LMKD changes must NOT modify Chimera conditional blocks."""
    print("\n=== TEST 2: Apply LMKD flat change only — Chimera must be preserved ===")
    tmp = make_tempfile(TEST_CONTENT)
    try:
        props = extract_properties_from_file(tmp)
        lmkd = props['LMKD']
        chimera = props['Chimera']

        # Simulate user only changing plg_key in LMKD flat section
        lmkd_flat_modified = dict(lmkd['_flat'])
        lmkd_flat_modified['ro.slmk.plg_key'] = '1520'  # Changed

        props_to_apply = {
            'LMKD': {
                '_flat': lmkd_flat_modified,
                '_conditional': lmkd['_conditional']  # Pass through unchanged
            },
            'Chimera': {
                '_flat': chimera['_flat'],
                '_conditional': chimera['_conditional']  # Pass through unchanged
            }
        }

        success, err = update_properties_in_file(tmp, props_to_apply)
        assert success, f"Update failed: {err}"

        with open(tmp, 'r', encoding='utf-8') as f:
            result = f.read()

        assert 'ro.slmk.plg_key=1520' in result, "plg_key not updated"
        assert 'ro.slmk.chimera_strategy_8gb=1024,24,10,2550' in result, \
            "Chimera ifneq (1024) was DESTROYED — Bug 2 still present!"
        assert 'ro.slmk.chimera_strategy_8gb=1228,24,10,2550' in result, \
            "Chimera else (1228) was destroyed"
        assert 'ro.slmk.chimera_strategy_12gb=1024,28,14,2857' in result, \
            "Chimera 12gb ifneq was DESTROYED"

        print("  [OK] ro.slmk.plg_key successfully updated to 1520")
        print("  [OK] Chimera ifneq block (1024) preserved")
        print("  [OK] Chimera else block (1228) preserved")
        print("TEST 2: PASSED")
    finally:
        os.unlink(tmp)


def test_3_apply_chimera_ifneq_only():
    """Test: update only the ifneq context of Chimera, else must stay the same."""
    print("\n=== TEST 3: Apply Chimera ifneq context — else must be preserved ===")
    tmp = make_tempfile(TEST_CONTENT)
    try:
        props = extract_properties_from_file(tmp)
        chimera = props['Chimera']
        lmkd = props['LMKD']

        # Simulate user changing only the ifneq values of chimera_strategy_8gb
        new_chimera_conditional = []
        for block in chimera['_conditional']:
            new_block = dict(block)
            new_if = dict(block['if_props'])
            new_if['ro.slmk.chimera_strategy_8gb'] = '2048,32,15,3000'  # Changed
            new_block['if_props'] = new_if
            # else_props unchanged
            new_chimera_conditional.append(new_block)

        props_to_apply = {
            'LMKD': {'_flat': lmkd['_flat'], '_conditional': lmkd['_conditional']},
            'Chimera': {'_flat': chimera['_flat'], '_conditional': new_chimera_conditional}
        }

        success, err = update_properties_in_file(tmp, props_to_apply)
        assert success, f"Update failed: {err}"

        with open(tmp, 'r', encoding='utf-8') as f:
            result = f.read()

        assert 'ro.slmk.chimera_strategy_8gb=2048,32,15,3000' in result, \
            "Chimera ifneq not updated to 2048"
        assert 'ro.slmk.chimera_strategy_8gb=1228,24,10,2550' in result, \
            "Chimera else (1228) was destroyed"
        # chimera_12gb should be unchanged
        assert 'ro.slmk.chimera_strategy_12gb=1024,28,14,2857' in result, \
            "Chimera 12gb ifneq was destroyed (not touched)"
        assert 'ro.slmk.chimera_strategy_12gb=1228,28,14,2857' in result, \
            "Chimera 12gb else was destroyed"

        print("  [OK] Chimera 8gb ifneq updated to 2048")
        print("  [OK] Chimera 8gb else (1228) preserved")
        print("  [OK] Chimera 12gb both contexts untouched")
        print("TEST 3: PASSED")
    finally:
        os.unlink(tmp)


def test_4_flat_display():
    """Test: get_flat_properties_for_display returns sensible flat dict."""
    print("\n=== TEST 4: get_flat_properties_for_display ===")
    tmp = make_tempfile(TEST_CONTENT)
    try:
        props = extract_properties_from_file(tmp)
        flat = get_flat_properties_for_display(props)
        assert 'LMKD' in flat, "LMKD missing from flat"
        assert 'Chimera' in flat, "Chimera missing from flat"
        # Chimera flat should contain both contexts merged (else overrides)
        assert 'ro.slmk.chimera_strategy_8gb' in flat['Chimera'], "chimera_8gb missing from flat"
        print(f"  Chimera flat chimera_8gb = {flat['Chimera']['ro.slmk.chimera_strategy_8gb']}")
        print("TEST 4: PASSED")
    finally:
        os.unlink(tmp)


def test_5_structure_match():
    """Test: validate_conditional_structure_match detects mismatches."""
    print("\n=== TEST 5: validate_conditional_structure_match ===")
    tmp = make_tempfile(TEST_CONTENT)
    try:
        props_a = extract_properties_from_file(tmp)
        props_b = extract_properties_from_file(tmp)

        is_match, diffs = validate_conditional_structure_match(props_a, props_b)
        assert is_match, f"Same file should match: {diffs}"
        print("  [OK] Same file matches itself")

        # Modify props_b to have different structure
        props_b['Chimera']['_conditional'] = []
        is_match, diffs = validate_conditional_structure_match(props_a, props_b)
        assert not is_match, "Different structure should not match"
        print(f"  [OK] Different structure detected: {diffs}")
        print("TEST 5: PASSED")
    finally:
        os.unlink(tmp)


if __name__ == '__main__':
    results = []
    for test_fn in [test_1_extraction, test_2_apply_lmkd_only_chimera_preserved,
                    test_3_apply_chimera_ifneq_only, test_4_flat_display, test_5_structure_match]:
        try:
            test_fn()
            results.append(('PASS', test_fn.__name__))
        except AssertionError as e:
            print(f"  [FAIL] {e}")
            results.append(('FAIL', test_fn.__name__))
        except Exception as e:
            import traceback
            print(f"  [ERROR] {e}")
            traceback.print_exc()
            results.append(('ERROR', test_fn.__name__))

    print("\n" + "=" * 50)
    print("SUMMARY:")
    for status, name in results:
        icon = "✅" if status == 'PASS' else "❌"
        print(f"  {icon} {status}: {name}")
    all_pass = all(s == 'PASS' for s, _ in results)
    print("=" * 50)
    sys.exit(0 if all_pass else 1)

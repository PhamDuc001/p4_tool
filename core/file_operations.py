"""
Enhanced File operations for LMKD and Chimera properties with Delete Property support
Handles file reading, writing, and property extraction/deletion
"""
import os
import shutil
from datetime import datetime

def find_block_boundaries_improved(lines, start_header):
    """Find start and end indices of a block - IMPROVED with case-insensitive"""
    start = end = None
    
    # Find start header (case-insensitive)
    for idx, line in enumerate(lines):
        if line.strip().lower() == start_header.lower():
            start = idx
            break
    
    if start is None:
        return None, None
    
    # Find end boundary (empty line or comment line)
    for idx in range(start + 1, len(lines)):
        line_stripped = lines[idx].strip()
        
        # End at empty line
        if not line_stripped:
            end = idx
            break
        
        # End at any comment line
        if line_stripped.startswith('#'):
            end = idx
            break
    
    if end is None:
        end = len(lines)
    
    return start, end

def extract_block_content(lines, start_header):
    """Extract ONLY content within block (excluding header) - case-insensitive"""
    start, end = find_block_boundaries_improved(lines, start_header)
    
    if start is None:
        return []
    
    # Return content after header, before next boundary
    return lines[start+1:end]

def replace_block_content(target_lines, new_content_lines, start_header):
    """Replace ONLY content within block, keep header and other blocks intact"""
    start, end = find_block_boundaries_improved(target_lines, start_header)
    
    if start is None:
        # Block not found, append at end
        return target_lines + [start_header + "\n"] + new_content_lines
    
    # Build result: keep header, replace content, keep rest
    result = target_lines[:start+1]  # Include header line
    result.extend(new_content_lines)   # New content
    result.extend(target_lines[end:])    # Rest of file (including next headers/blocks)
    
    return result

def extract_block(lines, start_header, next_header_list):
    """Extract block of lines between headers - LEGACY (kept for backward compatibility)"""
    start = end = None
    for idx, line in enumerate(lines):
        if line.strip() == start_header:
            start = idx
            break
    if start is None:
        return []

    for idx in range(start + 1, len(lines)):
        if lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(lines)
    return lines[start:end]

def validate_properties_exist(file_path):
    """Check if LMKD and Chimera properties exist in file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        has_lmkd = "# LMKD property" in content or "# DHA property" in content
        has_chimera = "# Chimera property" in content
        
        return has_lmkd, has_chimera
    except:
        return False, False

def replace_block(target_lines, block_lines, start_header, next_header_list):
    """Replace block in target lines with new block"""
    start = end = None
    for idx, line in enumerate(target_lines):
        if line.strip() == start_header:
            start = idx
            break
    if start is None:
        return target_lines

    for idx in range(start + 1, len(target_lines)):
        if target_lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(target_lines)

    return target_lines[:start] + block_lines + target_lines[end:]

# def update_lmkd_chimera(vince_path, target_path, log_callback):
#     """Update LMKD and Chimera properties in target file"""
#     target_name = "BENI" if "beni" in target_path.lower() else "FLUMEN" if "flumen" in target_path.lower() else "TARGET"
#     log_callback(f"[STEP 3] Updating LMKD and Chimera properties in {target_name}...")
    
#     with open(vince_path, "r", encoding="utf-8") as f:
#         vince_lines = f.readlines()
#     with open(target_path, "r", encoding="utf-8") as f:
#         target_lines = f.readlines()

#     lmkd_block = extract_block(vince_lines, "# LMKD property", ["#", ""])
#     if not lmkd_block:
#         lmkd_block = extract_block(vince_lines, "# DHA property", ["#", ""])
#     chimera_block = extract_block(vince_lines, "# Chimera property", ["#", ""]) 

#     updated_target = replace_block(target_lines, lmkd_block, "# LMKD property", ["#", ""])
#     updated_target = replace_block(updated_target, chimera_block, "# Chimera property", ["#", ""]) 

#     # Write updated file without creating a backup
#     with open(target_path, "w", encoding="utf-8") as f:
#         f.writelines(updated_target)
#     log_callback(f"[OK] Updated {target_name} file.")

def update_lmkd_chimera(vince_path, target_path, log_callback):
    """Update LMKD and Chimera properties in target file - COMPLETELY REWRITTEN"""
    target_name = "BENI" if "beni" in target_path.lower() else "FLUMEN" if "flumen" in target_path.lower() else "TARGET"
    log_callback(f"[STEP 3] Updating LMKD and Chimera properties in {target_name}...")
    
    # Read files
    with open(vince_path, "r", encoding="utf-8") as f:
        vince_lines = f.readlines()
    with open(target_path, "r", encoding="utf-8") as f:
        target_lines = f.readlines()

    # Extract content from VINCE (not headers) - case-insensitive
    lmkd_content = []
    chimera_content = []
    
    # Try LMKD first, then DHA
    lmkd_content = extract_block_content(vince_lines, "# LMKD property")
    if not lmkd_content:
        lmkd_content = extract_block_content(vince_lines, "# DHA property")
    
    # Extract Chimera content
    chimera_content = extract_block_content(vince_lines, "# Chimera property")
    
    # Check what exists in target - case-insensitive
    has_lmkd = any(line.strip().lower() == "# lmkd property" for line in target_lines)
    has_dha = any(line.strip().lower() == "# dha property" for line in target_lines)
    has_chimera = any(line.strip().lower() == "# chimera property" for line in target_lines)
    
    updated_target = target_lines[:]
    
    # Update LMKD/DHA block if exists in target and has content from VINCE
    if lmkd_content:
        if has_lmkd:
            updated_target = replace_block_content(updated_target, lmkd_content, "# LMKD property")
            log_callback(f"[OK] Updated LMKD property block in {target_name}")
        elif has_dha:
            updated_target = replace_block_content(updated_target, lmkd_content, "# DHA property")
            log_callback(f"[OK] Updated DHA property block in {target_name}")
        else:
            # Add LMKD block if target doesn't have it
            lmkd_header = "# LMKD property" if any("# LMKD property" in line for line in vince_lines) else "# DHA property"
            updated_target = replace_block_content(updated_target, lmkd_content, lmkd_header)
            log_callback(f"[OK] Added LMKD property block to {target_name}")
    else:
        log_callback(f"[INFO] No LMKD content found in VINCE, skipping LMKD update")
    
    # Update Chimera block if exists in target and has content from VINCE
    if chimera_content:
        if has_chimera:
            updated_target = replace_block_content(updated_target, chimera_content, "# Chimera property")
            log_callback(f"[OK] Updated Chimera property block in {target_name}")
        else:
            # Add Chimera block if target doesn't have it
            updated_target = replace_block_content(updated_target, chimera_content, "# Chimera property")
            log_callback(f"[OK] Added Chimera property block to {target_name}")
    else:
        log_callback(f"[INFO] No Chimera content found in VINCE, skipping Chimera update")
    
    # Write updated file
    with open(target_path, "w", encoding="utf-8") as f:
        f.writelines(updated_target)
    
    log_callback(f"[OK] Updated {target_name} file successfully.")

def create_backup(file_path):
    """Create backup of file with timestamp"""
    backup_path = file_path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copyfile(file_path, backup_path)
    return backup_path

# ============================================================================
# CONDITIONAL-AWARE PROPERTY EXTRACTION (v2)
# ============================================================================

def _parse_prop_line(line):
    """Parse a single property line, returning (key, value) or None."""
    stripped = line.strip().rstrip(' \\')
    if not stripped or stripped.startswith('#'):
        return None
    # Skip PRODUCT_PROPERTY_OVERRIDES lines and makefile keywords
    if 'PRODUCT_PROPERTY_OVERRIDES' in stripped:
        return None
    if stripped in ('ifneq', 'ifdef', 'ifndef', 'else', 'endif'):
        return None
    if stripped.startswith(('ifneq', 'ifdef', 'ifndef', 'else', 'endif')):
        return None
    if '=' not in stripped:
        return None
    key, value = stripped.split('=', 1)
    key = key.strip()
    value = value.strip()
    if '#' in value:
        value = value.split('#')[0].strip()
    # Remove trailing backslash from value if any
    value = value.rstrip(' \\')
    if not key:
        return None
    return key, value


def _extract_block_lines(all_lines, start_header):
    """
    Find ALL occurrences of start_header in all_lines and return the combined
    set of lines up until the next section header (comment line that is not
    a continuation) or EOF. Multiple LMKD blocks (e.g. one flat then one
    conditional with the same header) are merged into a single list.
    Returns list of lines STARTING from the header line.
    """
    result = []
    i = 0
    in_block = False
    block_end_patterns = None

    while i < len(all_lines):
        stripped = all_lines[i].strip()
        if stripped.lower() == start_header.lower():
            # Found a header – start/continue capturing
            if not in_block:
                # First occurrence – record header once
                result.append(all_lines[i])
                in_block = True
            else:
                # Subsequent occurrence of same header – don't duplicate header
                pass
            i += 1
            continue

        if in_block:
            # End of block when we hit a different section header
            if stripped.startswith('#') and stripped.lower() != start_header.lower():
                in_block = False
                # Don't advance i – the caller may need to detect the boundary
                break
            result.append(all_lines[i])
        i += 1

    return result


def enforce_structure_from_raw(file_path, properties_dict):
    """
    Completely replace the LMKD and Chimera blocks in file_path with the _raw_lines
    from properties_dict (which originally came from the source reference file).
    Then writes back to file_path.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for category, header in [("LMKD", "# LMKD property"), ("Chimera", "# Chimera property")]:
            cat_data = properties_dict.get(category)
            if not cat_data:
                continue
            
            raw_content = cat_data.get('_raw_lines', '')
            if not raw_content:
                continue
                
            # Convert raw string to list of lines if it's not already
            if isinstance(raw_content, str):
                raw_lines = raw_content.splitlines(keepends=True)
            else:
                raw_lines = raw_content
                
            # Deletion phase: Find all lines belonging to the old block and remove them
            i = 0
            in_block = False
            new_lines = []
            
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped.lower() == header.lower() or (category == "LMKD" and stripped.lower() == "# dha property"):
                    in_block = True
                    i += 1
                    continue
                    
                if in_block:
                    if stripped.startswith('#') and stripped.lower() != header.lower() and (category != "LMKD" or stripped.lower() != "# dha property"):
                        in_block = False
                        new_lines.append(lines[i])
                else:
                    new_lines.append(lines[i])
                i += 1
                
            lines = new_lines
            
            # Insertion phase: Find where to insert the new blocks
            insert_idx = len(lines)
            if category == "LMKD":
                # Find best place for LMKD (before Chimera)
                for i, line in enumerate(lines):
                    if line.strip().lower() == "# chimera property":
                        insert_idx = max(0, i - 1)  # Put before chimera
                        break
            elif category == "Chimera":
                # Find best place for Chimera (after LMKD ends)
                last_lmkd = -1
                for i, line in enumerate(lines):
                    if line.strip().startswith('ro.slmk.'):
                        last_lmkd = i
                if last_lmkd != -1:
                    insert_idx = last_lmkd + 1
                    
            # Inject new raw block with a spacing line before and after to ensure clean separation
            lines = lines[:insert_idx] + ["\n"] + raw_lines + ["\n"] + lines[insert_idx:]

        with open(file_path, "w", encoding="utf-8") as f:
            # We don't want triple newlines, so we do a quick cleanup of multiple empty lines
            cleaned_lines = []
            empty_count = 0
            for line in lines:
                if not line.strip():
                    empty_count += 1
                    if empty_count > 2:  # allow max 2 empty lines
                        continue
                else:
                    empty_count = 0
                cleaned_lines.append(line)
            f.writelines(cleaned_lines)
            
        return True, None
    except Exception as e:
        return False, str(e)


def _parse_block_with_conditionals(block_lines):
    """
    Parse a block of lines (from after header to end of section) that may
    contain ifneq/ifdef/ifndef … else … endif constructs.

    Returns a dict:
    {
        "_flat": {prop_key: prop_value, ...},          # properties outside any if/else
        "_conditional": [
            {
                "condition": "ifneq ($(filter usa%, ...), )",
                "if_props":   {prop_key: prop_value},  # inside ifneq block
                "else_props": {prop_key: prop_value}   # inside else block (None if absent)
            },
            ...
        ]
    }
    """
    flat = {}
    conditionals = []

    i = 0
    lines = block_lines  # lines already exclude the header
    # Skip first line if it IS the header
    if lines and lines[0].strip().lower().startswith('# '):
        i = 1

    while i < len(lines):
        stripped = lines[i].strip()

        # ---- Start of a conditional block ----
        if stripped.startswith(('ifneq', 'ifdef', 'ifndef')):
            condition = stripped
            if_props = {}
            else_props = None
            i += 1
            state = 'if'  # 'if' or 'else'

            while i < len(lines):
                cur = lines[i].strip()

                if cur == 'else':
                    state = 'else'
                    else_props = {}
                    i += 1
                    continue

                if cur == 'endif':
                    i += 1
                    break

                # Nested ifneq inside – skip (shouldn't normally appear but be safe)
                if cur.startswith(('ifneq', 'ifdef', 'ifndef')):
                    # Simple skip until matching endif
                    depth = 1
                    i += 1
                    while i < len(lines) and depth > 0:
                        c = lines[i].strip()
                        if c.startswith(('ifneq', 'ifdef', 'ifndef')):
                            depth += 1
                        elif c == 'endif':
                            depth -= 1
                        i += 1
                    continue

                parsed = _parse_prop_line(lines[i])
                if parsed:
                    k, v = parsed
                    if state == 'if':
                        if_props[k] = v
                    else:
                        else_props[k] = v
                i += 1

            conditionals.append({
                'condition': condition,
                'if_props': if_props,
                'else_props': else_props
            })
            continue

        # ---- Flat property line ----
        parsed = _parse_prop_line(lines[i])
        if parsed:
            k, v = parsed
            flat[k] = v

        i += 1

    return {'_flat': flat, '_conditional': conditionals}


def extract_properties_from_file(file_path):
    """
    Extract LMKD and Chimera properties from file.

    Returns a dict with the NEW conditional-aware structure:
    {
        "LMKD": {
            "_flat": {prop_key: value, ...},
            "_conditional": [
                {"condition": "ifneq ...", "if_props": {...}, "else_props": {...}},
                ...
            ]
        },
        "Chimera": { ... same structure ... }
    }
    Returns None if neither category has any properties.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        properties = {}

        # ---- LMKD / DHA ----
        lmkd_block = _extract_block_lines(lines, "# LMKD property")
        if not lmkd_block:
            lmkd_block = _extract_block_lines(lines, "# DHA property")
        if lmkd_block:
            parsed = _parse_block_with_conditionals(lmkd_block)
            parsed['_raw_lines'] = "".join(lmkd_block)
            if parsed['_flat'] or parsed['_conditional']:
                properties["LMKD"] = parsed

        # ---- Chimera ----
        chimera_block = _extract_block_lines(lines, "# Chimera property")
        if chimera_block:
            parsed = _parse_block_with_conditionals(chimera_block)
            parsed['_raw_lines'] = "".join(chimera_block)
            if parsed['_flat'] or parsed['_conditional']:
                properties["Chimera"] = parsed

        if not properties:
            return None

        # Ensure both keys exist (with empty structure) for downstream consumers
        for cat in ('LMKD', 'Chimera'):
            if cat not in properties:
                properties[cat] = {'_flat': {}, '_conditional': [], '_raw_lines': ''}

        return properties

    except Exception:
        return None


def get_flat_properties_for_display(conditional_properties):
    """
    Convert the new conditional-aware structure into a simple flat dict.
    Used for quick comparisons (BENI vs FLUMEN vs REL).
    For conditional props, both if and else values are included –
    if they conflict, the else value takes precedence (conservative choice).
    """
    flat = {}
    if not conditional_properties:
        return flat

    for cat, data in conditional_properties.items():
        if cat.startswith('_'):
            continue
        if not isinstance(data, dict):
            continue
        cat_flat = {}
        # Flat properties
        cat_flat.update(data.get('_flat', {}))
        # Conditional properties – if value first, else overrides
        for block in data.get('_conditional', []):
            cat_flat.update(block.get('if_props', {}))
            if block.get('else_props'):
                cat_flat.update(block['else_props'])
        flat[cat] = cat_flat
    return flat


def validate_conditional_structure_match(props_a, props_b):
    """
    Check whether two conditional property structures are compatible
    (same number of conditional blocks per category, same condition strings).
    Returns (is_match, list_of_diffs).
    """
    diffs = []
    for cat in ('LMKD', 'Chimera'):
        blocks_a = props_a.get(cat, {}).get('_conditional', [])
        blocks_b = props_b.get(cat, {}).get('_conditional', [])
        if len(blocks_a) != len(blocks_b):
            diffs.append(f"{cat}: different number of conditional blocks ({len(blocks_a)} vs {len(blocks_b)})")
            continue
        for i, (ba, bb) in enumerate(zip(blocks_a, blocks_b)):
            if ba['condition'] != bb['condition']:
                diffs.append(f"{cat} block {i}: condition mismatch ('{ba['condition']}' vs '{bb['condition']}')")
    return len(diffs) == 0, diffs


def parse_properties_block(block_lines):
    """
    Parse property block and extract key-value pairs (FLAT, legacy).
    NOTE: This ignores if/else structure – use _parse_block_with_conditionals for
    the new conditional-aware extraction.
    """
    properties = {}

    for line in block_lines:
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue
        # Skip makefile keywords
        if line.startswith(('ifneq', 'ifdef', 'ifndef', 'else', 'endif')):
            continue
        # Skip PRODUCT_PROPERTY_OVERRIDES lines
        if "PRODUCT_PROPERTY_OVERRIDES" in line:
            continue
        # Look for property=value pattern
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().rstrip(' \\')
            if "#" in value:
                value = value.split("#")[0].strip()
            if key:
                properties[key] = value

    return properties

# ============================================================================
# ENHANCED PROPERTY BLOCK UPDATE FUNCTIONS WITH DELETE SUPPORT
# ============================================================================

def find_block_boundaries(lines, start_header, next_header_list):
    """Find start and end indices of a property block"""
    start = end = None
    for idx, line in enumerate(lines):
        if line.strip() == start_header:
            start = idx
            break
    
    if start is None:
        return None, None
    
    for idx in range(start + 1, len(lines)):
        if lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(lines)
    
    return start, end

def analyze_product_override_blocks(original_lines):
    """Analyze and identify PRODUCT_PROPERTY_OVERRIDES blocks in the section while preserving conditional structure"""
    override_blocks = []
    i = 1  # Skip header line
    
    # Track conditional structure to avoid cross-block property merging
    conditional_stack = []  # Track if/else/endif nesting
    current_conditional_start = None
    
    while i < len(original_lines):
        line = original_lines[i]
        stripped_line = line.strip()
        
        # Track conditional structure
        if stripped_line.startswith("ifneq") or stripped_line.startswith("ifdef") or stripped_line.startswith("ifndef"):
            conditional_stack.append(('if', i))
            current_conditional_start = i
        elif stripped_line == "else":
            if conditional_stack:
                conditional_stack[-1] = ('else', i)
        elif stripped_line == "endif":
            if conditional_stack:
                conditional_stack.pop()
                if not conditional_stack:
                    current_conditional_start = None
        
        if "PRODUCT_PROPERTY_OVERRIDES" in stripped_line and "+=" in stripped_line:
            # Start of new override block
            block_start = i
            block_properties = []
            block_lines = [i]  # Store line indices
            block_conditional_context = list(conditional_stack)  # Capture current conditional context
            i += 1
            
            # Collect all properties in this block
            while i < len(original_lines):
                prop_line = original_lines[i]
                prop_stripped = prop_line.strip()
                
                # Check if we're entering/exiting a different conditional context
                if prop_stripped.startswith("ifneq") or prop_stripped.startswith("ifdef") or prop_stripped.startswith("ifndef"):
                    # New conditional block started, end current property collection
                    break
                elif prop_stripped == "else" or prop_stripped == "endif":
                    # Conditional structure changed, end current property collection
                    break
                elif not prop_stripped or prop_stripped.startswith("#"):
                    block_lines.append(i)
                    i += 1
                    continue
                elif "=" in prop_stripped:
                    # Extract property name
                    if prop_stripped.endswith("\\"):
                        prop_content = prop_stripped[:-1].strip()
                    else:
                        prop_content = prop_stripped
                    
                    if "=" in prop_content:
                        key = prop_content.split("=", 1)[0].strip()
                        block_properties.append(key)
                    
                    block_lines.append(i)
                    
                    # If line doesn't end with backslash, this is end of block
                    if not prop_stripped.endswith("\\"):
                        i += 1
                        break
                    i += 1
                else:
                    # Non-property line, might be end of block
                    break
            
            override_blocks.append({
                'start': block_start,
                'properties': block_properties,
                'lines': block_lines,
                'conditional_context': block_conditional_context  # Preserve conditional context
            })
        else:
            i += 1
    
    return override_blocks

def get_default_indentation(original_lines):
    """Get default indentation from existing property lines"""
    default_indent = "    "  # Default 4 spaces
    for line in original_lines:
        if "=" in line and not line.strip().startswith("#") and "PRODUCT_PROPERTY_OVERRIDES" not in line:
            default_indent = line[:len(line) - len(line.lstrip())]
            break
    return default_indent

def update_product_override_block_with_deletions(original_lines, override_blocks, remaining_properties):
    """Update PRODUCT_PROPERTY_OVERRIDES blocks with new properties and handle deletions while preserving conditional structure"""
    new_block = [original_lines[0]]  # Keep header line
    processed_lines = set()
    
    # Create a mapping of line numbers to original lines for reference
    line_mapping = {}
    for i, line in enumerate(original_lines):
        line_mapping[i] = line
    
    # Track which properties have been assigned to specific blocks
    assigned_properties = set()
    
    for line_idx in range(1, len(original_lines)):  # Skip header
        if line_idx in processed_lines:
            continue
            
        line = original_lines[line_idx]
        stripped_line = line.strip()
        
        # Keep all lines as-is initially, we'll only modify PRODUCT_PROPERTY_OVERRIDES blocks
        # This preserves conditional structure completely
        new_block.append(line)
        processed_lines.add(line_idx)
    
    # Now go through each PRODUCT_PROPERTY_OVERRIDES block and update only the properties within it
    for block in override_blocks:
        block_start = block['start']
        block_lines = block['lines']
        block_properties = block['properties']
        
        # Only process if this block has properties that need to be updated
        properties_to_update = {}
        for prop_key in block_properties:
            if prop_key in remaining_properties:
                properties_to_update[prop_key] = remaining_properties[prop_key]
                assigned_properties.add(prop_key)
        
        if properties_to_update:
            # Update properties within this specific block
            # We need to find and replace property lines within this block range
            updated_block_lines = []
            i = 0
            while i < len(block_lines):
                line_idx = block_lines[i]
                if line_idx >= len(original_lines):
                    i += 1
                    continue
                    
                line = original_lines[line_idx]
                stripped_line = line.strip()
                
                # Check if this is a property line that needs updating
                if "=" in stripped_line and not stripped_line.startswith("#") and "PRODUCT_PROPERTY_OVERRIDES" not in stripped_line:
                    # Extract property key
                    prop_line_content = stripped_line[:-1].strip() if stripped_line.endswith("\\") else stripped_line
                    if "=" in prop_line_content:
                        prop_key = prop_line_content.split("=", 1)[0].strip()
                        
                        # If this property needs to be updated
                        if prop_key in properties_to_update:
                            # Get indentation
                            indent = line[:len(line) - len(line.lstrip())]
                            
                            # Create updated line
                            new_value = properties_to_update[prop_key]
                            # Check if there's a trailing comment
                            original_content = prop_line_content.split("=", 1)[1].strip()
                            if "#" in original_content:
                                comment_part = original_content.split("#", 1)[1]
                                new_line = f"{indent}{prop_key}={new_value} #{comment_part}\n"
                            else:
                                # Check if this should have a backslash (not the last property in block)
                                has_backslash = stripped_line.endswith("\\")
                                if has_backslash:
                                    new_line = f"{indent}{prop_key}={new_value} \\\n"
                                else:
                                    new_line = f"{indent}{prop_key}={new_value}\n"
                            
                            updated_block_lines.append((line_idx, new_line))
                            # Remove from remaining properties since it's been assigned
                            if prop_key in remaining_properties:
                                del remaining_properties[prop_key]
                        else:
                            # Keep original line
                            updated_block_lines.append((line_idx, line))
                    else:
                        # Keep original line
                        updated_block_lines.append((line_idx, line))
                else:
                    # Keep original line (comments, empty lines, PRODUCT_PROPERTY_OVERRIDES line, etc.)
                    updated_block_lines.append((line_idx, line))
                
                i += 1
            
            # Apply the updates to the new_block
            for line_idx, updated_line in updated_block_lines:
                if line_idx < len(new_block):
                    new_block[line_idx] = updated_line
    
    return new_block, remaining_properties

def add_remaining_properties(new_block, remaining_properties, original_lines):
    """Add any remaining properties that weren't added to PRODUCT_PROPERTY_OVERRIDES blocks"""
    if remaining_properties:
        default_indent = get_default_indentation(original_lines)
        
        # Add new properties as regular properties
        new_props_lines = []
        for key, value in remaining_properties.items():
            new_props_lines.append(f"{default_indent}{key}={value}\n")
        
        # Insert after last property or at end
        new_block.extend(new_props_lines)
    
    return new_block

def update_properties_block_preserve_format_with_deletions(lines, new_properties, start_header, next_header_list):
    """Update properties block while preserving original format and handling deletions"""
    # Find block boundaries
    start, end = find_block_boundaries(lines, start_header, next_header_list)
    if start is None:
        return lines  # Block not found
    
    # Extract original block to preserve formatting
    original_lines = lines[start:end]
    remaining_properties = new_properties.copy()
    
    # Analyze PRODUCT_PROPERTY_OVERRIDES blocks
    override_blocks = analyze_product_override_blocks(original_lines)
    
    # Update the block with deletion support
    new_block, remaining_properties = update_product_override_block_with_deletions(
        original_lines, override_blocks, remaining_properties
    )
    
    # Add any remaining properties
    new_block = add_remaining_properties(new_block, remaining_properties, original_lines)
    
    # Replace the block
    return lines[:start] + new_block + lines[end:]

# ============================================================================
# CONDITIONAL-AWARE UPDATE FUNCTIONS (v2)
# ============================================================================

def _is_new_conditional_structure(properties_dict):
    """
    Detect if properties_dict uses the new conditional-aware structure:
    { "LMKD": {"_flat": {...}, "_conditional": [...]}, ... }
    """
    for cat in ('LMKD', 'Chimera'):
        val = properties_dict.get(cat)
        if isinstance(val, dict) and ('_flat' in val or '_conditional' in val):
            return True
    return False


def update_properties_in_file(file_path, properties_dict):
    """
    Update properties in file with new values while preserving format.
    Handles both the new conditional-aware structure (v2) and the legacy
    flat/context-aware structures for backward compatibility.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # ---- NEW: conditional-aware structure from extract_properties_from_file v2 ----
        if _is_new_conditional_structure(properties_dict):
            return _update_v2_conditional_structure(file_path, properties_dict, lines)

        # ---- LEGACY: old conditional-aware update (values_by_context dict) ----
        if _is_conditional_aware_update(properties_dict):
            return _update_properties_conditional_aware(file_path, properties_dict, lines)

        # ---- LEGACY: flat property update ----
        if properties_dict.get("LMKD") and len(properties_dict["LMKD"]) > 0:
            lines = update_properties_block_preserve_format_with_deletions(
                lines, properties_dict["LMKD"],
                "# LMKD property", ["# Chimera property", "# DHA property"]
            )
            if not any("# LMKD property" in line for line in lines):
                lines = update_properties_block_preserve_format_with_deletions(
                    lines, properties_dict["LMKD"],
                    "# DHA property", ["# Chimera property"]
                )

        if properties_dict.get("Chimera") and len(properties_dict["Chimera"]) > 0:
            lines = update_properties_block_preserve_format_with_deletions(
                lines, properties_dict["Chimera"],
                "# Chimera property", ["# Nandswap", "#", ""]
            )

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True, None

    except Exception as e:
        return False, str(e)


def _update_v2_conditional_structure(file_path, properties_dict, lines):
    """
    Apply changes described by the v2 conditional-aware structure.

    For each category (LMKD, Chimera):
    - _flat props: update exactly as before (only matching flat lines in file)
    - _conditional blocks: for each block, match by condition string and update
      only the properties that actually changed, inside the correct if/else context.

    Key principle: if a property's value has NOT changed (original == current),
    we do NOT touch it in the file \u2014 preserving the other context untouched.
    """
    try:
        for category in ('LMKD', 'Chimera'):
            cat_data = properties_dict.get(category)
            if not cat_data or not isinstance(cat_data, dict):
                continue

            flat_props = cat_data.get('_flat', {})
            conditional_blocks = cat_data.get('_conditional', [])

            # Determine section header and next-headers for this category
            if category == 'LMKD':
                section_header = '# LMKD property'
                alt_header = '# DHA property'
                next_headers = ['# Chimera property', '# DHA property', '# Nandswap']
            else:
                section_header = '# Chimera property'
                alt_header = None
                next_headers = ['# Nandswap', '#', '']

            # ---- Update flat properties ----
            if flat_props:
                lines = _update_flat_props_in_section(
                    lines, flat_props, section_header, next_headers
                )
                if alt_header and not any(section_header in ln for ln in lines):
                    lines = _update_flat_props_in_section(
                        lines, flat_props, alt_header, next_headers
                    )

            # ---- Update conditional blocks ----
            for cond_block in conditional_blocks:
                condition = cond_block.get('condition', '')
                if_props = cond_block.get('if_props', {})
                else_props = cond_block.get('else_props')

                if condition:
                    lines = _update_conditional_block_in_file(
                        lines, condition, if_props, else_props
                    )

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True, None

    except Exception as e:
        return False, str(e)


def _update_flat_props_in_section(lines, flat_props, section_header, next_headers):
    """
    Update flat (non-conditional) properties within a named section.
    Only updates lines that are NOT inside a ifneq/else/ifdef block.
    """
    # Find section boundaries
    start, end = find_block_boundaries(lines, section_header, next_headers)
    if start is None:
        return lines

    section = lines[start:end]

    # Walk through the section; skip anything inside a conditional block
    remaining = flat_props.copy()
    in_conditional = 0  # nesting depth

    for i in range(1, len(section)):  # skip header line
        stripped = section[i].strip()

        # Track conditional nesting
        if stripped.startswith(('ifneq', 'ifdef', 'ifndef')):
            in_conditional += 1
            continue
        if stripped == 'else' and in_conditional > 0:
            continue
        if stripped == 'endif':
            if in_conditional > 0:
                in_conditional -= 1
            continue

        # Only update flat lines (not inside any conditional)
        if in_conditional > 0:
            continue

        parsed = _parse_prop_line(section[i])
        if parsed:
            k, v = parsed
            if k in remaining:
                new_v = remaining[k]
                indent = section[i][:len(section[i]) - len(section[i].lstrip())]
                has_bs = section[i].rstrip('\n\r').endswith('\\')
                if has_bs:
                    section[i] = f"{indent}{k}={new_v} \\\n"
                else:
                    section[i] = f"{indent}{k}={new_v}\n"
                del remaining[k]

    return lines[:start] + section + lines[end:]


def _update_conditional_block_in_file(lines, condition, if_props, else_props):
    """
    Find the conditional block with the given condition string in lines and
    update *only* the properties provided, inside *only* the correct sub-block
    (ifneq block vs else block).

    Properties not listed in if_props / else_props are left completely untouched.
    """
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # Found the matching condition line
        if stripped == condition:
            # Now parse forward: update if-block then else-block
            i += 1
            state = 'if'  # current state: 'if' or 'else'
            depth = 1     # nesting depth for the outer ifneq

            while i < len(lines) and depth > 0:
                cur = lines[i].strip()

                if cur.startswith(('ifneq', 'ifdef', 'ifndef')):
                    depth += 1
                    i += 1
                    continue

                if cur == 'else' and depth == 1:
                    state = 'else'
                    i += 1
                    continue

                if cur == 'endif':
                    depth -= 1
                    i += 1
                    continue

                # Property line \u2013 check if we should update it
                parsed = _parse_prop_line(lines[i])
                if parsed:
                    k, v = parsed
                    if state == 'if' and if_props and k in if_props:
                        new_v = if_props[k]
                        indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
                        has_bs = lines[i].rstrip('\n\r').endswith('\\')
                        if has_bs:
                            lines[i] = f"{indent}{k}={new_v} \\\n"
                        else:
                            lines[i] = f"{indent}{k}={new_v}\n"
                    elif state == 'else' and else_props and k in else_props:
                        new_v = else_props[k]
                        indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
                        has_bs = lines[i].rstrip('\n\r').endswith('\\')
                        if has_bs:
                            lines[i] = f"{indent}{k}={new_v} \\\n"
                        else:
                            lines[i] = f"{indent}{k}={new_v}\n"

                i += 1

            # Found and processed the matching condition \u2013 done
            return lines

        i += 1

    return lines


def _is_conditional_aware_update(properties_dict):
    """Check if this is a legacy conditional-aware update (has values_by_context info)"""
    for category, props in properties_dict.items():
        if isinstance(props, dict):
            for prop_name, prop_value in props.items():
                if isinstance(prop_value, dict) and 'values_by_context' in prop_value:
                    return True
                if isinstance(prop_value, dict) and any(key.startswith('[') for key in prop_value.keys()):
                    return True
    return False


def _update_properties_conditional_aware(file_path, properties_dict, lines):
    """Update properties with legacy conditional context awareness (values_by_context format)"""
    try:
        for category, props in properties_dict.items():
            if isinstance(props, dict) and category in ["LMKD", "Chimera"]:
                conditional_props = {}
                flat_props = {}

                for prop_name, prop_value in props.items():
                    if isinstance(prop_value, dict) and 'values_by_context' in prop_value:
                        conditional_props[prop_name] = prop_value
                    else:
                        flat_props[prop_name] = prop_value

                if conditional_props:
                    lines = _update_conditional_properties_in_section(lines, category, conditional_props)

                if flat_props:
                    if category == "LMKD":
                        lines = update_properties_block_preserve_format_with_deletions(
                            lines, flat_props, "# LMKD property", ["# Chimera property", "# DHA property"]
                        )
                        if not any("# LMKD property" in line for line in lines):
                            lines = update_properties_block_preserve_format_with_deletions(
                                lines, flat_props, "# DHA property", ["# Chimera property"]
                            )
                    elif category == "Chimera":
                        lines = update_properties_block_preserve_format_with_deletions(
                            lines, flat_props, "# Chimera property", ["# Nandswap", "#", ""]
                        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True, None

    except Exception as e:
        return False, str(e)


def _update_conditional_properties_in_section(lines, category, conditional_props):
    """Update conditional properties in a specific section with context preservation"""
    section_header = f"# {category} property"
    next_headers = ["# Chimera property", "# DHA property", "# Nandswap", "#", ""] if category == "LMKD" else ["# Nandswap", "#", ""]

    start, end = find_block_boundaries(lines, section_header, next_headers)
    if start is None:
        return lines

    section_lines = lines[start:end]

    for prop_name, prop_data in conditional_props.items():
        context_values = prop_data.get('values_by_context', {})
        selected_contexts = prop_data.get('selected_contexts', list(context_values.keys()))
        section_lines = _update_property_in_conditional_contexts(
            section_lines, prop_name, context_values, selected_contexts
        )

    return lines[:start] + section_lines + lines[end:]


def _update_property_in_conditional_contexts(section_lines, prop_name, context_values, selected_contexts):
    """Update property values in the selected conditional contexts"""
    i = 1  # Skip header
    while i < len(section_lines):
        line = section_lines[i].strip()

        if line.startswith('ifneq') or line.startswith('ifdef') or line.startswith('ifndef'):
            condition_start = i
            condition_text = line
            context_key = f"[{condition_text}]"
            if context_key in selected_contexts and context_key in context_values:
                new_value = context_values[context_key]
                i = _update_properties_in_conditional_block(section_lines, condition_start, prop_name, new_value)
            else:
                i = _skip_conditional_block(section_lines, condition_start)
        else:
            i += 1

    # Handle else blocks
    i = 1
    while i < len(section_lines):
        line = section_lines[i].strip()
        if line == 'else':
            else_key = "[else]"
            if else_key in selected_contexts and else_key in context_values:
                new_value = context_values[else_key]
                i = _update_properties_in_else_block(section_lines, i, prop_name, new_value)
            else:
                i += 1
        else:
            i += 1

    return section_lines


def _update_properties_in_conditional_block(lines, start_idx, prop_name, new_value):
    """Update property in a conditional (ifneq) block"""
    i = start_idx + 1
    while i < len(lines) and not lines[i].strip().startswith(('else', 'endif')):
        line = lines[i]
        stripped_line = line.strip()

        if '=' in stripped_line and not stripped_line.startswith('#'):
            clean_line = stripped_line.rstrip(' \\')
            if '=' in clean_line:
                key = clean_line.split('=', 1)[0].strip()
                if key == prop_name:
                    indent = line[:len(line) - len(line.lstrip())]
                    has_backslash = stripped_line.endswith('\\')
                    if has_backslash:
                        lines[i] = f"{indent}{prop_name}={new_value} \\\n"
                    else:
                        lines[i] = f"{indent}{prop_name}={new_value}\n"
                    return i + 1

        if not stripped_line or stripped_line.startswith(('endif', 'ifneq', 'ifdef', 'ifndef')):
            break
        i += 1

    return i + 1


def _update_properties_in_else_block(lines, start_idx, prop_name, new_value):
    """Update property in an else block"""
    i = start_idx + 1
    while i < len(lines) and not lines[i].strip().startswith('endif'):
        line = lines[i]
        stripped_line = line.strip()

        if '=' in stripped_line and not stripped_line.startswith('#'):
            clean_line = stripped_line.rstrip(' \\')
            if '=' in clean_line:
                key = clean_line.split('=', 1)[0].strip()
                if key == prop_name:
                    indent = line[:len(line) - len(line.lstrip())]
                    has_backslash = stripped_line.endswith('\\')
                    if has_backslash:
                        lines[i] = f"{indent}{prop_name}={new_value} \\\n"
                    else:
                        lines[i] = f"{indent}{prop_name}={new_value}\n"
                    return i + 1

        if not stripped_line or stripped_line.startswith(('ifneq', 'ifdef', 'ifndef')):
            break
        i += 1

    return i + 1


def _skip_conditional_block(lines, start_idx):
    """Skip past a conditional block"""
    i = start_idx + 1
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('endif'):
            return i + 1
        elif line.startswith(('ifneq', 'ifdef', 'ifndef')):
            i = _skip_conditional_block(lines, i)
        else:
            i += 1
    return i

def compare_properties_between_files(file1_path, file2_path):
    """Compare properties between two files and return differences"""
    try:
        props1_raw = extract_properties_from_file(file1_path)
        props2_raw = extract_properties_from_file(file2_path)
        
        if not props1_raw or not props2_raw:
            return None
            
        props1 = get_flat_properties_for_display(props1_raw)
        props2 = get_flat_properties_for_display(props2_raw)
        
        differences = []
        
        # Compare LMKD properties
        lmkd1 = props1.get("LMKD", {})
        lmkd2 = props2.get("LMKD", {})
        lmkd_diffs = compare_property_dict(lmkd1, lmkd2, "LMKD")
        differences.extend(lmkd_diffs)
        
        # Compare Chimera properties
        chimera1 = props1.get("Chimera", {})
        chimera2 = props2.get("Chimera", {})
        chimera_diffs = compare_property_dict(chimera1, chimera2, "Chimera")
        differences.extend(chimera_diffs)
        
        return differences
        
    except Exception:
        return None

def compare_property_dict(dict1, dict2, category):
    """Compare two property dictionaries"""
    differences = []
    
    all_keys = set(dict1.keys()) | set(dict2.keys())
    
    for key in all_keys:
        val1 = dict1.get(key, "<missing>")
        val2 = dict2.get(key, "<missing>")
        
        if val1 != val2:
            differences.append(f"{category}.{key}: File1='{val1}' vs File2='{val2}'")
    
    return differences

# ============================================================================
# DEPRECATED - LEGACY FUNCTIONS (Keep for backward compatibility)
# ============================================================================



def update_properties_block_preserve_format(lines, new_properties, start_header, next_header_list):
    """Update properties block while preserving original format and comments"""
    return update_properties_block_preserve_format_with_deletions(lines, new_properties, start_header, next_header_list)

def update_properties_block(lines, new_properties, start_header, next_header_list):
    """Update properties block in file lines"""
    # Find block boundaries
    start = end = None
    for idx, line in enumerate(lines):
        if line.strip() == start_header:
            start = idx
            break
    
    if start is None:
        return lines  # Block not found
    
    for idx in range(start + 1, len(lines)):
        if lines[idx].strip() in next_header_list:
            end = idx
            break
    if end is None:
        end = len(lines)
    
    # Build new block
    new_block = [lines[start]]  # Keep header line
    
    # Add properties
    for key, value in new_properties.items():
        new_block.append(f"{key}={value}\n")
    
    # Add empty line before next section if needed
    if end < len(lines) and lines[end].strip():
        new_block.append("\n")
    
    # Replace the block
    return lines[:start] + new_block + lines[end:]

def compare_properties_between_files(file1_path, file2_path):
    """Compare properties between two files and return differences"""
    try:
        props1 = extract_properties_from_file(file1_path)
        props2 = extract_properties_from_file(file2_path)
        
        if not props1 or not props2:
            return None
        
        differences = []
        
        # Compare LMKD properties
        lmkd1 = props1.get("LMKD", {})
        lmkd2 = props2.get("LMKD", {})
        lmkd_diffs = compare_property_dict(lmkd1, lmkd2, "LMKD")
        differences.extend(lmkd_diffs)
        
        # Compare Chimera properties
        chimera1 = props1.get("Chimera", {})
        chimera2 = props2.get("Chimera", {})
        chimera_diffs = compare_property_dict(chimera1, chimera2, "Chimera")
        differences.extend(chimera_diffs)
        
        return differences
        
    except Exception:
        return None

def compare_property_dict(dict1, dict2, category):
    """Compare two property dictionaries"""
    differences = []
    
    all_keys = set(dict1.keys()) | set(dict2.keys())
    
    for key in all_keys:
        val1 = dict1.get(key, "<missing>")
        val2 = dict2.get(key, "<missing>")
        
        if val1 != val2:
            differences.append(f"{category}.{key}: File1='{val1}' vs File2='{val2}'")
    
    return differences

# ============================================================================
# CONDITIONAL STRUCTURE ANALYSIS FUNCTIONS (NEW)
# ============================================================================

def analyze_conditional_structure(file_content):
    """
    Analyze conditional structure in file content
    Extract conditional blocks and properties with context information
    """
    lines = file_content.split('\n') if isinstance(file_content, str) else file_content
    conditional_sections = {}
    
    # Parse từng section
    section_headers = ["# LMKD property", "# Chimera property", "# DHA property"]
    
    for section_header in section_headers:
        section_data = analyze_section_conditional_blocks(lines, section_header)
        if section_data:
            section_name = section_header.replace("# ", "").replace(" property", "")
            conditional_sections[section_name] = section_data
    
    return conditional_sections

def analyze_section_conditional_blocks(lines, section_header):
    """
    Analyze conditional blocks in a specific section
    """
    # Find section boundaries
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == section_header:
            start_idx = i
            break
    
    if start_idx is None:
        return None
    
    # Find end boundary
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        line_stripped = lines[i].strip()
        if not line_stripped or (line_stripped.startswith('#') and section_header not in line_stripped):
            if i > start_idx + 1:  # Skip empty lines right after header
                end_idx = i
                break
    
    # Analyze conditional blocks in section
    section_lines = lines[start_idx:end_idx]
    conditional_blocks = []
    
    i = 1  # Skip header line
    while i < len(section_lines):
        line = section_lines[i].strip()
        
        # Find conditional block start
        if line.startswith('ifneq') or line.startswith('ifdef') or line.startswith('ifndef'):
            condition_text = line
            condition_type = 'if'
            
            # Find properties in conditional block
            properties = []
            i += 1
            
            # Collect properties until else/endif
            while i < len(section_lines):
                prop_line = section_lines[i].strip()
                if prop_line.startswith('else') or prop_line.startswith('endif') or prop_line.startswith('ifneq'):
                    break
                
                if '=' in prop_line and 'PRODUCT_PROPERTY_OVERRIDES' not in prop_line and prop_line and not prop_line.startswith('#'):
                    # Parse property
                    clean_line = prop_line.rstrip(' \\')
                    if '=' in clean_line and not clean_line.startswith('PRODUCT_PROPERTY_OVERRIDES'):
                        key, value = clean_line.split('=', 1)
                        # Remove trailing comments
                        if '#' in value:
                            value = value.split('#')[0].strip()
                        properties.append({
                            'key': key.strip(),
                            'value': value.strip().rstrip(' \\'),
                            'line_number': start_idx + i
                        })
                i += 1
            
            # Handle else block if exists
            else_properties = []
            if i < len(section_lines) and section_lines[i].strip() == 'else':
                i += 1
                while i < len(section_lines):
                    prop_line = section_lines[i].strip()
                    if prop_line.startswith('endif') or prop_line.startswith('ifneq'):
                        break
                    
                    if '=' in prop_line and 'PRODUCT_PROPERTY_OVERRIDES' not in prop_line and prop_line and not prop_line.startswith('#'):
                        clean_line = prop_line.rstrip(' \\')
                        if '=' in clean_line and not clean_line.startswith('PRODUCT_PROPERTY_OVERRIDES'):
                            key, value = clean_line.split('=', 1)
                            # Remove trailing comments
                            if '#' in value:
                                value = value.split('#')[0].strip()
                            else_properties.append({
                                'key': key.strip(),
                                'value': value.strip().rstrip(' \\'),
                                'line_number': start_idx + i
                            })
                    i += 1
            
            conditional_blocks.append({
                'condition': condition_text,
                'type': condition_type,
                'properties': properties,
                'else_properties': else_properties if else_properties else None
            })
            
            # Skip endif
            if i < len(section_lines) and section_lines[i].strip() == 'endif':
                i += 1
        else:
            i += 1
    
    return {
        'header_line': start_idx,
        'blocks': conditional_blocks
    }

def test_conditional_parser():
    """
    Test function to validate conditional parser
    """
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
    
    result = analyze_conditional_structure(test_content)
    print("=== CONDITIONAL PARSER TEST RESULT ===")
    print(f"Sections found: {list(result.keys())}")
    
    for section, data in result.items():
        print(f"\n{section} Section:")
        if data['blocks']:
            for i, block in enumerate(data['blocks']):
                print(f"  Block {i+1}: {block['condition']}")
                print(f"    Properties: {len(block['properties'])}")
                for prop in block['properties']:
                    print(f"      {prop['key']} = {prop['value']}")
                if block['else_properties']:
                    print(f"    Else Properties: {len(block['else_properties'])}")
                    for prop in block['else_properties']:
                        print(f"      {prop['key']} = {prop['value']}")
        else:
            print("  No conditional blocks found")
    
    return result

# Test the parser when file is run directly
if __name__ == "__main__":
    test_conditional_parser()

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

def extract_properties_from_file(file_path):
    """Extract LMKD and Chimera properties from file and return as dictionary"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        properties = {"LMKD": {}, "Chimera": {}}
        
        # Extract LMKD properties
        lmkd_block = extract_block(lines, "# LMKD property", ["#", ""])
        if not lmkd_block:
            lmkd_block = extract_block(lines, "# DHA property", ["#", ""])
        
        if lmkd_block:
            lmkd_props = parse_properties_block(lmkd_block)
            properties["LMKD"] = lmkd_props
        
        # Extract Chimera properties
        chimera_block = extract_block(lines, "# Chimera property", ["#", ""])
        if chimera_block:
            chimera_props = parse_properties_block(chimera_block)
            properties["Chimera"] = chimera_props
        
        # Return None if no properties found
        if not properties["LMKD"] and not properties["Chimera"]:
            return None
        
        return properties
        
    except Exception:
        return None

def parse_properties_block(block_lines):
    """Parse property block and extract key-value pairs"""
    properties = {}
    
    for line in block_lines:
        line = line.strip()
        # Skip comments and empty lines  
        if not line or line.startswith("#"):
            continue
        
        # Look for property=value pattern
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Remove any trailing comments
            if "#" in value:
                value = value.split("#")[0].strip()
            
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
# UPDATED MAIN FUNCTION WITH DELETE SUPPORT
# ============================================================================

def update_properties_in_file(file_path, properties_dict):
    """Update properties in file with new values while preserving format and handling deletions"""
    try:
        # Read current file (no backup)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Update LMKD properties with deletion support
        if "LMKD" in properties_dict and properties_dict["LMKD"]:
            lines = update_properties_block_preserve_format_with_deletions(lines, properties_dict["LMKD"], 
                                          "# LMKD property", ["# Chimera property", "# DHA property"])
            if not any("# LMKD property" in line for line in lines):
                # Try with DHA property if LMKD not found
                lines = update_properties_block_preserve_format_with_deletions(lines, properties_dict["LMKD"], 
                                              "# DHA property", ["# Chimera property"])
        
        # Update Chimera properties with deletion support
        if "Chimera" in properties_dict and properties_dict["Chimera"]:
            lines = update_properties_block_preserve_format_with_deletions(lines, properties_dict["Chimera"], 
                                          "# Chimera property", ["# Nandswap", "#", ""]) 
        
        # Write updated file
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return True, None
        
    except Exception as e:
        return False, str(e)

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

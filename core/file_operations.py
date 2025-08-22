"""
Enhanced File operations for LMKD and Chimera properties with Delete Property support
Handles file reading, writing, and property extraction/deletion
"""
import os
import shutil
from datetime import datetime

def extract_block(lines, start_header, next_header_list):
    """Extract block of lines between headers"""
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

#     lmkd_block = extract_block(vince_lines, "# LMKD property", ["# Chimera property", "# DHA property"])
#     if not lmkd_block:
#         lmkd_block = extract_block(vince_lines, "# DHA property", ["# Chimera property"])
#     chimera_block = extract_block(vince_lines, "# Chimera property", ["# Nandswap", "#", ""]) 

#     updated_target = replace_block(target_lines, lmkd_block, "# LMKD property", ["# Chimera property", "# DHA property"])
#     updated_target = replace_block(updated_target, chimera_block, "# Chimera property", ["# Nandswap", "#", ""]) 

#     # Write updated file without creating a backup
#     with open(target_path, "w", encoding="utf-8") as f:
#         f.writelines(updated_target)
#     log_callback(f"[OK] Updated {target_name} file.")

def update_lmkd_chimera(vince_path, target_path, log_callback):
    """Update LMKD and Chimera properties in target file - Enhanced to add missing sections"""
    target_name = "BENI" if "beni" in target_path.lower() else "FLUMEN" if "flumen" in target_path.lower() else "TARGET"
    log_callback(f"[STEP 3] Updating LMKD and Chimera properties in {target_name}...")
    
    with open(vince_path, "r", encoding="utf-8") as f:
        vince_lines = f.readlines()
    with open(target_path, "r", encoding="utf-8") as f:
        target_lines = f.readlines()

    # Extract blocks from VINCE
    lmkd_block = extract_block(vince_lines, "# LMKD property", ["#", ""])
    if not lmkd_block:
        lmkd_block = extract_block(vince_lines, "# DHA property", ["#", ""])
    chimera_block = extract_block(vince_lines, "# Chimera property", ["#", ""]) 

    # Check what sections exist in target
    has_lmkd = any("# LMKD property" in line for line in target_lines)
    has_dha = any("# DHA property" in line for line in target_lines)
    has_chimera = any("# Chimera property" in line for line in target_lines)
    
    # Determine which LMKD/DHA header to use based on VINCE
    lmkd_header = "# LMKD property" if any("# LMKD property" in line for line in vince_lines) else "# DHA property"
    
    updated_target = target_lines[:]
    
    # Update existing sections
    if has_lmkd or has_dha:
        # Replace existing LMKD section
        if has_lmkd:
            updated_target = replace_block(updated_target, lmkd_block, "# LMKD property", ["#", ""])
        elif has_dha:
            updated_target = replace_block(updated_target, lmkd_block, "# DHA property", ["#", ""])
    
    if has_chimera:
        # Replace existing Chimera section
        updated_target = replace_block(updated_target, chimera_block, "# Chimera property", ["#", ""]) 
    
    # Add missing sections to end of file
    sections_to_add = []
    
    # Check if we need to add LMKD/DHA section
    if not has_lmkd and not has_dha and lmkd_block:
        sections_to_add.append(lmkd_block)
    
    # Check if we need to add Chimera section  
    if not has_chimera and chimera_block:
        sections_to_add.append(chimera_block)
    
    # Add missing sections to end of file
    if sections_to_add:
        # Ensure file ends with newline before adding sections
        if updated_target and not updated_target[-1].endswith('\n'):
            updated_target[-1] = updated_target[-1] + '\n'
        
        # Add a blank line before first new section
        updated_target.append('\n')
        
        # Add each missing section
        for section_block in sections_to_add:
            updated_target.extend(section_block)
            # Add blank line after each section (except last)
            if section_block != sections_to_add[-1]:
                updated_target.append('\n')

    # Write updated file without creating a backup
    with open(target_path, "w", encoding="utf-8") as f:
        f.writelines(updated_target)
    log_callback(f"[OK] Updated {target_name} file.")

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
        lmkd_block = extract_block(lines, "# LMKD property", ["# Chimera property", "# DHA property"])
        if not lmkd_block:
            lmkd_block = extract_block(lines, "# DHA property", ["# Chimera property"])
        
        if lmkd_block:
            lmkd_props = parse_properties_block(lmkd_block)
            properties["LMKD"] = lmkd_props
        
        # Extract Chimera properties
        chimera_block = extract_block(lines, "# Chimera property", ["# Nandswap", "#", ""])
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
    """Analyze and identify PRODUCT_PROPERTY_OVERRIDES blocks in the section"""
    override_blocks = []
    i = 1  # Skip header line
    
    while i < len(original_lines):
        line = original_lines[i]
        stripped_line = line.strip()
        
        if "PRODUCT_PROPERTY_OVERRIDES" in stripped_line and "+=" in stripped_line:
            # Start of new override block
            block_start = i
            block_properties = []
            block_lines = [i]  # Store line indices
            i += 1
            
            # Collect all properties in this block
            while i < len(original_lines):
                prop_line = original_lines[i]
                prop_stripped = prop_line.strip()
                
                if not prop_stripped or prop_stripped.startswith("#"):
                    block_lines.append(i)
                    i += 1
                    continue
                
                if "=" in prop_stripped:
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
                    # Non-property line, end of block
                    break
            
            override_blocks.append({
                'start': block_start,
                'properties': block_properties,
                'lines': block_lines
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
    """Update PRODUCT_PROPERTY_OVERRIDES blocks with new properties and handle deletions"""
    new_block = [original_lines[0]]  # Keep header line
    processed_lines = set()
    
    for line_idx in range(1, len(original_lines)):  # Skip header
        if line_idx in processed_lines:
            continue
            
        line = original_lines[line_idx]
        stripped_line = line.strip()
        
        # Keep comments and empty lines as-is
        if not stripped_line or stripped_line.startswith("#"):
            new_block.append(line)
            continue
        
        # Handle PRODUCT_PROPERTY_OVERRIDES blocks
        current_block = None
        for block in override_blocks:
            if line_idx == block['start']:
                current_block = block
                break
        
        if current_block:
            # Process entire PRODUCT_PROPERTY_OVERRIDES block
            new_block.append(original_lines[current_block['start']])  # Add PRODUCT_PROPERTY_OVERRIDES line
            processed_lines.add(current_block['start'])
            
            # Get indentation from existing properties
            default_indent = "    "
            for idx in current_block['lines'][1:]:  # Skip PRODUCT_PROPERTY_OVERRIDES line
                if idx < len(original_lines):
                    prop_line = original_lines[idx]
                    if "=" in prop_line.strip() and not prop_line.strip().startswith("#"):
                        default_indent = prop_line[:len(prop_line) - len(prop_line.lstrip())]
                        break
            
            # Collect all properties for this block (existing + new - deleted)
            block_props = {}
            
            # Add existing properties (only if they exist in remaining_properties - this handles deletions)
            for idx in current_block['lines'][1:]:  # Skip PRODUCT_PROPERTY_OVERRIDES line
                if idx < len(original_lines):
                    prop_line = original_lines[idx]
                    prop_stripped = prop_line.strip()
                    
                    if not prop_stripped or prop_stripped.startswith("#"):
                        continue
                        
                    if "=" in prop_stripped:
                        prop_content = prop_stripped[:-1].strip() if prop_stripped.endswith("\\") else prop_stripped
                        if "=" in prop_content:
                            key, original_value = prop_content.split("=", 1)
                            key = key.strip()
                            
                            # Only include if key exists in remaining_properties (deletion check)
                            if key in remaining_properties:
                                block_props[key] = remaining_properties[key]
                                del remaining_properties[key]
            
            # Add any remaining new properties to this block
            for key, value in list(remaining_properties.items()):
                block_props[key] = value
                del remaining_properties[key]
            
            # Write all properties in this block (only if there are properties left)
            if block_props:
                prop_items = list(block_props.items())
                for idx, (key, value) in enumerate(prop_items):
                    if idx == len(prop_items) - 1:  # Last property - no backslash
                        new_block.append(f"{default_indent}{key}={value}\n")
                    else:  # Not last property - add backslash
                        new_block.append(f"{default_indent}{key}={value} \\\n")
            
            # Mark all lines in this block as processed
            for idx in current_block['lines']:
                processed_lines.add(idx)
        
        # Handle regular property lines (not in PRODUCT_PROPERTY_OVERRIDES block)
        elif "=" in stripped_line and not "PRODUCT_PROPERTY_OVERRIDES" in stripped_line:
            key, old_value = stripped_line.split("=", 1)
            key = key.strip()
            
            # Only include if key exists in remaining_properties (deletion check)
            if key in remaining_properties:
                # Preserve original indentation
                indent = len(line) - len(line.lstrip())
                indent_str = line[:indent]
                
                # Get trailing comment if exists
                trailing_comment = ""
                if "#" in old_value:
                    value_part, comment_part = old_value.split("#", 1)
                    trailing_comment = " #" + comment_part.rstrip()
                
                # Use new value
                new_value = remaining_properties[key]
                new_line = f"{indent_str}{key}={new_value}{trailing_comment}\n"
                new_block.append(new_line)
                del remaining_properties[key]
            # If key not in remaining_properties, it's deleted - skip this line
        else:
            # Keep other lines unchanged
            new_block.append(line)
    
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
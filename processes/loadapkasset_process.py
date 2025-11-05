"""
LoadApkAsset process implementation
Handles adding asset apps to chipsets in ReadaheadManager.java
Processes across REL → FLUMEN → BENI with automatic integration
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from tkinter import messagebox

from core.p4_operations import (
    get_integration_source_depot_path,
    create_changelist_silent,
    map_single_depot,
    sync_file_silent,
    checkout_file_silent,
    validate_depot_path,
    find_device_common_mk_path
)

from config.p4_config import depot_to_local_path

# All available asset apps
AVAILABLE_ASSETS = [
    "ASSET_CAMERA",
    "ASSET_DIAL",
    "ASSET_CLOCK",
    "ASSET_CONTACT",
    "ASSET_CALENDAR",
    "ASSET_CALCULATOR",
    "ASSET_GALLERY",
    "ASSET_MESSAGE",
    "ASSET_MYFILE",
    "ASSET_SBROWSER",
    "ASSET_NOTE",
    "ASSET_SETTINGS",
    "ASSET_VOICENOTE"
]


def find_samsung_vendor_path(workspace_name, log_callback=None):
    """Find vendor/samsung base path from workspace"""
    try:
        _, view_paths = find_device_common_mk_path(workspace_name, log_callback)
        
        for view_path in view_paths:
            if "/vendor/samsung/" in view_path:
                match = re.search(r"(.+/vendor/samsung/)", view_path)
                if match:
                    samsung_path = match.group(1)
                    if log_callback:
                        log_callback(f"[FOUND] Samsung vendor path: {samsung_path}")
                    return samsung_path
        
        if log_callback:
            log_callback("[NOT_FOUND] No vendor/samsung path found")
        return None
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error finding samsung path: {str(e)}")
        return None


def construct_readahead_manager_path(samsung_path):
    """Construct ReadaheadManager.java path from samsung base path"""
    return f"{samsung_path}frameworks/sdhms/java/com/sec/android/sdhms/performance/module/readahead/ReadaheadManager.java"


def parse_readahead_manager_file(file_path, log_callback=None):
    """
    Parse ReadaheadManager.java file to extract chipset and their current assets
    
    Returns:
        Dict[str, List[str]]: Mapping of chipset name to list of current asset apps
    """
    try:
        local_path = depot_to_local_path(file_path)
        
        if log_callback:
            log_callback(f"[PARSE] Reading file: {local_path}")
        
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        chipset_assets = {}
        
        # Find initModel method - more flexible pattern
        init_model_match = re.search(r'private\s+void\s+initModel\s*\(\s*\)\s*\{', content, re.DOTALL)
        if not init_model_match:
            if log_callback:
                log_callback("[ERROR] Could not find initModel() method")
            return {}
        
        # Get content starting from initModel
        start_pos = init_model_match.end()
        
        # Find matching closing brace for initModel
        brace_count = 1
        end_pos = start_pos
        for i in range(start_pos, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break
        
        init_model_content = content[start_pos:end_pos]
        
        if log_callback:
            log_callback(f"[PARSE] Found initModel() method, length: {len(init_model_content)} chars")
        
        # Find all if blocks with CHIP_XXX - more flexible pattern
        # Pattern matches: if (PerformanceFeature.CHIP_XXXX) or else if (PerformanceFeature.CHIP_XXXX)
        chip_pattern = r'(?:else\s+)?if\s*\(\s*PerformanceFeature\.CHIP_(\w+)\s*\)'
        
        lines = init_model_content.split('\n')
        current_chip = None
        chip_block_lines = []
        
        for line in lines:
            # Check if this line starts a new chip block
            chip_match = re.search(chip_pattern, line)
            if chip_match:
                # Process previous chip block if exists
                if current_chip:
                    block_content = '\n'.join(chip_block_lines)
                    assets = extract_assets_from_block(block_content, log_callback)
                    chipset_assets[current_chip] = assets
                    if log_callback:
                        log_callback(f"[PARSED] {current_chip}: {', '.join(assets) if assets else '(no assets)'}")
                
                # Start new chip block
                current_chip = chip_match.group(1)
                chip_block_lines = []
            elif current_chip:
                # Add line to current chip block
                chip_block_lines.append(line)
                # Check if we hit another else if or end of blocks
                if line.strip().startswith('} else if') or line.strip() == '}':
                    if line.strip() == '}' and 'else' not in line:
                        # Process last chip block
                        block_content = '\n'.join(chip_block_lines)
                        assets = extract_assets_from_block(block_content, log_callback)
                        chipset_assets[current_chip] = assets
                        if log_callback:
                            log_callback(f"[PARSED] {current_chip}: {', '.join(assets) if assets else '(no assets)'}")
                        current_chip = None
                        chip_block_lines = []
        
        # Process last chip block if exists
        if current_chip and chip_block_lines:
            block_content = '\n'.join(chip_block_lines)
            assets = extract_assets_from_block(block_content, log_callback)
            chipset_assets[current_chip] = assets
            if log_callback:
                log_callback(f"[PARSED] {current_chip}: {', '.join(assets) if assets else '(no assets)'}")
        
        if log_callback:
            log_callback(f"[PARSE] Found {len(chipset_assets)} chipsets total")
        
        return chipset_assets
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to parse ReadaheadManager.java: {str(e)}")
            import traceback
            log_callback(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise


def extract_assets_from_block(block_content, log_callback=None):
    """Extract ASSET_XXX from a chip block"""
    # Find updateAssetKey call
    asset_match = re.search(r'mReadahead\.updateAssetKey\s*\(([^)]+)\)', block_content)
    if asset_match:
        assets_str = asset_match.group(1)
        # Extract all ASSET_XXX tokens
        assets = re.findall(r'ASSET_\w+', assets_str)
        return assets
    return []


def add_assets_to_chipset(file_path, chipset_name, new_assets, changelist_id, log_callback=None):
    """
    Add new assets to specified chipset in ReadaheadManager.java
    
    Args:
        file_path: Depot path to ReadaheadManager.java
        chipset_name: Name of chipset (e.g., "EXYNOS850")
        new_assets: List of asset names to add (e.g., ["ASSET_GALLERY", "ASSET_CLOCK"])
        changelist_id: Changelist ID to checkout file
    """
    try:
        local_path = depot_to_local_path(file_path)
        
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find the if block for this chipset
        chip_pattern = rf'(if\s*\(\s*PerformanceFeature\.CHIP_{chipset_name}\s*\)\s*\{{[^}}]*)(mReadahead\.updateAssetKey\(([^)]+)\))([^}}]*\}})'
        
        match = re.search(chip_pattern, content, re.DOTALL)
        if not match:
            if log_callback:
                log_callback(f"[ERROR] Could not find CHIP_{chipset_name} block")
            raise RuntimeError(f"Chipset {chipset_name} not found in file")
        
        prefix = match.group(1)
        old_update_call = match.group(2)
        current_assets_str = match.group(3)
        suffix = match.group(4)
        
        # Extract current assets
        current_assets = re.findall(r'ASSET_\w+', current_assets_str)
        
        # Add new assets (avoid duplicates)
        assets_to_add = [asset for asset in new_assets if asset not in current_assets]
        
        if not assets_to_add:
            if log_callback:
                log_callback(f"[INFO] All assets already exist for {chipset_name}")
            return False
        
        # Build new asset string
        all_assets = current_assets + assets_to_add
        new_assets_str = " | ".join(all_assets)
        new_update_call = f"mReadahead.updateAssetKey({new_assets_str})"
        
        # Replace in content
        new_block = prefix + new_update_call + suffix
        old_block = prefix + old_update_call + suffix
        
        new_content = content.replace(old_block, new_block)
        
        # Write back to file
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        if log_callback:
            log_callback(f"[OK] Added {len(assets_to_add)} assets to {chipset_name}: {', '.join(assets_to_add)}")
        
        return True
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to add assets: {str(e)}")
        raise


def process_single_branch_loadapkasset(branch_name, workspace_or_path, chipset_name, 
                                       new_assets, changelist_id, is_first_branch, log_callback=None):
    """
    Process single branch for LoadApkAsset mode
    
    Args:
        branch_name: "REL", "FLUMEN", or "BENI"
        workspace_or_path: For first branch - workspace name, for cascaded - integrated path
        chipset_name: Chipset to add assets to
        new_assets: List of assets to add
        changelist_id: Changelist ID
        is_first_branch: True if first branch in cascade
    
    Returns:
        str: Path to ReadaheadManager.java file
    """
    if log_callback:
        log_callback(f"\n[{branch_name}] ========== Processing {branch_name} ==========")
    
    try:
        # Get ReadaheadManager.java path
        if isinstance(workspace_or_path, str) and is_first_branch:
            # First branch - find from workspace
            if log_callback:
                log_callback(f"[{branch_name}] Finding ReadaheadManager.java from workspace...")
            
            samsung_path = find_samsung_vendor_path(workspace_or_path, log_callback)
            if not samsung_path:
                raise RuntimeError(f"Cannot find samsung vendor path in {branch_name}")
            
            readahead_manager_path = construct_readahead_manager_path(samsung_path)
        else:
            # Cascaded branch - use provided path
            readahead_manager_path = workspace_or_path
            if log_callback:
                log_callback(f"[{branch_name}] Using integrated ReadaheadManager.java path")
        
        # Validate path exists
        if not validate_depot_path(readahead_manager_path):
            raise RuntimeError(f"ReadaheadManager.java not found: {readahead_manager_path}")
        
        if log_callback:
            log_callback(f"[{branch_name}] Found: {readahead_manager_path}")
        
        # Map, sync, checkout
        map_single_depot(readahead_manager_path)
        sync_file_silent(readahead_manager_path)
        checkout_file_silent(readahead_manager_path, changelist_id)
        
        # Add assets to chipset
        modified = add_assets_to_chipset(
            readahead_manager_path, chipset_name, new_assets, 
            changelist_id, log_callback
        )
        
        if modified:
            if log_callback:
                log_callback(f"[{branch_name}] ✓ ReadaheadManager.java modified")
        else:
            if log_callback:
                log_callback(f"[{branch_name}] ℹ No changes needed")
        
        if log_callback:
            log_callback(f"[{branch_name}] ========== {branch_name} completed ==========")
        
        return readahead_manager_path
    
    except Exception as e:
        if log_callback:
            log_callback(f"[{branch_name}] [ERROR] {str(e)}")
        raise


def run_loadapkasset_process(workspaces, chipset_name, selected_assets, changelist_id,
                              log_callback, progress_callback=None, error_callback=None):
    """
    Execute LoadApkAsset process with integration cascading
    Cascades across REL → FLUMEN → BENI automatically
    """
    try:
        if log_callback:
            log_callback("[LOADAPKASSET] Starting LoadApkAsset process with integration cascading...")
        
        # Determine processing order
        rel_ws = workspaces.get("REL", "").strip()
        flumen_ws = workspaces.get("FLUMEN", "").strip()
        beni_ws = workspaces.get("BENI", "").strip()
        
        if log_callback:
            log_callback("[VALIDATION] Checking provided workspaces...")
            log_callback(f"[INPUT] REL: {rel_ws if rel_ws else '(not provided)'}")
            log_callback(f"[INPUT] FLUMEN: {flumen_ws if flumen_ws else '(not provided)'}")
            log_callback(f"[INPUT] BENI: {beni_ws if beni_ws else '(not provided)'}")
        
        # Validate at least one workspace
        if not rel_ws and not flumen_ws and not beni_ws:
            raise RuntimeError("At least one workspace from REL, FLUMEN, or BENI is required")
        
        # Determine cascade order
        cascade_branches = []
        if rel_ws:
            cascade_branches = ["REL", "FLUMEN", "BENI"]
        elif flumen_ws:
            cascade_branches = ["FLUMEN", "BENI"]
        elif beni_ws:
            cascade_branches = ["BENI"]
        
        if log_callback:
            log_callback(f"[CASCADE] Processing order: {' → '.join(cascade_branches)}")
        
        if progress_callback:
            progress_callback(10)
        
        # Create/get changelist
        if changelist_id:
            if log_callback:
                log_callback(f"[CL] Using provided changelist: {changelist_id}")
        else:
            changelist_id = create_changelist_silent("LoadApkAsset - Add asset apps to chipsets")
            if log_callback:
                log_callback(f"[CL] Created new changelist: {changelist_id}")
        
        if progress_callback:
            progress_callback(20)
        
        # Process branches with cascading
        current_readahead_manager_path = None
        progress_step = 80 / len(cascade_branches)
        current_progress = 20
        
        for idx, branch in enumerate(cascade_branches):
            try:
                is_first_branch = (idx == 0)
                
                # Determine input for this branch
                if idx == 0:
                    # First branch - use workspace name
                    branch_input = workspaces[branch]
                else:
                    # Cascaded branch - get path from integration
                    if log_callback:
                        log_callback(f"\n[CASCADE] Finding {branch} path from integration...")
                    
                    integrated_path = get_integration_source_depot_path(
                        current_readahead_manager_path, log_callback
                    )
                    
                    if not integrated_path:
                        if log_callback:
                            log_callback(f"[WARNING] Could not cascade to {branch}, skipping...")
                        continue
                    
                    branch_input = integrated_path
                
                # Process this branch
                readahead_manager_path = process_single_branch_loadapkasset(
                    branch, branch_input, chipset_name, selected_assets,
                    changelist_id, is_first_branch, log_callback
                )
                
                # Save path for next cascade
                current_readahead_manager_path = readahead_manager_path
                
                current_progress += progress_step
                if progress_callback:
                    progress_callback(int(current_progress))
            
            except Exception as e:
                if log_callback:
                    log_callback(f"[ERROR] Failed to process {branch}: {str(e)}")
                
                response = messagebox.askyesno(
                    "Processing Error",
                    f"Error processing {branch}: {str(e)}\n\nContinue with remaining branches?",
                )
                
                if not response:
                    raise
        
        if progress_callback:
            progress_callback(100)
        
        # Summary
        if log_callback:
            log_callback("\n[LOADAPKASSET] ========== PROCESS COMPLETED SUCCESSFULLY ==========")
            log_callback(f"[SUMMARY] Chipset: {chipset_name}")
            log_callback(f"[SUMMARY] Assets added: {', '.join(selected_assets)}")
            log_callback(f"[SUMMARY] Changelist: {changelist_id}")
            log_callback(f"[SUMMARY] Cascaded branches: {' → '.join(cascade_branches)}")
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] LoadApkAsset process failed: {str(e)}")
        if error_callback:
            error_callback("LoadApkAsset Process Error", str(e))
        if progress_callback:
            progress_callback(0)
        raise

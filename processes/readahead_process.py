"""
Readahead process implementation - REFACTORED VERSION
Handles the readahead mode business logic for workspace processing and rscmgr.rc modification
Enhanced with centralized utilities and reduced code duplication
"""
import os
import re
import subprocess
from tkinter import messagebox, simpledialog
from core.p4_operations import (
    create_changelist_silent, sync_file_silent, checkout_file_silent
)
from core.core_utils import (
    get_path_validator, get_client_mapper, get_auto_resolver
)
from processes.system_process import find_device_common_mk_path
from processes.system_process import process_target_workspace_enhanced
from config.p4_config import depot_to_local_path

def validate_workspace_format(workspace_name):
    """Validate if workspace has proper TEMPLATE format"""
    return get_path_validator().validate_workspace_format(workspace_name)

def detect_workspace_branch(workspace_name, log_callback=None):
    """Detect which branch a workspace belongs to (BENI, FLUMEN, REL)"""
    if not workspace_name:
        return None

    workspace_upper = workspace_name.upper()

    if "BENI" in workspace_upper:
        return "BENI"
    elif "FLUMEN" in workspace_upper:
        return "FLUMEN"
    elif "REL" in workspace_upper:
        return "REL"
    else:
        if log_callback:
            log_callback(
                f"[WARNING] Cannot detect branch for workspace: {workspace_name}"
            )
        return None

def find_rscmgr_filename_from_device_common(device_common_path, log_callback=None):
    """Find rscmgr.rc filename from device_common.mk file"""
    if log_callback:
        log_callback(f"[READAHEAD] Searching rscmgr filename in: {device_common_path}")

    try:
        local_path = depot_to_local_path(device_common_path)

        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for rscmgr.rc or rscmgr_{model}.rc pattern
        rscmgr_match = re.search(r"rscmgr(?:_\w+)?\.rc", content)

        if rscmgr_match:
            rscmgr_file = rscmgr_match.group(0)
            if log_callback:
                log_callback(f"[OK] Found rscmgr filename: {rscmgr_file}")
            return rscmgr_file
        else:
            if log_callback:
                log_callback("[WARNING] No rscmgr filename found in device_common.mk")
            return None

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Error reading device_common.mk: {str(e)}")
        return None

def prompt_for_rscmgr_filename(log_callback=None):
    """Prompt user to input rscmgr filename"""
    if log_callback:
        log_callback("[INPUT] Prompting user for rscmgr filename...")

    filename = simpledialog.askstring(
        "Rscmgr Filename",
        "Enter the rscmgr filename (e.g., rscmgr.rc or rscmgr_mt6789.rc):",
        initialvalue="rscmgr.rc",
    )

    if filename:
        # Store for future use (this would be persistent in real implementation)
        if log_callback:
            log_callback(f"[INPUT] User provided rscmgr filename: {filename}")
        return filename.strip()

    return None

def validate_pending_changelist(changelist_id, log_callback=None):
    """Validate if pending changelist exists and is editable"""
    if log_callback:
        log_callback(f"[VALIDATE] Checking pending changelist: {changelist_id}")

    try:
        # Get changelist info
        result = subprocess.run(
            f"p4 change -o {changelist_id}", capture_output=True, text=True, shell=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Changelist {changelist_id} does not exist")

        # Check if changelist is pending (not submitted)
        changelist_info = result.stdout
        if "Status:\tpending" not in changelist_info:
            raise RuntimeError(f"Changelist {changelist_id} is not in pending status")

        # Check if user owns this changelist
        import getpass

        current_user = getpass.getuser()
        if f"User:\t{current_user}" not in changelist_info:
            if log_callback:
                log_callback(
                    f"[WARNING] Changelist {changelist_id} may not belong to current user"
                )

        if log_callback:
            log_callback(f"[OK] Changelist {changelist_id} is valid and pending")

        return True

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Changelist validation failed: {str(e)}")
        return False

def extract_workspace_from_rscmgr_path(rscmgr_depot_path):
    """
    Extract workspace name from rscmgr.rc depot path
    Example: //depot_name/branch/vendor/samsung/model/rscmgr.rc → infer workspace
    This is reverse engineering from depot path to workspace
    """
    # For now, return the depot path itself as workspace
    # In a real implementation, you would map depot path back to workspace name
    # This could involve P4 client mapping analysis or workspace naming conventions

    # Simple approach: extract branch info from path and construct workspace name
    try:
        # Pattern: //depot/branch/... → extract branch part
        if "beni" in rscmgr_depot_path.lower():
            # Extract workspace pattern from depot path if possible
            # This is simplified - real implementation would be more sophisticated
            return rscmgr_depot_path  # Return depot path for now
        elif "flumen" in rscmgr_depot_path.lower():
            return rscmgr_depot_path
        elif "rel" in rscmgr_depot_path.lower():
            return rscmgr_depot_path
        else:
            return rscmgr_depot_path
    except:
        return rscmgr_depot_path

def auto_resolve_missing_branches_readahead(workspaces, rscmgr_filename, log_callback=None):
    """
    Auto-resolve missing branches for rscmgr.rc files using integration logic - REFACTORED
    Returns resolved workspaces dict with rscmgr.rc paths
    """
    if log_callback:
        log_callback("[AUTO-RESOLVE] Starting auto-resolve for readahead mode...")

    resolved = workspaces.copy()
    vendor = workspaces.get("VENDOR", "").strip()
    beni = workspaces.get("BENI", "").strip()
    flumen = workspaces.get("FLUMEN", "").strip()
    rel = workspaces.get("REL", "").strip()

    # Log input state
    if log_callback:
        log_callback(f"[INPUT] VENDOR: {vendor}")
        log_callback(f"[INPUT] BENI: {beni if beni else '(empty)'}")
        log_callback(f"[INPUT] FLUMEN: {flumen if flumen else '(empty)'}")
        log_callback(f"[INPUT] REL: {rel if rel else '(empty)'}")

    try:
        # Use centralized auto resolver for consistent behavior
        auto_resolver = get_auto_resolver()
        mapper = get_client_mapper()

        # Case 1: VENDOR + REL provided, but FLUMEN + BENI empty
        # Auto-resolve: REL rscmgr.rc → FLUMEN rscmgr.rc → BENI rscmgr.rc
        if vendor and rel and not flumen and not beni:
            log_callback(
                "[AUTO-RESOLVE] Case detected: VENDOR + REL → Auto-resolve FLUMEN and BENI rscmgr.rc files"
            )

            # Step 1: Find REL rscmgr.rc file path
            rel_rscmgr_path = find_rscmgr_file_path(rel, rscmgr_filename, log_callback)
            if not rel_rscmgr_path:
                raise RuntimeError(
                    f"Cannot find {rscmgr_filename} in REL workspace: {rel}"
                )

            # Use centralized cascading resolution: REL → FLUMEN → BENI
            cascading_result = auto_resolver.resolve_cascading_branches(
                rel_rscmgr_path, ["REL", "FLUMEN", "BENI"], log_callback
            )

            # Convert rscmgr.rc paths back to workspace format
            flumen_workspace = extract_workspace_from_rscmgr_path(cascading_result["FLUMEN"])
            beni_workspace = extract_workspace_from_rscmgr_path(cascading_result["BENI"])
            
            resolved["FLUMEN"] = flumen_workspace
            resolved["BENI"] = beni_workspace
            
            log_callback(f"[AUTO] Detected FLUMEN workspace from rscmgr.rc: {flumen_workspace}")
            log_callback(f"[AUTO] Detected BENI workspace from rscmgr.rc: {beni_workspace}")

        # Case 2: VENDOR + FLUMEN provided, but BENI empty (REL may or may not be provided)
        # Auto-resolve: FLUMEN rscmgr.rc → BENI rscmgr.rc
        elif vendor and flumen and not beni:
            log_callback(
                "[AUTO-RESOLVE] Case detected: VENDOR + FLUMEN → Auto-resolve BENI rscmgr.rc"
            )

            # Step 1: Find FLUMEN rscmgr.rc file path
            flumen_rscmgr_path = find_rscmgr_file_path(
                flumen, rscmgr_filename, log_callback
            )
            if not flumen_rscmgr_path:
                raise RuntimeError(
                    f"Cannot find {rscmgr_filename} in FLUMEN workspace: {flumen}"
                )

            # Use centralized resolution: FLUMEN → BENI
            cascading_result = auto_resolver.resolve_cascading_branches(
                flumen_rscmgr_path, ["FLUMEN", "BENI"], log_callback
            )

            # Convert BENI rscmgr.rc path back to workspace format
            beni_workspace = extract_workspace_from_rscmgr_path(cascading_result["BENI"])
            resolved["BENI"] = beni_workspace
            
            log_callback(f"[AUTO] Detected BENI workspace from rscmgr.rc: {beni_workspace}")

        # Case 3: All fields provided or no auto-resolve needed
        else:
            log_callback(
                "[AUTO-RESOLVE] No auto-resolve needed - processing with provided inputs"
            )

        # Log final resolved values
        log_callback("[AUTO-RESOLVE] Final resolved workspaces:")
        for key, value in resolved.items():
            if value:
                log_callback(f"[RESOLVED] {key}: {value}")

        return resolved

    except Exception as e:
        if log_callback:
            log_callback(f"[AUTO-RESOLVE ERROR] {str(e)}")
            log_callback("[FALLBACK] Using provided workspaces without auto-resolve")

        return workspaces.copy()

def find_rscmgr_file_path(workspace_name, rscmgr_filename, log_callback=None):
    """Find rscmgr file path in workspace using existing system process logic"""
    if log_callback:
        log_callback(
            f"[SEARCH] Looking for {rscmgr_filename} in workspace: {workspace_name}"
        )

    try:
        from processes.system_process import (
            find_device_common_mk_path,
            find_filtered_samsung_vendor_paths,
            find_rscmgr_file_in_samsung_paths,
            construct_rscmgr_file_path,
        )

        # Get device_common.mk and view paths from workspace
        device_common_path, all_view_paths = find_device_common_mk_path(
            workspace_name, log_callback
        )
        if not device_common_path:
            return None

        # Find filtered samsung vendor paths
        samsung_paths = find_filtered_samsung_vendor_paths(all_view_paths, log_callback)

        # Find rscmgr file in samsung paths
        rscmgr_path = find_rscmgr_file_in_samsung_paths(
            samsung_paths, rscmgr_filename, log_callback
        )

        # If not found in workspace paths, try constructing from device_common path
        if not rscmgr_path and device_common_path:
            base_path_match = re.search(r"^(.+/vendor/samsung/)", device_common_path)
            if base_path_match:
                base_samsung_path = base_path_match.group(1)
                constructed_path = construct_rscmgr_file_path(
                    base_samsung_path, rscmgr_filename, log_callback
                )

                # Validate constructed path
                path_validator = get_path_validator()
                if path_validator.validate_depot_path(constructed_path):
                    rscmgr_path = constructed_path

        return rscmgr_path

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to find rscmgr file: {str(e)}")
        return None

def edit_rscmgr_file(
    rscmgr_path, resource_num, libraries, changelist_id, log_callback=None
):
    """Edit rscmgr file to add libraries to specified resource section"""
    if log_callback:
        log_callback(
            f"[EDIT] Adding {len(libraries)} libraries to resource={resource_num} in {rscmgr_path}"
        )

    try:
        local_path = depot_to_local_path(rscmgr_path)

        # Read current content
        with open(local_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find resource section
        resource_section_found = False
        resource_pattern = f"sys.readahead.resource={resource_num}"
        section_start_index = None
        section_end_index = None
        ending_line = None
        ending_line_index = None

        # Find the resource section
        for i, line in enumerate(lines):
            if resource_pattern in line:
                resource_section_found = True
                section_start_index = i

                # Find the end of this resource section
                # Look for next "on property:" or end of file
                section_end_index = len(lines)  # Default to end of file
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("on property:"):
                        section_end_index = j
                        break

                # Check the last line of this section for --fully
                # Find the last non-empty line in this section
                for k in range(section_end_index - 1, section_start_index, -1):
                    if lines[k].strip():
                        last_line = lines[k].strip()
                        if "--fully" not in last_line:
                            # This is an ending line (like setprop), save it for later
                            ending_line = lines[k]
                            ending_line_index = k
                            if log_callback:
                                log_callback(f"[DETECT] Found ending line: {last_line}")
                        break

                break

        # If resource section not found, create it
        if not resource_section_found:
            if log_callback:
                log_callback(
                    f"[CREATE] Creating new resource section for resource={resource_num}"
                )

            # Find a good place to insert (after existing sections or at end)
            insert_index = len(lines)

            # Add new resource section
            new_section_lines = [
                f"\non property:sys.readahead.resource={resource_num}\n"
            ]

            # Add libraries
            for library in libraries:
                formatted_line = f"    readahead {library} --fully\n"
                new_section_lines.append(formatted_line)

            # Add ending line
            new_section_lines.append("    setprop sys.readahead.resource 0\n")

            # Insert new section
            lines.extend(new_section_lines)
        else:
            # Resource section exists, insert libraries
            if log_callback:
                log_callback(
                    f"[MODIFY] Modifying existing resource section for resource={resource_num}"
                )

            # Remove ending line if it exists
            if ending_line_index is not None:
                removed_line = lines.pop(ending_line_index)
                if log_callback:
                    log_callback(
                        f"[REMOVE] Temporarily removed ending line: {removed_line.strip()}"
                    )
                # Update section_end_index after removal
                section_end_index -= 1

            # Find insertion point (after existing readahead entries)
            insert_index = section_start_index + 1

            # Skip existing readahead entries to find insertion point
            for j in range(section_start_index + 1, section_end_index):
                if lines[j].strip().startswith("readahead") and "--fully" in lines[j]:
                    insert_index = j + 1
                else:
                    break

            # Insert new libraries
            new_lines = []
            for library in libraries:
                formatted_line = f"    readahead {library} --fully\n"
                new_lines.append(formatted_line)

            # Insert new libraries at the correct position
            for j, new_line in enumerate(new_lines):
                lines.insert(insert_index + j, new_line)

            # Add back the ending line if it existed
            if ending_line is not None:
                lines.insert(insert_index + len(new_lines), ending_line)
                if log_callback:
                    log_callback(
                        f"[RESTORE] Restored ending line: {ending_line.strip()}"
                    )

        # Write updated content
        with open(local_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        if log_callback:
            log_callback(
                f"[OK] Added {len(libraries)} libraries to resource={resource_num}"
            )

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Failed to edit rscmgr file: {str(e)}")
        raise

def process_workspace_sequence(
    workspaces,
    rscmgr_filename,
    resource1_libs,
    resource2_libs,
    changelist_id,
    log_callback=None,
):
    """Process workspaces in order: REL → FLUMEN → BENI - REFACTORED"""
    if log_callback:
        log_callback("[SEQUENCE] Processing workspaces in order: REL → FLUMEN → BENI")

    # Use provided changelist or create new
    if changelist_id:
        if log_callback:
            log_callback(f"[CL] Using provided changelist: {changelist_id}")
        final_changelist_id = changelist_id
    else:
        # Create shared changelist
        final_changelist_id = create_changelist_silent(
            "Readahead - Update rscmgr.rc files"
        )
        if log_callback:
            log_callback(f"[CL] Created new changelist: {final_changelist_id}")

    # Process order: REL, FLUMEN, BENI
    process_order = ["REL", "FLUMEN", "BENI"]
    mapper = get_client_mapper()

    for branch in process_order:
        workspace = workspaces.get(branch, "").strip()
        if not workspace:
            continue

        if log_callback:
            log_callback(f"\n[PROCESS] Processing {branch} workspace: {workspace}")

        try:
            # Find rscmgr file path - handle both workspace names and depot paths
            if workspace.startswith("//"):
                # Direct depot path to rscmgr.rc file
                rscmgr_path = workspace
            else:
                # Workspace name - find rscmgr.rc using existing logic
                rscmgr_path = find_rscmgr_file_path(
                    workspace, rscmgr_filename, log_callback
                )

            if not rscmgr_path:
                if log_callback:
                    log_callback(
                        f"[ERROR] Could not find {rscmgr_filename} in {branch}"
                    )
                # Show popup and ask to continue
                response = messagebox.askyesno(
                    "File Not Found",
                    f"Could not find {rscmgr_filename} in {branch} workspace.\n\nContinue with remaining workspaces?",
                )
                if not response:
                    break
                continue

            # Map, sync and checkout rscmgr file using centralized utilities
            mapper.map_single_depot(rscmgr_path)
            sync_file_silent(rscmgr_path)
            checkout_file_silent(rscmgr_path, final_changelist_id)

            # Edit rscmgr file for Resource=1
            if resource1_libs:
                edit_rscmgr_file(
                    rscmgr_path, 1, resource1_libs, final_changelist_id, log_callback
                )

            # Edit rscmgr file for Resource=2
            if resource2_libs:
                edit_rscmgr_file(
                    rscmgr_path, 2, resource2_libs, final_changelist_id, log_callback
                )

            if log_callback:
                log_callback(f"[OK] {branch} processing completed")

        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Failed to process {branch}: {str(e)}")
            # Continue with other workspaces
            continue

    return final_changelist_id

def run_readahead_process(
    workspaces,
    resource1_libs,
    resource2_libs,
    changelist_id,
    log_callback,
    progress_callback=None,
    error_callback=None,
):
    """Execute the readahead process - REFACTORED VERSION"""
    try:
        if log_callback:
            log_callback("[READAHEAD] Starting readahead process...")

        # ============================================================================
        # STEP 0: VALIDATE CHANGELIST (if provided)
        # ============================================================================
        if changelist_id:
            if log_callback:
                log_callback(
                    f"[VALIDATION] Validating provided changelist: {changelist_id}"
                )

            if not validate_pending_changelist(changelist_id, log_callback):
                raise RuntimeError(
                    f"Invalid or inaccessible changelist: {changelist_id}"
                )

        # ============================================================================
        # STEP 1: VALIDATION using centralized validator
        # ============================================================================
        if log_callback:
            log_callback("[VALIDATION] Validating inputs...")

        vendor = workspaces.get("VENDOR", "").strip()
        if not vendor:
            raise RuntimeError("VENDOR workspace is mandatory")

        path_validator = get_path_validator()
        if not path_validator.validate_workspace_format(vendor):
            raise RuntimeError(f"VENDOR must be a workspace (TEMPLATE_*): {vendor}")

        # Validate at least one other workspace
        other_branches = ["BENI", "FLUMEN", "REL"]
        provided_workspaces = [
            workspaces.get(branch, "").strip()
            for branch in other_branches
            if workspaces.get(branch, "").strip()
        ]

        if not provided_workspaces:
            raise RuntimeError(
                "At least one workspace from BENI, FLUMEN, or REL is required"
            )

        # Validate workspace formats
        for branch in other_branches:
            workspace = workspaces.get(branch, "").strip()
            if workspace and not path_validator.validate_workspace_format(workspace):
                raise RuntimeError(
                    f"{branch} must be a workspace (TEMPLATE_*): {workspace}"
                )

        if progress_callback:
            progress_callback(10)

        # ============================================================================
        # STEP 2: FIND RSCMGR FILENAME FROM VENDOR using centralized utilities
        # ============================================================================
        if log_callback:
            log_callback(
                "[VENDOR] Processing VENDOR workspace to find rscmgr filename..."
            )

        # Get device_common.mk from VENDOR workspace using Parse logic
        vendor_device_common, _ = find_device_common_mk_path(vendor, log_callback)
        if not vendor_device_common:
            raise RuntimeError(
                f"Cannot find device_common.mk in VENDOR workspace: {vendor}"
            )

        # Map and sync VENDOR device_common.mk using centralized utilities
        mapper = get_client_mapper()
        mapper.map_single_depot(vendor_device_common)
        sync_file_silent(vendor_device_common)

        # Find rscmgr filename
        rscmgr_filename = find_rscmgr_filename_from_device_common(
            vendor_device_common, log_callback
        )

        if not rscmgr_filename:
            # Prompt user for filename
            rscmgr_filename = prompt_for_rscmgr_filename(log_callback)
            if not rscmgr_filename:
                raise RuntimeError("rscmgr filename is required to proceed")

        if log_callback:
            log_callback(f"[OK] Using rscmgr filename: {rscmgr_filename}")

        if progress_callback:
            progress_callback(30)

        # ============================================================================
        # STEP 3: AUTO-RESOLVE MISSING BRANCHES using refactored function
        # ============================================================================
        if log_callback:
            log_callback("[AUTO-RESOLVE] Auto-resolving missing branches...")

        resolved_workspaces = auto_resolve_missing_branches_readahead(
            workspaces, rscmgr_filename, log_callback
        )

        if progress_callback:
            progress_callback(50)

        # ============================================================================
        # STEP 4: PROCESS WORKSPACE SEQUENCE using refactored function
        # ============================================================================
        if log_callback:
            log_callback(
                "[SEQUENCE] Processing workspaces in order: REL → FLUMEN → BENI"
            )

        final_changelist_id = process_workspace_sequence(
            resolved_workspaces,
            rscmgr_filename,
            resource1_libs,
            resource2_libs,
            changelist_id,
            log_callback,
        )

        if progress_callback:
            progress_callback(100)

        # ============================================================================
        # STEP 5: SUMMARY
        # ============================================================================
        if log_callback:
            log_callback(f"\n[READAHEAD] Process completed successfully!")
            log_callback(f"[SUMMARY] Rscmgr filename: {rscmgr_filename}")
            log_callback(f"[SUMMARY] Resource=1 libraries: {len(resource1_libs)}")
            log_callback(f"[SUMMARY] Resource=2 libraries: {len(resource2_libs)}")
            log_callback(f"[SUMMARY] Changelist: {final_changelist_id}")

            processed_branches = []
            for branch in ["REL", "FLUMEN", "BENI"]:
                if resolved_workspaces.get(branch, "").strip():
                    processed_branches.append(branch)
            log_callback(
                f"[SUMMARY] Processed branches: {', '.join(processed_branches)}"
            )

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Readahead process failed: {str(e)}")
        if error_callback:
            error_callback("Readahead Process Error", str(e))
        if progress_callback:
            progress_callback(0)
        raise
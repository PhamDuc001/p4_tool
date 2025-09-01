"""
Core utilities module - Centralized common functionality
Consolidates duplicated functions across modules
"""
import subprocess
import re
from typing import List, Optional, Dict, Tuple, Any
from config.p4_config import get_client_name, depot_to_local_path


class P4ClientMapper:
    """Centralized client mapping functionality"""
    
    def __init__(self):
        self.client_name = get_client_name()
        if not self.client_name:
            raise RuntimeError("Client name not initialized. Please check P4 configuration.")
    
    def map_depots(self, depot_paths: List[str], log_callback=None, silent=False):
        """
        Generic function to map multiple depot paths to client spec
        
        Args:
            depot_paths: List of depot paths to map
            log_callback: Optional logging callback
            silent: If True, suppress logging
        """
        from core.p4_operations import run_cmd
        
        if not depot_paths:
            return
        
        if log_callback and not silent:
            depot_names = [self._get_depot_name(path) for path in depot_paths]
            log_callback(f"[STEP 2] Mapping {', '.join(depot_names)} to client spec...")
        
        client_spec = run_cmd("p4 client -o")
        lines = client_spec.splitlines()
        new_lines = []
        
        # Remove existing mappings for these depots
        for line in lines:
            if not any(depot in line for depot in depot_paths):
                new_lines.append(line)
        
        # Add new mappings
        for depot_path in depot_paths:
            new_lines.append(f"\t{depot_path}\t//{self.client_name}/{depot_path[2:]}")
        
        new_spec = "\n".join(new_lines)
        run_cmd("p4 client -i", input_text=new_spec)
        
        if log_callback and not silent:
            log_callback("[OK] Mapping completed.")
    
    def _get_depot_name(self, depot_path: str) -> str:
        """Extract readable depot name from depot path"""
        depot_path_lower = depot_path.lower()
        if "beni" in depot_path_lower:
            return "BENI"
        elif "flumen" in depot_path_lower:
            return "FLUMEN"
        elif "vince" in depot_path_lower:
            return "VINCE"
        elif "rel" in depot_path_lower:
            return "REL"
        else:
            return "DEPOT"
    
    # Convenience methods for backward compatibility
    def map_single_depot(self, depot_path: str, log_callback=None):
        """Map single depot to client spec"""
        self.map_depots([depot_path], log_callback)
    
    def map_two_depots(self, depot1: str, depot2: str, log_callback=None, silent=False):
        """Map two depots to client spec"""
        self.map_depots([depot1, depot2], log_callback, silent)
    
    def map_three_depots(self, depot1: str, depot2: str, depot3: str, log_callback=None, silent=False):
        """Map three depots to client spec"""
        self.map_depots([depot1, depot2, depot3], log_callback, silent)
    
    def map_four_depots(self, depot1: str, depot2: str, depot3: str, depot4: str, log_callback=None):
        """Map four depots to client spec"""
        self.map_depots([depot1, depot2, depot3, depot4], log_callback)


class PropertyManager:
    """Centralized property extraction and management"""
    
    @staticmethod
    def extract_properties_from_file(file_path: str) -> Optional[Dict[str, Dict[str, str]]]:
        """Extract LMKD and Chimera properties from file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            properties = {"LMKD": {}, "Chimera": {}}
            
            # Extract LMKD properties
            lmkd_block = PropertyManager._extract_block(
                lines, "# LMKD property", ["# Chimera property", "# DHA property"]
            )
            if not lmkd_block:
                lmkd_block = PropertyManager._extract_block(
                    lines, "# DHA property", ["# Chimera property"]
                )
            
            if lmkd_block:
                lmkd_props = PropertyManager._parse_properties_block(lmkd_block)
                properties["LMKD"] = lmkd_props
            
            # Extract Chimera properties
            chimera_block = PropertyManager._extract_block(
                lines, "# Chimera property", ["# Nandswap", "#", ""]
            )
            if chimera_block:
                chimera_props = PropertyManager._parse_properties_block(chimera_block)
                properties["Chimera"] = chimera_props
            
            # Return None if no properties found
            if not properties["LMKD"] and not properties["Chimera"]:
                return None
            
            return properties
            
        except Exception:
            return None
    
    @staticmethod
    def _extract_block(lines: List[str], start_header: str, next_header_list: List[str]) -> List[str]:
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
    
    @staticmethod
    def _parse_properties_block(block_lines: List[str]) -> Dict[str, str]:
        """Parse property block and extract key-value pairs"""
        properties = {}
        
        for line in block_lines:
            line = line.strip()
            # Skip comments and empty lines  
            if not line or line.startswith("#"):
                continue
            
            # Skip PRODUCT_PROPERTY_OVERRIDES lines
            if "PRODUCT_PROPERTY_OVERRIDES" in line:
                continue
            
            # Look for property=value pattern
            if "=" in line:
                # Remove backslash if present
                clean_line = line.rstrip(" \\")
                
                key, value = clean_line.split("=", 1)
                key = key.strip()
                value = value.strip()
                
                # Remove any trailing comments
                if "#" in value:
                    value = value.split("#")[0].strip()
                
                properties[key] = value
        
        return properties
    
    @staticmethod
    def compare_properties(props1: Dict[str, Dict], props2: Dict[str, Dict]) -> List[str]:
        """Compare properties between two property dictionaries"""
        differences = []
        
        # Compare LMKD properties
        lmkd1 = props1.get("LMKD", {})
        lmkd2 = props2.get("LMKD", {})
        lmkd_diffs = PropertyManager._compare_property_dict(lmkd1, lmkd2, "LMKD")
        differences.extend(lmkd_diffs)
        
        # Compare Chimera properties
        chimera1 = props1.get("Chimera", {})
        chimera2 = props2.get("Chimera", {})
        chimera_diffs = PropertyManager._compare_property_dict(chimera1, chimera2, "Chimera")
        differences.extend(chimera_diffs)
        
        return differences
    
    @staticmethod
    def _compare_property_dict(dict1: Dict[str, str], dict2: Dict[str, str], category: str) -> List[str]:
        """Compare two property dictionaries"""
        differences = []
        
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        for key in all_keys:
            val1 = dict1.get(key, "<missing>")
            val2 = dict2.get(key, "<missing>")
            
            if val1 != val2:
                differences.append(f"{category}.{key}: Dict1='{val1}' vs Dict2='{val2}'")
        
        return differences


class PathValidator:
    """Centralized path validation functionality"""
    
    @staticmethod
    def validate_depot_path(depot_path: str) -> bool:
        """Validate if depot path exists in Perforce"""
        try:
            result = subprocess.run(
                f"p4 files {depot_path}", 
                capture_output=True, 
                text=True, 
                shell=True
            )
            if result.returncode != 0 or "no such file" in result.stderr.lower():
                return False
            return True
        except:
            return False
    
    @staticmethod
    def validate_device_common_mk_path(depot_path: str) -> Tuple[bool, bool]:
        """
        Validate if depot path exists and is a device_common.mk file
        Returns (exists, is_device_common_mk)
        """
        try:
            # Check if path exists
            result = subprocess.run(
                f"p4 files {depot_path}", 
                capture_output=True, 
                text=True, 
                shell=True
            )
            if result.returncode != 0 or "no such file" in result.stderr.lower():
                return False, False
            
            # Check if it's a device_common.mk file
            is_device_common = depot_path.endswith("/device_common.mk")
            
            return True, is_device_common
            
        except:
            return False, False
    
    @staticmethod
    def is_workspace_like(user_input: str) -> bool:
        """Return True if the input string looks like a P4 workspace template name."""
        if not user_input:
            return False
        return user_input.strip().upper().startswith("TEMPLATE")
    
    @staticmethod
    def validate_workspace_format(workspace_name: str) -> bool:
        """Validate if workspace has proper TEMPLATE format"""
        if not workspace_name:
            return False
        return PathValidator.is_workspace_like(workspace_name)


class AutoResolver:
    """Centralized auto-resolve functionality"""
    
    def __init__(self):
        self.mapper = P4ClientMapper()
        self.validator = PathValidator()
    
    def get_integration_source_depot_path(self, depot_path: str, log_callback=None) -> Optional[str]:
        """
        Get integration source depot path from p4 filelog version #1
        Parse integration history and return source depot path from "branch from" line
        Returns None if no integration source found or parsing failed
        """
        try:
            # Use #1 to get the first version (integration source)
            cmd = f"p4 filelog -i {depot_path}#1"
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                if log_callback:
                    log_callback(f"[WARNING] P4 filelog command failed for {depot_path}#1")
                return None
            
            output = result.stdout.strip()
            if not output:
                if log_callback:
                    log_callback(f"[WARNING] Empty filelog output for {depot_path}#1")
                return None
            
            # Look for "... ... branch from <path>#<version>" pattern
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("... ... branch from "):
                    # Extract path from "... ... branch from //path/device_common.mk#1"
                    # Remove "... ... branch from " prefix and "#<version>" suffix
                    source_path = line[len("... ... branch from "):].split('#')[0]
                    if log_callback:
                        log_callback(f"[PARSE] Extracted integration source: {source_path}")
                    return source_path
                    
            if log_callback:
                log_callback(f"[WARNING] No 'branch from' line found in filelog output for {depot_path}#1")
            return None
            
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Error getting integration source: {str(e)}")
            return None
    
    def resolve_cascading_branches(self, start_depot: str, branch_order: List[str], 
                                  log_callback=None) -> Dict[str, str]:
        """
        Generic cascading branch resolution
        
        Args:
            start_depot: Starting depot path
            branch_order: Order of branches to resolve (e.g., ["REL", "FLUMEN", "BENI"])
            log_callback: Optional logging callback
            
        Returns:
            Dict mapping branch names to depot paths
        """
        resolved = {}
        current_depot = start_depot
        current_branch = branch_order[0]
        resolved[current_branch] = current_depot
        
        if log_callback:
            log_callback(f"[AUTO-RESOLVE] Starting cascading resolution from {current_branch}: {current_depot}")
        
        try:
            # Map and sync starting depot
            from core.p4_operations import sync_file_silent
            self.mapper.map_single_depot(current_depot)
            sync_file_silent(current_depot)
            
            # Resolve remaining branches in order
            for i in range(1, len(branch_order)):
                next_branch = branch_order[i]
                
                # Get integration source from current depot
                source_depot = self.get_integration_source_depot_path(current_depot, log_callback)
                if not source_depot:
                    raise RuntimeError(f"No integration history found for {current_branch}: {current_depot}")
                
                # Validate source exists
                if not self.validator.validate_depot_path(source_depot):
                    raise RuntimeError(f"Integration source does not exist: {source_depot}")
                
                resolved[next_branch] = source_depot
                if log_callback:
                    log_callback(f"[AUTO] Detected {next_branch} from {current_branch}: {source_depot}")
                
                # Prepare for next iteration
                current_depot = source_depot
                current_branch = next_branch
                
                # Map and sync for next iteration
                self.mapper.map_single_depot(source_depot)
                sync_file_silent(source_depot)
            
            if log_callback:
                log_callback("[AUTO-RESOLVE] Cascading resolution completed successfully")
            
            return resolved
            
        except Exception as e:
            if log_callback:
                log_callback(f"[AUTO-RESOLVE ERROR] {str(e)}")
            raise RuntimeError(f"Auto-resolve failed: {str(e)}")


# Global instances for backward compatibility
_client_mapper = None
_property_manager = None 
_path_validator = None
_auto_resolver = None

def get_client_mapper():
    global _client_mapper
    if _client_mapper is None:
        _client_mapper = P4ClientMapper()
    return _client_mapper

def get_property_manager():
    global _property_manager
    if _property_manager is None:
        _property_manager = PropertyManager()
    return _property_manager

def get_path_validator():
    global _path_validator
    if _path_validator is None:
        _path_validator = PathValidator()
    return _path_validator

def get_auto_resolver():
    global _auto_resolver
    if _auto_resolver is None:
        _auto_resolver = AutoResolver()
    return _auto_resolver
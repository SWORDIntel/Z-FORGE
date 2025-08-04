#!/usr/bin/env python3
"""
ZFS Root Selection Module for Calamares

This module handles the selection and configuration of the target ZFS dataset
for system installation.
"""

import subprocess
import json
import os
from typing import Dict, List, Optional

try:
    import libcalamares
    from libcalamares.utils import gettext_path, gettext_languages
except ImportError:
    # For testing outside Calamares
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    import libcalamares

class ZfsrootselectJob:
    """
    Calamares Job for ZFS root selection and configuration
    """
    
    def __init__(self):
        self.gs = libcalamares.globalstorage
        self.selected_pool = None
        self.selected_dataset = None
        self.installation_mode = "new"
        
    def pretty_name(self):
        """Return pretty name for the job"""
        return "Configure ZFS Root Dataset"
        
    def detect_pools(self) -> List[Dict]:
        """Detect available ZFS pools"""
        pools = []
        try:
            # Run zpool list to get available pools
            result = subprocess.run(
                ["zpool", "list", "-H", "-o", "name,size,allocated,free,health"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 5:
                            pools.append({
                                "name": parts[0],
                                "size": parts[1],
                                "allocated": parts[2],
                                "free": parts[3],
                                "health": parts[4]
                            })
        except Exception as e:
            libcalamares.utils.warning(f"Failed to detect ZFS pools: {e}")
            
        return pools
        
    def detect_datasets(self, pool_name: str) -> List[Dict]:
        """Detect datasets in a pool"""
        datasets = []
        try:
            # Run zfs list for the specific pool
            result = subprocess.run(
                ["zfs", "list", "-H", "-r", "-o", "name,mountpoint,used,available", pool_name],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            datasets.append({
                                "name": parts[0],
                                "mountpoint": parts[1],
                                "used": parts[2],
                                "available": parts[3]
                            })
        except Exception as e:
            libcalamares.utils.warning(f"Failed to detect datasets: {e}")
            
        return datasets
        
    def create_root_dataset(self, pool_name: str, dataset_name: str) -> bool:
        """Create a new root dataset for installation"""
        try:
            full_dataset = f"{pool_name}/{dataset_name}"
            
            # Create the dataset
            result = subprocess.run(
                ["zfs", "create", "-o", "mountpoint=/", full_dataset],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                libcalamares.utils.error(f"Failed to create dataset: {result.stderr}")
                return False
                
            # Set additional properties
            properties = [
                ("compression", "lz4"),
                ("atime", "off"),
                ("xattr", "sa"),
                ("acltype", "posixacl")
            ]
            
            for prop, value in properties:
                subprocess.run(
                    ["zfs", "set", f"{prop}={value}", full_dataset],
                    capture_output=True,
                    check=False
                )
                
            return True
            
        except Exception as e:
            libcalamares.utils.error(f"Exception creating dataset: {e}")
            return False
            
    def configure_boot_dataset(self, pool_name: str) -> bool:
        """Configure boot dataset if needed"""
        try:
            boot_dataset = f"{pool_name}/boot"
            
            # Check if boot dataset exists
            result = subprocess.run(
                ["zfs", "list", boot_dataset],
                capture_output=True,
                check=False
            )
            
            if result.returncode != 0:
                # Create boot dataset
                subprocess.run(
                    ["zfs", "create", "-o", "mountpoint=/boot", boot_dataset],
                    capture_output=True,
                    check=True
                )
                
            return True
            
        except Exception as e:
            libcalamares.utils.warning(f"Failed to configure boot dataset: {e}")
            return False
            
    def set_pool_bootfs(self, pool_name: str, dataset_name: str) -> bool:
        """Set the bootfs property on the pool"""
        try:
            full_dataset = f"{pool_name}/{dataset_name}"
            
            result = subprocess.run(
                ["zpool", "set", f"bootfs={full_dataset}", pool_name],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                libcalamares.utils.error(f"Failed to set bootfs: {result.stderr}")
                return False
                
            return True
            
        except Exception as e:
            libcalamares.utils.error(f"Exception setting bootfs: {e}")
            return False
            
    def run(self):
        """Execute the job"""
        libcalamares.utils.debug("Starting ZFS root selection job")
        
        # Get configuration from global storage
        config_str = self.gs.value("zfsRootConfig")
        if not config_str:
            # Use defaults if no configuration
            config = {
                "pool": "tank",
                "dataset": "root",
                "mode": "new"
            }
        else:
            try:
                config = json.loads(config_str)
            except json.JSONDecodeError:
                libcalamares.utils.error("Failed to parse ZFS root configuration")
                return ("Failed to parse configuration", "Invalid JSON in zfsRootConfig")
                
        self.selected_pool = config.get("pool", "tank")
        self.selected_dataset = config.get("dataset", "root")
        self.installation_mode = config.get("mode", "new")
        
        libcalamares.utils.debug(f"Selected pool: {self.selected_pool}")
        libcalamares.utils.debug(f"Selected dataset: {self.selected_dataset}")
        libcalamares.utils.debug(f"Installation mode: {self.installation_mode}")
        
        # Verify pool exists
        pools = self.detect_pools()
        pool_names = [p["name"] for p in pools]
        
        if self.selected_pool not in pool_names:
            return (f"Pool not found", f"ZFS pool '{self.selected_pool}' does not exist")
            
        # Create or prepare the root dataset
        if self.installation_mode == "new":
            # Create new dataset
            if not self.create_root_dataset(self.selected_pool, self.selected_dataset):
                return ("Failed to create dataset", 
                       f"Could not create dataset {self.selected_pool}/{self.selected_dataset}")
                       
        elif self.installation_mode == "replace":
            # Check dataset exists
            datasets = self.detect_datasets(self.selected_pool)
            dataset_names = [d["name"] for d in datasets]
            full_dataset = f"{self.selected_pool}/{self.selected_dataset}"
            
            if full_dataset not in dataset_names:
                return ("Dataset not found", 
                       f"Dataset {full_dataset} does not exist for replacement")
                       
        # Configure boot dataset
        if not self.configure_boot_dataset(self.selected_pool):
            libcalamares.utils.warning("Boot dataset configuration failed (non-fatal)")
            
        # Set bootfs property
        if not self.set_pool_bootfs(self.selected_pool, self.selected_dataset):
            return ("Failed to set bootfs", 
                   f"Could not set bootfs property on pool {self.selected_pool}")
                   
        # Store the target for other modules
        self.gs.insert("zfsRootDataset", f"{self.selected_pool}/{self.selected_dataset}")
        self.gs.insert("zfsBootPool", self.selected_pool)
        
        libcalamares.utils.debug("ZFS root selection completed successfully")
        return None

# Module entry point for Calamares
def run():
    """Entry point for Calamares job execution"""
    job = ZfsrootselectJob()
    return job.run()
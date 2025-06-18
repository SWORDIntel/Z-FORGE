#!/usr/bin/env python3
# calamares/modules/zfspooldetect/main.py

"""
ZFS Pool Detection Module
Scans system for existing ZFS pools and validates them for installation
"""

import subprocess
import json
import os
import libcalamares
from typing import Dict, List, Optional

def pretty_name():
    return "Detecting ZFS Storage Pools"

def pretty_status_message():
    """Dynamic status message during execution"""
    return "Scanning for existing ZFS pools..."

def run():
    """
    Main entry point for pool detection
    Finds all importable ZFS pools and their datasets
    """
    
    libcalamares.utils.debug("Starting ZFS pool detection...")
    
    try:
        # Import all pools in read-only mode for safety
        pools = import_all_pools()
        
        if not pools:
            # No pools found, show error
            libcalamares.utils.warning("No ZFS pools found on system")
            return ("No ZFS pools detected",
                    "No existing ZFS pools were found on this system. "
                    "Please use the 'Bootstrap New Proxmox VE' option instead.")
        
        # Scan each pool for suitable root datasets
        pool_info = {}
        for pool in pools:
            info = scan_pool(pool)
            if info['suitable_for_install']:
                pool_info[pool] = info
        
        if not pool_info:
            return ("No suitable pools",
                    "ZFS pools were found but none contain suitable root datasets. "
                    "Found pools: " + ", ".join(pools))
        
        # Store results in global storage for next module
        libcalamares.globalstorage.insert("zfs_pools", pool_info)
        libcalamares.globalstorage.insert("zfs_pool_names", list(pool_info.keys()))
        
        # Log detected configuration
        libcalamares.utils.debug(f"Detected pools: {json.dumps(pool_info, indent=2)}")
        
        # Export pools again to release them
        for pool in pools:
            export_pool(pool)
            
        return None  # Success
        
    except Exception as e:
        libcalamares.utils.error(f"Pool detection failed: {str(e)}")
        return (f"Detection failed",
                f"Failed to detect ZFS pools: {str(e)}\n"
                f"Please check that the ZFS kernel modules are loaded.")

def import_all_pools() -> List[str]:
    """Import all available pools in read-only mode"""
    
    pools = []
    
    # First, check if ZFS module is loaded
    result = subprocess.run(
        ["lsmod | grep zfs"],
        shell=True,
        capture_output=True
    )
    
    if result.returncode != 0:
        # Try to load ZFS modules
        subprocess.run(["modprobe", "zfs"], capture_output=True)
    
    # Scan for importable pools
    result = subprocess.run(
        ["zpool", "import"],
        capture_output=True,
        text=True
    )
    
    # Parse output to find pool names
    for line in result.stdout.split('\n'):
        if 'pool:' in line:
            pool_name = line.split('pool:')[1].strip()
            if pool_name:
                pools.append(pool_name)
    
    # Import each pool read-only
    for pool in pools:
        import_cmd = [
            "zpool", "import",
            "-o", "readonly=on",
            "-N",  # Don't mount datasets
            pool
        ]
        subprocess.run(import_cmd, capture_output=True)
    
    return pools

def scan_pool(pool_name: str) -> Dict:
    """Scan a pool for Proxmox installations"""
    
    info = {
        'suitable_for_install': False,
        'existing_roots': [],
        'pool_status': 'unknown',
        'pool_health': 'unknown',
        'features': {},
        'properties': {}
    }
    
    # Get pool status
    status_result = subprocess.run(
        ["zpool", "status", pool_name],
        capture_output=True,
        text=True
    )
    
    if status_result.returncode == 0:
        output = status_result.stdout
        if 'ONLINE' in output:
            info['pool_status'] = 'online'
        if 'state: ' in output:
            for line in output.split('\n'):
                if 'state: ' in line:
                    info['pool_health'] = line.split('state: ')[1].strip()
    
    # Get pool properties
    props_result = subprocess.run(
        ["zpool", "get", "all", pool_name, "-H", "-o", "property,value"],
        capture_output=True,
        text=True
    )
    
    if props_result.returncode == 0:
        for line in props_result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) == 2:
                prop, value = parts
                info['properties'][prop] = value
    
    # Check for feature flags
    if 'feature@encryption' in info['properties']:
        info['features']['encryption'] = info['properties']['feature@encryption'] == 'active'
    
    # List datasets
    datasets_result = subprocess.run(
        ["zfs", "list", "-r", "-H", "-o", "name,mountpoint", pool_name],
        capture_output=True,
        text=True
    )
    
    if datasets_result.returncode == 0:
        for line in datasets_result.stdout.strip().split('\n'):
            parts = line.split('\t')
            if len(parts) == 2:
                dataset, mountpoint = parts
                
                # Check if this looks like a root dataset
                # Look for ROOT/proxmox or ROOT/pve patterns
                if '/ROOT/' in dataset or mountpoint == '/':
                    # Try to detect if it's a Proxmox installation
                    if is_proxmox_root(dataset):
                        info['existing_roots'].append({
                            'dataset': dataset,
                            'mountpoint': mountpoint,
                            'is_proxmox': True
                        })
                        info['suitable_for_install'] = True
                    else:
                        info['existing_roots'].append({
                            'dataset': dataset,
                            'mountpoint': mountpoint,
                            'is_proxmox': False
                        })
    
    # If no Proxmox found, but pool is healthy, still suitable
    if info['pool_health'] == 'ONLINE' and not info['existing_roots']:
        info['suitable_for_install'] = True
    
    return info

def is_proxmox_root(dataset: str) -> bool:
    """Check if a dataset contains Proxmox installation"""
    
    # Temporarily mount dataset to check
    temp_mount = f"/tmp/zforge_check_{dataset.replace('/', '_')}"
    
    try:
        os.makedirs(temp_mount, exist_ok=True)
        
        # Mount dataset
        mount_result = subprocess.run(
            ["mount", "-t", "zfs", dataset, temp_mount],
            capture_output=True
        )
        
        if mount_result.returncode != 0:
            return False
        
        # Check for Proxmox indicators
        proxmox_indicators = [
            f"{temp_mount}/etc/pve",
            f"{temp_mount}/usr/bin/pvecm",
            f"{temp_mount}/etc/proxmox-ve-release"
        ]
        
        is_pve = any(os.path.exists(indicator) for indicator in proxmox_indicators)
        
        # Unmount
        subprocess.run(["umount", temp_mount], capture_output=True)
        
        return is_pve
        
    except Exception:
        return False
    finally:
        # Cleanup
        try:
            os.rmdir(temp_mount)
        except:
            pass

def export_pool(pool_name: str):
    """Export a pool to release it"""
    subprocess.run(
        ["zpool", "export", pool_name],
        capture_output=True
    )

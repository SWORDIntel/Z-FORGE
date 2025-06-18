#!/usr/bin/env python3
# z-forge/builder/core/lockfile.py

"""
Build Lockfile Manager
Tracks package versions, git commits, and build state for reproducible builds
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class BuildLockfile:
    """Manages package version locking for reproducible builds"""
    
    def __init__(self, lockfile_path: Path):
        """
        Initialize lockfile manager
        
        Args:
            lockfile_path: Path where lockfile will be stored
        """
        
        self.lockfile_path = lockfile_path
        
        # Initialize or load lock data
        if lockfile_path.exists():
            self._load()
        else:
            self.lock_data = {
                'created': datetime.utcnow().isoformat(),
                'packages': {},
                'git_repos': {},
                'checksums': {},
                'modules': {}
            }
    
    def _load(self):
        """Load existing lockfile"""
        
        with open(self.lockfile_path, 'r') as f:
            self.lock_data = json.load(f)
            
        # Ensure all required sections exist
        for section in ['packages', 'git_repos', 'checksums', 'modules']:
            if section not in self.lock_data:
                self.lock_data[section] = {}
    
    def record_package_version(self, package: str, version: str):
        """
        Record exact package version used
        
        Args:
            package: Package name
            version: Package version string
        """
        
        self.lock_data['packages'][package] = {
            'version': version,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def record_git_commit(self, repo: str, commit: str, tag: Optional[str] = None):
        """
        Record git repository state
        
        Args:
            repo: Repository URL or identifier
            commit: Git commit hash
            tag: Optional git tag
        """
        
        self.lock_data['git_repos'][repo] = {
            'commit': commit,
            'tag': tag,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def record_file_checksum(self, file_path: str, algorithm: str, checksum: str):
        """
        Record file checksum
        
        Args:
            file_path: Path to the file (relative or absolute)
            algorithm: Hash algorithm used (e.g., "sha256")
            checksum: Computed checksum value
        """
        
        self.lock_data['checksums'][file_path] = {
            'algorithm': algorithm,
            'value': checksum,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def record_module_execution(self, module_name: str, result: Dict[str, Any]):
        """
        Record module execution results
        
        Args:
            module_name: Name of the executed module
            result: Module execution results
        """
        
        # Store only non-verbose information to avoid lockfile bloat
        self.lock_data['modules'][module_name] = {
            'status': result.get('status'),
            'timestamp': datetime.utcnow().isoformat(),
            'version': result.get('version', 'unknown')
        }
        
        # Store special information from certain modules
        if module_name == 'KernelAcquisition':
            self.lock_data['modules'][module_name]['kernel_version'] = result.get('kernel_version')
        elif module_name == 'ZFSBuild':
            self.lock_data['modules'][module_name]['zfs_version'] = result.get('zfs_version')
        elif module_name == 'ISOGeneration':
            self.lock_data['modules'][module_name]['iso_path'] = result.get('iso_path')
            self.lock_data['modules'][module_name]['iso_size'] = result.get('iso_size')
    
    def save(self):
        """Write lockfile to disk"""
        
        self.lock_data['last_updated'] = datetime.utcnow().isoformat()
        
        with open(self.lockfile_path, 'w') as f:
            json.dump(self.lock_data, f, indent=2)
    
    def get_package_version(self, package: str) -> Optional[str]:
        """
        Get locked package version
        
        Args:
            package: Package name to lookup
            
        Returns:
            Package version or None if not found
        """
        
        if package in self.lock_data['packages']:
            return self.lock_data['packages'][package]['version']
        return None
    
    def get_module_result(self, module_name: str) -> Optional[Dict[str, Any]]:
        """
        Get module execution result
        
        Args:
            module_name: Module name to lookup
            
        Returns:
            Module execution results or None if not found
        """
        
        if module_name in self.lock_data['modules']:
            return self.lock_data['modules'][module_name]
        return None

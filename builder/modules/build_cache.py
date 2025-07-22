#!/usr/bin/env python3
"""
Build Cache Module for Z-FORGE
Implements intelligent caching for faster build resumes
"""

import os
import json
import hashlib
import shutil
import tarfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

class BuildCache:
    """Manage build artifact caching for fast resumes"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Cache directory (outside workspace so it survives cleanup)
        self.cache_dir = Path.home() / ".cache" / "zforge"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_manifest = self.cache_dir / "manifest.json"
        self.max_cache_age_days = 7
        self.max_cache_size_gb = 10
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Initialize cache system and clean old entries"""
        try:
            self.logger.info("Initializing build cache system...")
            
            # Load cache manifest
            self._load_manifest()
            
            # Clean old/oversized cache
            cleaned = self._clean_cache()
            
            # Initialize cache for this build
            self.build_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            return {
                'status': 'success',
                'cache_dir': str(self.cache_dir),
                'cache_size_mb': self._get_cache_size_mb(),
                'entries_cleaned': cleaned,
                'build_id': self.build_id
            }
            
        except Exception as e:
            self.logger.error(f"Cache initialization failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def cache_module_output(self, module_name: str, output_paths: List[Path]) -> bool:
        """Cache the output of a module"""
        try:
            # Generate cache key based on module and config
            cache_key = self._generate_cache_key(module_name)
            cache_file = self.cache_dir / f"{cache_key}.tar.gz"
            
            self.logger.info(f"Caching {module_name} output to {cache_file.name}")
            
            # Create tarball of outputs
            with tarfile.open(cache_file, 'w:gz') as tar:
                for path in output_paths:
                    if path.exists():
                        arcname = str(path.relative_to(self.workspace))
                        tar.add(path, arcname=arcname)
            
            # Update manifest
            self.manifest[cache_key] = {
                'module': module_name,
                'timestamp': datetime.now().isoformat(),
                'size': cache_file.stat().st_size,
                'paths': [str(p.relative_to(self.workspace)) for p in output_paths],
                'config_hash': self._get_config_hash(module_name)
            }
            self._save_manifest()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache {module_name}: {e}")
            return False
    
    def restore_module_output(self, module_name: str) -> Optional[Dict]:
        """Restore cached output for a module"""
        try:
            # Check if cache exists and is valid
            cache_key = self._generate_cache_key(module_name)
            
            if cache_key not in self.manifest:
                return None
            
            cache_info = self.manifest[cache_key]
            cache_file = self.cache_dir / f"{cache_key}.tar.gz"
            
            if not cache_file.exists():
                return None
            
            # Verify config hasn't changed
            if cache_info.get('config_hash') != self._get_config_hash(module_name):
                self.logger.info(f"Cache invalid for {module_name}: configuration changed")
                return None
            
            # Check age
            timestamp = datetime.fromisoformat(cache_info['timestamp'])
            if datetime.now() - timestamp > timedelta(days=self.max_cache_age_days):
                self.logger.info(f"Cache too old for {module_name}")
                return None
            
            self.logger.info(f"Restoring {module_name} from cache")
            
            # Extract cached files
            with tarfile.open(cache_file, 'r:gz') as tar:
                tar.extractall(self.workspace)
            
            return {
                'restored': True,
                'paths': cache_info['paths'],
                'cached_at': cache_info['timestamp']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to restore cache for {module_name}: {e}")
            return None
    
    def cache_package_downloads(self, packages: List[str]) -> str:
        """Get path for caching downloaded packages"""
        # Create package cache directory
        pkg_cache = self.cache_dir / "packages"
        pkg_cache.mkdir(exist_ok=True)
        
        # APT can use this as a cache
        return str(pkg_cache)
    
    def cache_git_repos(self, repo_url: str, target_path: Path) -> bool:
        """Cache git repositories to avoid re-cloning"""
        try:
            # Generate cache key from URL
            repo_key = hashlib.md5(repo_url.encode()).hexdigest()
            repo_cache = self.cache_dir / "git" / repo_key
            
            if repo_cache.exists():
                # Update existing cache
                self.logger.info(f"Updating cached repository: {repo_url}")
                subprocess.run(
                    ['git', '-C', str(repo_cache), 'fetch', '--all'],
                    check=True,
                    capture_output=True
                )
                
                # Clone from local cache (much faster)
                subprocess.run(
                    ['git', 'clone', str(repo_cache), str(target_path)],
                    check=True,
                    capture_output=True
                )
            else:
                # Initial clone to cache
                repo_cache.parent.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Caching repository: {repo_url}")
                
                subprocess.run(
                    ['git', 'clone', '--mirror', repo_url, str(repo_cache)],
                    check=True,
                    capture_output=True
                )
                
                # Clone from cache
                subprocess.run(
                    ['git', 'clone', str(repo_cache), str(target_path)],
                    check=True,
                    capture_output=True
                )
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git cache failed: {e}")
            return False
    
    def _generate_cache_key(self, module_name: str) -> str:
        """Generate unique cache key for module"""
        # Include module name and relevant config
        key_parts = [
            module_name,
            self.config.get('builder_config', {}).get('debian_release', ''),
            self.config.get('builder_config', {}).get('kernel_version', ''),
        ]
        
        key_string = '_'.join(filter(None, key_parts))
        return hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    def _get_config_hash(self, module_name: str) -> str:
        """Get hash of module-relevant configuration"""
        # Extract config relevant to this module
        relevant_config = {
            'module': module_name,
            'builder': self.config.get('builder_config', {}),
        }
        
        # Add module-specific config
        if module_name == 'ZFSBuild':
            relevant_config['zfs'] = self.config.get('zfs_config', {})
        elif module_name == 'ProxmoxIntegration':
            relevant_config['proxmox'] = self.config.get('proxmox_config', {})
        
        config_str = json.dumps(relevant_config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _load_manifest(self):
        """Load cache manifest"""
        if self.cache_manifest.exists():
            try:
                with open(self.cache_manifest, 'r') as f:
                    self.manifest = json.load(f)
            except:
                self.manifest = {}
        else:
            self.manifest = {}
    
    def _save_manifest(self):
        """Save cache manifest"""
        with open(self.cache_manifest, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def _clean_cache(self) -> int:
        """Clean old and oversized cache entries"""
        cleaned = 0
        
        # Remove old entries
        for key, info in list(self.manifest.items()):
            try:
                timestamp = datetime.fromisoformat(info['timestamp'])
                if datetime.now() - timestamp > timedelta(days=self.max_cache_age_days):
                    cache_file = self.cache_dir / f"{key}.tar.gz"
                    if cache_file.exists():
                        cache_file.unlink()
                    del self.manifest[key]
                    cleaned += 1
            except:
                pass
        
        # Check total size
        while self._get_cache_size_mb() > self.max_cache_size_gb * 1024:
            # Remove oldest entry
            if not self.manifest:
                break
                
            oldest_key = min(
                self.manifest.keys(),
                key=lambda k: self.manifest[k].get('timestamp', '')
            )
            
            cache_file = self.cache_dir / f"{oldest_key}.tar.gz"
            if cache_file.exists():
                cache_file.unlink()
            del self.manifest[oldest_key]
            cleaned += 1
        
        if cleaned > 0:
            self._save_manifest()
            self.logger.info(f"Cleaned {cleaned} cache entries")
        
        return cleaned
    
    def _get_cache_size_mb(self) -> float:
        """Get total cache size in MB"""
        total_size = 0
        
        for item in self.cache_dir.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
        
        return total_size / (1024 * 1024)
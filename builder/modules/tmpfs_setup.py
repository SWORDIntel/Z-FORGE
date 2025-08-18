#!/usr/bin/env python3
"""
TMPFS Setup Module for Z-FORGE
Configures RAM-based filesystem for high-performance builds
"""

import os
import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, Optional, Any
import logging
import re

# Try to import psutil, but make it optional
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

class TmpfsSetup:
    """Sets up tmpfs (RAM disk) for high-performance builds"""
    
    def __init__(self, workspace: Path, config: Dict):
        """
        Initialize tmpfs setup module
        
        Args:
            workspace: Path to workspace root (will be disk fallback)
            config: Build configuration dictionary
        """
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Get tmpfs configuration
        self.tmpfs_config = config.get('tmpfs_config', {})
        self.mount_points = self.tmpfs_config.get('mount_points', [])
        
        # Default mount point from config with increased RAM allocation
        self.primary_tmpfs_path = Path(config.get('workspace_path', '/tmp/zforge_tmpfs_workspace'))
        self.fallback_path = Path(config.get('backup_workspace_path', str(workspace)))
        
        # Memory thresholds (in MB) - Reserve 8GB for system 
        self.min_free_ram_mb = 8192  # Reserve 8GB for system
        self.available_ram_mb = self._get_available_ram()
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """
        Set up tmpfs with resume capability and fallback to disk
        
        Args:
            resume_data: Optional checkpoint data to resume from
            lockfile: Optional BuildLockfile instance
            
        Returns:
            Dict with status and checkpoint information
        """
        self.logger.info("Setting up tmpfs for high-performance build...")
        
        checkpoints = {
            'memory_checked': False,
            'tmpfs_mounted': False,
            'directories_created': False,
            'fallback_prepared': False,
            'ccache_setup': False
        }
        
        # Load previous progress if resuming
        if resume_data:
            checkpoints = resume_data
            self.logger.info(f"Resuming tmpfs setup from checkpoint: {checkpoints}")
            
        try:
            if not checkpoints.get('memory_checked'):
                if not self._check_memory_requirements():
                    self.logger.warning("Insufficient RAM for tmpfs, falling back to disk")
                    return self._setup_fallback_mode(checkpoints)
                checkpoints['memory_checked'] = True
                
            if not checkpoints.get('tmpfs_mounted'):
                self._mount_tmpfs_points()
                checkpoints['tmpfs_mounted'] = True
                
            if not checkpoints.get('directories_created'):
                self._create_tmpfs_directories()
                checkpoints['directories_created'] = True
                
            if not checkpoints.get('fallback_prepared'):
                self._prepare_fallback_sync()
                checkpoints['fallback_prepared'] = True
                
            if not checkpoints.get('ccache_setup'):
                self._setup_ccache_tmpfs()
                checkpoints['ccache_setup'] = True
                
            self.logger.info(f"tmpfs setup complete. Using RAM disk at {self.primary_tmpfs_path}")
            
            return {
                'status': 'success',
                'mode': 'tmpfs',
                'primary_workspace': str(self.primary_tmpfs_path),
                'fallback_workspace': str(self.fallback_path),
                'tmpfs_mounts': [str(mp['path']) for mp in self.mount_points],
                'available_ram_mb': self.available_ram_mb,
                'module_checkpoint_data': checkpoints,
                'version': '1.0'
            }
            
        except Exception as e:
            self.logger.error(f"tmpfs setup failed: {e}")
            self.logger.warning("Falling back to disk-based build...")
            return self._setup_fallback_mode(checkpoints, error=str(e))
    
    def _get_available_ram(self) -> int:
        """Get available system RAM in MB"""
        try:
            if HAS_PSUTIL:
                return int(psutil.virtual_memory().available / (1024 * 1024))
            else:
                # Fallback to reading /proc/meminfo
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemAvailable:'):
                            # Extract KB value and convert to MB
                            kb_value = int(line.split()[1])
                            return kb_value // 1024
        except Exception as e:
            self.logger.warning(f"Could not read memory info: {e}")
            return 0
            
        return 0
        
    def _check_memory_requirements(self) -> bool:
        """Check if system has enough RAM for tmpfs"""
        total_requested_mb = 0
        
        # Calculate total tmpfs requirements
        for mount_point in self.mount_points:
            size_str = mount_point.get('size', '20G')  # Increased default to 20GB
            size_mb = self._parse_size_to_mb(size_str)
            total_requested_mb += size_mb
            
        required_ram_mb = total_requested_mb + self.min_free_ram_mb
        
        self.logger.info(f"RAM check: Available={self.available_ram_mb}MB, "
                        f"Required={required_ram_mb}MB (tmpfs={total_requested_mb}MB + reserve={self.min_free_ram_mb}MB)")
        
        if self.available_ram_mb < required_ram_mb:
            self.logger.warning(f"Insufficient RAM: need {required_ram_mb}MB, have {self.available_ram_mb}MB")
            return False
            
        return True
    
    def _parse_size_to_mb(self, size_str: str) -> int:
        """Parse size string (e.g., '20G', '2048M') to MB"""
        size_str = size_str.upper().strip()
        
        # Match number followed by optional unit
        match = re.match(r'(\d+)([KMGT]?)', size_str)
        if not match:
            self.logger.warning(f"Invalid size format: {size_str}, defaulting to 1GB")
            return 1024
            
        number, unit = match.groups()
        number = int(number)
        
        multipliers = {
            '': 1,      # Default to MB if no unit
            'K': 1/1024,  # KB to MB
            'M': 1,     # MB
            'G': 1024,  # GB to MB  
            'T': 1024*1024  # TB to MB
        }
        
        return int(number * multipliers.get(unit, 1))
    
    def _mount_tmpfs_points(self):
        """Mount all configured tmpfs points"""
        for mount_config in self.mount_points:
            mount_path = Path(mount_config['path'])
            size = mount_config.get('size', '20G')  # Increased to 20GB for main workspace
            options = mount_config.get('options', 'noatime')
            
            self.logger.info(f"Mounting tmpfs at {mount_path} with size {size}")
            
            # Create mount point directory
            subprocess.run(['sudo', 'mkdir', '-p', str(mount_path)], check=True)
            
            # Check if already mounted
            if self._is_mounted(mount_path):
                self.logger.info(f"{mount_path} already mounted")
                continue
            
            # Mount tmpfs with increased size
            mount_opts = f"size={size},{options}"
            mount_cmd = [
                'sudo', 'mount', '-t', 'tmpfs',
                '-o', mount_opts,
                'tmpfs', str(mount_path)
            ]
            
            subprocess.run(mount_cmd, check=True)
            
            # Set permissions for full access
            subprocess.run(['sudo', 'chmod', '777', str(mount_path)], check=True)
            
            self.logger.info(f"Successfully mounted tmpfs at {mount_path} with {size}")
    
    def _is_mounted(self, path: Path) -> bool:
        """Check if a path is mounted"""
        try:
            result = subprocess.run(
                ['mountpoint', '-q', str(path)],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False
    
    def _create_tmpfs_directories(self):
        """Create necessary directories in tmpfs"""
        base_dirs = [
            'temp',
            'cache', 
            'build',
            'chroot',
            'output',
            'logs',
            'debootstrap',
            'kernel_build',
            'zfs_src',
            'zfs_build',
            'proxmox_build',
            'live_build',
            'dracut',
            'zfsbootmenu',
            'bootloader',
            'calamares_build',
            'iso_build'
        ]
        
        for dir_name in base_dirs:
            dir_path = self.primary_tmpfs_path / dir_name
            subprocess.run(['sudo', 'mkdir', '-p', str(dir_path)], check=True)
            subprocess.run(['sudo', 'chmod', '777', str(dir_path)], check=True)
            
        self.logger.info(f"Created directory structure in tmpfs: {len(base_dirs)} directories")
    
    def _prepare_fallback_sync(self):
        """Prepare fallback workspace and sync points"""
        # Ensure fallback directory exists
        subprocess.run(['sudo', 'mkdir', '-p', str(self.fallback_path)], check=True)
        subprocess.run(['sudo', 'chmod', '777', str(self.fallback_path)], check=True)
        
        # Create sync directories
        sync_dirs = ['output', 'logs']
        for dir_name in sync_dirs:
            fallback_dir = self.fallback_path / dir_name
            subprocess.run(['sudo', 'mkdir', '-p', str(fallback_dir)], check=True)
            subprocess.run(['sudo', 'chmod', '777', str(fallback_dir)], check=True)
            
        self.logger.info("Prepared fallback workspace and sync directories")
    
    def _setup_ccache_tmpfs(self):
        """Set up ccache in tmpfs for compilation acceleration"""
        ccache_config = {
            'CCACHE_DIR': '/tmp/zforge_ccache',
            'CCACHE_MAXSIZE': '4G',  # Increased for better performance
            'CCACHE_COMPRESS': '1',
            'CCACHE_COMPRESS_LEVEL': '6'
        }
        
        # Create ccache directory if tmpfs mount point exists
        ccache_path = Path(ccache_config['CCACHE_DIR'])
        if any(ccache_path == Path(mp['path']) for mp in self.mount_points):
            subprocess.run(['sudo', 'mkdir', '-p', str(ccache_path)], check=True)
            subprocess.run(['sudo', 'chmod', '777', str(ccache_path)], check=True)
            
            # Set ccache configuration
            for key, value in ccache_config.items():
                os.environ[key] = value
                
            self.logger.info(f"Configured ccache in tmpfs: {ccache_path}")
        else:
            self.logger.info("No ccache tmpfs mount configured, skipping ccache setup")
    
    def _setup_fallback_mode(self, checkpoints: Dict, error: str = None) -> Dict:
        """Set up fallback mode using disk instead of tmpfs"""
        self.logger.info("Setting up fallback mode (disk-based build)")
        
        try:
            # Create workspace on disk
            subprocess.run(['sudo', 'mkdir', '-p', str(self.fallback_path)], check=True)
            subprocess.run(['sudo', 'chmod', '777', str(self.fallback_path)], check=True)
            
            # Create same directory structure as tmpfs would have
            self._create_disk_directories()
            
            # Set environment variables to use disk paths
            os.environ['TMPDIR'] = str(self.fallback_path / 'temp')
            os.environ['TEMP'] = str(self.fallback_path / 'temp')
            os.environ['TMP'] = str(self.fallback_path / 'temp')
            
            result = {
                'status': 'success',
                'mode': 'fallback_disk',
                'primary_workspace': str(self.fallback_path),
                'fallback_workspace': str(self.fallback_path),
                'reason': 'insufficient_ram' if not error else 'setup_error',
                'available_ram_mb': self.available_ram_mb,
                'module_checkpoint_data': checkpoints,
                'version': '1.0'
            }
            
            if error:
                result['setup_error'] = error
                
            return result
            
        except Exception as e:
            self.logger.error(f"Fallback setup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'mode': 'fallback_failed',
                'module_checkpoint_data': checkpoints,
                'module': self.__class__.__name__
            }
    
    def _create_disk_directories(self):
        """Create directory structure on disk (same as tmpfs)"""
        base_dirs = [
            'temp',
            'cache',
            'build', 
            'chroot',
            'output',
            'logs',
            'debootstrap',
            'kernel_build',
            'zfs_src',
            'zfs_build',
            'proxmox_build',
            'live_build',
            'dracut',
            'zfsbootmenu',
            'bootloader',
            'calamares_build',
            'iso_build'
        ]
        
        for dir_name in base_dirs:
            dir_path = self.fallback_path / dir_name
            subprocess.run(['sudo', 'mkdir', '-p', str(dir_path)], check=True)
            subprocess.run(['sudo', 'chmod', '777', str(dir_path)], check=True)
    
    def cleanup(self):
        """Cleanup tmpfs mounts"""
        try:
            self.logger.info("Cleaning up tmpfs mounts...")
            for mount_config in reversed(self.mount_points):
                mount_path = Path(mount_config['path'])
                if self._is_mounted(mount_path):
                    subprocess.run(['sudo', 'umount', str(mount_path)], check=False)
                    self.logger.info(f"Unmounted tmpfs at {mount_path}")
        except Exception as e:
            self.logger.warning(f"tmpfs cleanup error: {e}")

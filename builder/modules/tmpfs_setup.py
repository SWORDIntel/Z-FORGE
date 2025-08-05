#!/usr/bin/env python3
"""
tmpfs Setup Module for Z-FORGE
Sets up RAM-based filesystem for high-performance builds
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import psutil

class TmpfsSetup:
    """Module for setting up tmpfs (RAM-based filesystem) for builds"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.size = config.get('size', '8G')
        self.mount_point = Path(config.get('mount_point', '/tmp/zforge_tmpfs_workspace'))
        self.fallback_path = Path(config.get('fallback_path', '/home/john/zforge_workspace'))
        self.mount_options = config.get('mount_options', 'noatime,size=8G,nr_inodes=1M')
        
        # Check available RAM
        self.available_ram_gb = psutil.virtual_memory().total / (1024**3)
        
    def check_ram_availability(self) -> bool:
        """Check if system has enough RAM for tmpfs"""
        # Parse size (simple parsing for G suffix)
        if self.size.endswith('G'):
            required_gb = float(self.size[:-1])
        elif self.size.endswith('M'):
            required_gb = float(self.size[:-1]) / 1024
        else:
            # Assume bytes
            required_gb = float(self.size) / (1024**3)
            
        available_gb = self.available_ram_gb
        free_gb = psutil.virtual_memory().available / (1024**3)
        
        self.logger.info(f"System RAM: {available_gb:.1f}GB total, {free_gb:.1f}GB free")
        self.logger.info(f"Requested tmpfs size: {required_gb:.1f}GB")
        
        # Need at least 2GB free after tmpfs allocation
        if free_gb < (required_gb + 2.0):
            self.logger.warning(f"Insufficient RAM for {self.size} tmpfs. Need {required_gb + 2.0:.1f}GB free, have {free_gb:.1f}GB")
            return False
            
        return True
        
    def create_tmpfs(self) -> bool:
        """Create and mount tmpfs filesystem"""
        try:
            # Check if already mounted
            if self._is_mounted():
                self.logger.info(f"tmpfs already mounted at {self.mount_point}")
                return True
                
            # Create mount point
            self.mount_point.mkdir(parents=True, exist_ok=True)
            
            # Mount tmpfs
            mount_cmd = [
                'mount', '-t', 'tmpfs',
                '-o', self.mount_options,
                'tmpfs', str(self.mount_point)
            ]
            
            self.logger.info(f"Creating tmpfs: {' '.join(mount_cmd)}")
            result = subprocess.run(mount_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to create tmpfs: {result.stderr}")
                return False
                
            # Verify mount
            if not self._is_mounted():
                self.logger.error("tmpfs mount verification failed")
                return False
                
            # Set permissions
            os.chmod(self.mount_point, 0o755)
            
            self.logger.info(f"✅ tmpfs created successfully at {self.mount_point}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating tmpfs: {e}")
            return False
            
    def _is_mounted(self) -> bool:
        """Check if tmpfs is mounted at the specified path"""
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == str(self.mount_point) and parts[2] == 'tmpfs':
                        return True
            return False
        except Exception:
            return False
            
    def create_directory_structure(self) -> bool:
        """Create necessary subdirectories in tmpfs"""
        try:
            subdirs = [
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
            
            for subdir in subdirs:
                dir_path = self.mount_point / subdir
                dir_path.mkdir(parents=True, exist_ok=True)
                os.chmod(dir_path, 0o755)
                
            self.logger.info(f"✅ Created directory structure in tmpfs")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating directory structure: {e}")
            return False
            
    def setup_ccache(self) -> bool:
        """Set up ccache in tmpfs for faster compilation"""
        try:
            ccache_dir = Path('/tmp/zforge_ccache')
            
            # Create ccache tmpfs
            if not ccache_dir.exists():
                ccache_dir.mkdir(parents=True, exist_ok=True)
                
                # Mount ccache tmpfs
                mount_cmd = [
                    'mount', '-t', 'tmpfs',
                    '-o', 'noatime,size=2G',
                    'tmpfs', str(ccache_dir)
                ]
                
                result = subprocess.run(mount_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.warning(f"Failed to create ccache tmpfs: {result.stderr}")
                    # Continue without ccache tmpfs
                else:
                    self.logger.info("✅ ccache tmpfs created")
                    
            # Set ccache environment
            os.environ['CCACHE_DIR'] = str(ccache_dir)
            os.environ['CCACHE_MAXSIZE'] = '2G'
            os.environ['CCACHE_COMPRESS'] = '1'
            
            return True
            
        except Exception as e:
            self.logger.warning(f"ccache setup failed: {e}")
            return True  # Non-critical failure
            
    def create_backup_links(self) -> bool:
        """Create symbolic links to backup workspace for persistent data"""
        try:
            # Ensure backup workspace exists
            self.fallback_path.mkdir(parents=True, exist_ok=True)
            
            # Create persistent directories in backup location
            persistent_dirs = ['final_output', 'persistent_logs', 'package_cache']
            
            for dir_name in persistent_dirs:
                backup_dir = self.fallback_path / dir_name
                backup_dir.mkdir(exist_ok=True)
                
                # Create symlink in tmpfs
                tmpfs_link = self.mount_point / dir_name
                if not tmpfs_link.exists():
                    tmpfs_link.symlink_to(backup_dir)
                    
            self.logger.info("✅ Created backup workspace links")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating backup links: {e}")
            return False
            
    def execute(self) -> bool:
        """Main execution method"""
        self.logger.info("Setting up tmpfs for high-performance build...")
        
        # Check RAM availability
        if not self.check_ram_availability():
            self.logger.error("Insufficient RAM for tmpfs build")
            self.logger.info(f"Falling back to disk-based build at {self.fallback_path}")
            # Update config to use fallback path
            self.mount_point = self.fallback_path
            self.mount_point.mkdir(parents=True, exist_ok=True)
            return self.create_directory_structure()
            
        # Create tmpfs
        if not self.create_tmpfs():
            self.logger.error("Failed to create tmpfs, falling back to disk")
            self.mount_point = self.fallback_path
            self.mount_point.mkdir(parents=True, exist_ok=True)
            return self.create_directory_structure()
            
        # Set up directory structure
        if not self.create_directory_structure():
            return False
            
        # Set up ccache
        self.setup_ccache()
        
        # Create backup links
        self.create_backup_links()
        
        # Set environment variables for other modules
        os.environ['ZFORGE_WORKSPACE'] = str(self.mount_point)
        os.environ['TMPDIR'] = str(self.mount_point / 'temp')
        os.environ['TEMP'] = str(self.mount_point / 'temp')
        os.environ['TMP'] = str(self.mount_point / 'temp')
        
        self.logger.info(f"✅ tmpfs build environment ready at {self.mount_point}")
        
        # Log performance info
        disk_usage = shutil.disk_usage(self.mount_point)
        self.logger.info(f"tmpfs space: {disk_usage.total / (1024**3):.1f}GB total, {disk_usage.free / (1024**3):.1f}GB free")
        
        return True
        
    def cleanup(self) -> bool:
        """Cleanup tmpfs mount"""
        try:
            if self._is_mounted():
                # Sync important data first
                self._sync_important_data()
                
                # Unmount tmpfs
                subprocess.run(['umount', str(self.mount_point)], check=False)
                self.logger.info(f"tmpfs unmounted from {self.mount_point}")
                
            # Cleanup ccache tmpfs
            ccache_dir = Path('/tmp/zforge_ccache')
            if ccache_dir.exists():
                subprocess.run(['umount', str(ccache_dir)], check=False)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error during tmpfs cleanup: {e}")
            return False
            
    def _sync_important_data(self):
        """Sync important data from tmpfs to permanent storage"""
        try:
            sync_dirs = [
                ('output', 'output'),
                ('logs', 'logs'),
                ('final_output', 'output')
            ]
            
            for src_dir, dst_dir in sync_dirs:
                src_path = self.mount_point / src_dir
                dst_path = self.fallback_path / dst_dir
                
                if src_path.exists() and any(src_path.iterdir()):
                    dst_path.mkdir(parents=True, exist_ok=True)
                    
                    # Use rsync for efficient sync
                    subprocess.run([
                        'rsync', '-av', '--update',
                        f"{src_path}/", f"{dst_path}/"
                    ], check=False)
                    
                    self.logger.info(f"Synced {src_dir} to permanent storage")
                    
        except Exception as e:
            self.logger.warning(f"Error syncing data: {e}")


def main():
    """Standalone execution for testing"""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    config = {
        'size': '8G',
        'mount_point': '/tmp/zforge_tmpfs_workspace',
        'fallback_path': '/home/john/zforge_workspace'
    }
    
    tmpfs = TmpfsSetup(config)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
        tmpfs.cleanup()
    else:
        tmpfs.execute()


if __name__ == '__main__':
    main()
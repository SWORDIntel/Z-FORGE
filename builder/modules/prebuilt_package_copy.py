"""
Prebuilt Package Copy Module

Copies prebuilt packages from host to chroot for installation
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class PrebuiltPackageCopy:
    """Copy prebuilt packages into chroot"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        
        # Handle different config structures
        source_path = config.get('source', '/home/ubuntu/Documents/Z-FORGE/prebuilt_packages')
        if isinstance(source_path, dict):
            source_path = '/home/ubuntu/Documents/Z-FORGE/prebuilt_packages'
        self.source_dir = Path(str(source_path))
        
        destination_path = config.get('destination', 'prebuilt_packages')  
        if isinstance(destination_path, dict):
            destination_path = 'prebuilt_packages'
        self.destination = str(destination_path)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Copy prebuilt packages to chroot"""
        try:
            self.logger.info("Copying prebuilt packages to chroot...")
            
            # Validate source directory
            if not self.source_dir.exists():
                self.logger.error(f"Source directory not found: {self.source_dir}")
                return False
                
            # Create destination in chroot
            # Handle if destination is a Path or str
            if isinstance(self.destination, Path):
                dest_path = str(self.destination).lstrip('/')
            else:
                dest_path = self.destination.lstrip('/') if self.destination else 'prebuilt_packages'
            chroot_dest = self.chroot_path / dest_path
            chroot_dest.mkdir(parents=True, exist_ok=True)
            
            # Count packages
            total_packages = sum(1 for _ in self.source_dir.rglob("*.deb"))
            self.logger.info(f"Found {total_packages} packages to copy")
            
            # Copy package categories
            categories = ['zfs', 'kernel', 'bootloaders', 'system', 'utilities', 'calamares', 'proxmox']
            copied = 0
            
            for category in categories:
                src_cat = self.source_dir / category
                if src_cat.exists():
                    dst_cat = chroot_dest / category
                    dst_cat.mkdir(exist_ok=True)
                    
                    for pkg in src_cat.glob("*.deb"):
                        shutil.copy2(pkg, dst_cat / pkg.name)
                        copied += 1
                        
                    self.logger.info(f"Copied {len(list(src_cat.glob('*.deb')))} {category} packages")
            
            # Copy installation script
            install_script = self.source_dir / "install_in_chroot.sh"
            if install_script.exists():
                shutil.copy2(install_script, chroot_dest / "install_in_chroot.sh")
                (chroot_dest / "install_in_chroot.sh").chmod(0o755)
                self.logger.info("Copied installation script")
            
            # Copy package index
            pkg_index = self.source_dir / "PACKAGES.md"
            if pkg_index.exists():
                shutil.copy2(pkg_index, chroot_dest / "PACKAGES.md")
                
            self.logger.info(f"Successfully copied {copied} packages")
            
            # Calculate total size
            total_size = sum(f.stat().st_size for f in chroot_dest.rglob("*.deb"))
            self.logger.info(f"Total package size: {total_size / 1024 / 1024:.2f} MB")
            
            return {
                'status': 'success',
                'packages_copied': copied,
                'total_size_mb': total_size / 1024 / 1024,
                'destination': str(chroot_dest)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to copy packages: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def validate_config(self) -> bool:
        """Validate module configuration"""
        if not self.config.get('source'):
            self.logger.error("No source directory specified")
            return False
            
        if not Path(self.config['source']).exists():
            self.logger.error(f"Source directory does not exist: {self.config['source']}")
            return False
            
        return True
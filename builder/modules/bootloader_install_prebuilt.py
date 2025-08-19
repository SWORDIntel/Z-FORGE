"""
Bootloader Install Prebuilt Module

Installs prebuilt bootloader packages (ZFSBootMenu, GRUB with ZFS support)
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class BootloaderInstallPrebuilt:
    """Install prebuilt bootloader packages"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.packages_dir = self.config.get('packages_dir', 'prebuilt_packages/bootloaders')
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Install bootloader packages in chroot"""
        try:
            self.logger.info("Installing prebuilt bootloader packages...")
            
            # Check packages directory
            # packages_dir is relative to chroot
            chroot_pkg_path = self.chroot_path / self.packages_dir
            
            if not chroot_pkg_path.exists():
                self.logger.error(f"Package directory not found: {chroot_pkg_path}")
                return {'status': 'error', 'error': f'Package directory not found: {chroot_pkg_path}', 'module': self.__class__.__name__}
                
            # List available packages
            packages = list(chroot_pkg_path.glob("*.deb"))
            self.logger.info(f"Found {len(packages)} bootloader packages")
            
            if not packages:
                self.logger.warning("No bootloader packages found, skipping")
                return {'status': 'success', 'packages_installed': 0, 'note': 'No packages found'}
                
            installed_count = 0
            
            # Install ZFSBootMenu if available
            zfsbootmenu_pkgs = [p for p in packages if 'zfsbootmenu' in p.name.lower()]
            if zfsbootmenu_pkgs:
                self.logger.info("Installing ZFSBootMenu...")
                for pkg in zfsbootmenu_pkgs:
                    install_cmd = f"dpkg -i {pkg_path}/{pkg.name}"
                    if self._run_in_chroot(install_cmd):
                        installed_count += 1
                    else:
                        self.logger.warning(f"Failed to install {pkg.name}")
                        
                # Configure ZFSBootMenu
                self._configure_zfsbootmenu()
                
            # Install GRUB with ZFS support
            grub_pkgs = [p for p in packages if 'grub' in p.name.lower()]
            if grub_pkgs:
                self.logger.info("Installing GRUB packages...")
                for pkg in grub_pkgs:
                    install_cmd = f"dpkg -i {pkg_path}/{pkg.name}"
                    if self._run_in_chroot(install_cmd):
                        installed_count += 1
                    
            # Install dracut if available
            dracut_pkgs = [p for p in packages if 'dracut' in p.name.lower()]
            if dracut_pkgs:
                self.logger.info("Installing dracut...")
                for pkg in dracut_pkgs:
                    install_cmd = f"dpkg -i {pkg_path}/{pkg.name}"
                    if self._run_in_chroot(install_cmd):
                        installed_count += 1
                    
            # Fix any dependencies
            self.logger.info("Fixing dependencies...")
            self._run_in_chroot("apt-get -f install -y")
            
            # Verify installation
            verify_cmd = "which zfsbootmenu generate-zbm dracut grub-install"
            output = self._run_in_chroot_output(verify_cmd)
            
            self.logger.info(f"Bootloader packages installation completed: {installed_count} packages")
            return {
                'status': 'success',
                'packages_installed': installed_count,
                'total_packages': len(packages),
                'verification': bool(output)
            }
                
        except Exception as e:
            self.logger.error(f"Failed to install bootloader packages: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _run_in_chroot(self, command: str) -> bool:
        """Run command in chroot environment"""
        try:
            full_cmd = f"chroot {self.chroot_path} /bin/bash -c '{command}'"
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning(f"Command failed: {command}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to run command in chroot: {e}")
            return False
            
    def _run_in_chroot_output(self, command: str) -> str:
        """Run command in chroot and return output"""
        try:
            full_cmd = f"chroot {self.chroot_path} /bin/bash -c '{command}'"
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception as e:
            self.logger.error(f"Failed to run command in chroot: {e}")
            return ""
            
    def _configure_zfsbootmenu(self):
        """Configure ZFSBootMenu"""
        try:
            self.logger.info("Configuring ZFSBootMenu...")
            
            # Create config directory
            config_dir = self.chroot_path / "etc/zfsbootmenu"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create basic config
            config_content = """
# ZFSBootMenu configuration
# Generated by Z-FORGE

Global:
  ManageImages: true
  BootMountPoint: /boot/efi
  DracutConfDir: /etc/zfsbootmenu/dracut.conf.d
  PreHooksDir: /etc/zfsbootmenu/generate-zbm.pre.d
  PostHooksDir: /etc/zfsbootmenu/generate-zbm.post.d
  
Components:
  ImageDir: /boot/efi/EFI/zbm
  Versions: 3
  Enabled: true
  
Kernel:
  CommandLine: quiet loglevel=3
  
EFI:
  ImageDir: /boot/efi/EFI/zbm
  Versions: false
  Enabled: true
"""
            
            config_file = config_dir / "config.yaml"
            config_file.write_text(config_content)
            
            # Create dracut config
            dracut_dir = config_dir / "dracut.conf.d"
            dracut_dir.mkdir(exist_ok=True)
            
            dracut_config = dracut_dir / "zfsbootmenu.conf"
            dracut_config.write_text("""
# ZFSBootMenu dracut configuration
omit_dracutmodules+=" btrfs cifs nfs nbd "
add_dracutmodules+=" zfs zfsbootmenu "
""")
            
            self.logger.info("ZFSBootMenu configured")
            
        except Exception as e:
            self.logger.warning(f"Failed to configure ZFSBootMenu: {e}")
            
    def validate_config(self) -> bool:
        """Validate module configuration"""
        return True
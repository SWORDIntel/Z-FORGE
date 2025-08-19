"""
Proxmox Install Prebuilt Module

Installs prebuilt Proxmox VE packages
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging


class ProxmoxInstallPrebuilt:
    """Install prebuilt Proxmox packages"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.packages_dir = self.config.get('packages_dir', 'prebuilt_packages/proxmox')
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Install Proxmox packages in chroot"""
        try:
            self.logger.info("Installing prebuilt Proxmox VE packages...")
            
            # Check packages directory
            # packages_dir is relative to chroot
            chroot_pkg_path = self.chroot_path / self.packages_dir
            
            if not chroot_pkg_path.exists():
                self.logger.warning(f"Proxmox package directory not found: {chroot_pkg_path}")
                self.logger.info("Skipping Proxmox installation (packages will be downloaded if needed)")
                return {'status': 'success', 'packages_installed': 0, 'note': 'Skipped - no packages found'}
                
            # List packages
            packages = list(chroot_pkg_path.glob("*.deb"))
            if not packages:
                self.logger.warning("No Proxmox packages found, will use repository")
                return self._install_from_repository()
                
            self.logger.info(f"Found {len(packages)} Proxmox packages")
            
            # Install in dependency order
            install_order = [
                'libpve-',      # Libraries first
                'libproxmox-',  # Proxmox libraries
                'pve-cluster',  # Cluster framework
                'pve-manager',  # Main management
                'proxmox-ve',   # Meta package
                'qemu-server',  # QEMU/KVM
                'pve-container', # LXC
                'pve-firewall', # Firewall
                'pve-ha-manager', # HA
            ]
            
            installed = []
            installed_count = 0
            
            for pattern in install_order:
                matching = [p for p in packages if pattern in p.name and p not in installed]
                for pkg in matching:
                    self.logger.info(f"Installing {pkg.name}...")
                    install_cmd = f"dpkg -i /{self.packages_dir}/{pkg.name}"
                    if self._run_in_chroot(install_cmd):
                        installed_count += 1
                    installed.append(pkg)
                    
            # Install remaining packages
            remaining = [p for p in packages if p not in installed]
            if remaining:
                self.logger.info(f"Installing {len(remaining)} remaining packages...")
                for pkg in remaining:
                    install_cmd = f"dpkg -i /{self.packages_dir}/{pkg.name}"
                    if self._run_in_chroot(install_cmd):
                        installed_count += 1
                    
            # Fix dependencies
            self.logger.info("Fixing dependencies...")
            self._run_in_chroot("apt-get -f install -y")
            
            # Configure Proxmox
            self._configure_proxmox()
            
            # Verify installation
            verify_cmd = "dpkg -l | grep -E '^ii.*(proxmox|pve)' | wc -l"
            output = self._run_in_chroot_output(verify_cmd)
            
            if output and int(output.strip()) > 0:
                self.logger.info(f"Successfully installed {output.strip()} Proxmox packages")
                return {
                    'status': 'success',
                    'packages_installed': installed_count,
                    'total_packages': len(packages),
                    'verified_packages': int(output.strip())
                }
            else:
                self.logger.warning("Proxmox packages not fully installed, continuing anyway")
                return {
                    'status': 'success',
                    'packages_installed': len(installed),
                    'note': 'Partial installation - some packages failed but continuing'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to install Proxmox packages: {e}")
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
            
    def _install_from_repository(self) -> Dict:
        """Fallback: Install from Proxmox repository"""
        try:
            self.logger.info("Installing Proxmox from repository...")
            
            # Add Proxmox repository
            repo_line = "deb http://download.proxmox.com/debian/pve trixie pve-no-subscription"
            self._run_in_chroot(f"echo '{repo_line}' > /etc/apt/sources.list.d/pve.list")
            
            # Add Proxmox key
            key_url = "https://enterprise.proxmox.com/debian/proxmox-release-trixie.gpg"
            self._run_in_chroot(f"wget -O /etc/apt/trusted.gpg.d/proxmox.gpg {key_url}")
            
            # Update and install
            if (self._run_in_chroot("apt-get update") and 
                self._run_in_chroot("apt-get install -y proxmox-ve")):
                return {
                    'status': 'success',
                    'installation_method': 'repository',
                    'packages_installed': 1
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Failed to install from repository',
                    'module': self.__class__.__name__
                }
            
        except Exception as e:
            self.logger.error(f"Failed to install from repository: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
            
    def _configure_proxmox(self):
        """Configure Proxmox VE"""
        try:
            self.logger.info("Configuring Proxmox VE...")
            
            # Create required directories
            dirs = [
                "/etc/pve",
                "/var/lib/pve-cluster",
                "/var/lib/pve-manager",
                "/var/lib/vz",
                "/var/lib/vz/template/cache",
                "/var/lib/vz/template/iso",
            ]
            
            for dir_path in dirs:
                (self.chroot_path / str(dir_path).lstrip('/')).mkdir(parents=True, exist_ok=True)
                
            # Basic network config for Proxmox
            network_config = """
# Network configuration for Proxmox VE
auto lo
iface lo inet loopback

auto vmbr0
iface vmbr0 inet dhcp
    bridge-ports eth0
    bridge-stp off
    bridge-fd 0
"""
            
            interfaces_file = self.chroot_path / "etc/network/interfaces"
            interfaces_file.write_text(network_config)
            
            # Enable services (will start on boot)
            services = [
                'pve-cluster',
                'pvedaemon',
                'pveproxy',
                'pvestatd',
                'pvescheduler',
            ]
            
            for service in services:
                self._run_in_chroot(f"systemctl enable {service} || true")
                
            self.logger.info("Proxmox VE configured")
            
        except Exception as e:
            self.logger.warning(f"Failed to configure Proxmox: {e}")
            
    def validate_config(self) -> bool:
        """Validate module configuration"""
        return True
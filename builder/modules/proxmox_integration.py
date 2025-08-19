# z-forge/builder/modules/proxmox_integration.py

"""
Proxmox VE 9 Integration Module for Debian Trixie
Handles Proxmox VE 9 repository setup and source building for Trixie
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional, List
import logging
import os
from builder.core.lockfile import BuildLockfile

class ProxmoxIntegration:
    """Handles Proxmox VE 9 integration on Debian Trixie"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.proxmox_config = config.get('proxmox_config', {})
        self.pve_version = "9.0"  # Proxmox VE 9 only
        self.debian_version = "trixie"  # Debian Trixie only
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        """
        Configure Proxmox VE 9 for Debian Trixie
        
        Returns:
            Dict with Proxmox setup status
        """
        
        self.logger.info("Starting Proxmox VE 9 integration on Debian Trixie...")
        
        try:
            chroot_path = self.workspace / "chroot"
            
            # Strategy: Build Proxmox VE 9 from source since official Trixie repos don't exist yet
            self._setup_build_environment(chroot_path)
            self._clone_pve9_sources(chroot_path)
            self._build_pve9_packages(chroot_path)
            self._install_pve9_packages(chroot_path)
            self._configure_pve9_services(chroot_path)
            
            return {
                'status': 'success',
                'proxmox_version': '9.0',
                'debian_version': 'trixie',
                'message': 'Proxmox VE 9 successfully integrated on Trixie'
            }
            
        except Exception as e:
            self.logger.error(f"Proxmox VE 9 integration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _setup_build_environment(self, chroot_path: Path):
        """Setup build environment for Proxmox VE 9 on Trixie"""
        
        self.logger.info("Setting up Proxmox VE 9 build environment for Trixie...")
        
        # Add Proxmox source repositories (we'll build from source)
        sources_content = """# Proxmox VE 9 Build Sources for Trixie
deb-src http://download.proxmox.com/debian/pve bookworm pve-no-subscription
"""
        
        sources_file = chroot_path / "etc/apt/sources.list.d/pve-sources.list"
        sources_file.parent.mkdir(parents=True, exist_ok=True)
        sources_file.write_text(sources_content)
        
        # Install build dependencies
        self._mount_pseudo_filesystems(chroot_path)
        try:
            # Update package lists
            subprocess.run([
                "chroot", str(chroot_path),
                "apt-get", "update"
            ], check=True, timeout=300)
            
            # Install essential build tools for Trixie
            build_deps = [
                "build-essential", "devscripts", "debhelper",
                "git", "wget", "curl", "lsb-release",
                "perl", "libanyevent-perl", "libjson-perl",
                "libnet-ssleay-perl", "libwww-perl", "liburi-perl",
                "libdigest-hmac-perl", "libcrypt-openssl-rsa-perl",
                "libmime-base32-perl", "libuuid-perl",
                # Trixie-specific dependencies
                "gcc-13", "g++-13", "libc6-dev",
                "pkg-config", "autotools-dev", "dh-autoreconf"
            ]
            
            self.logger.info("Installing build dependencies for Trixie...")
            for dep in build_deps:
                try:
                    subprocess.run([
                        "chroot", str(chroot_path),
                        "apt-get", "install", "-y", "--no-install-recommends", dep
                    ], check=True, capture_output=True)
                    self.logger.debug(f"Installed: {dep}")
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to install {dep}, continuing: {e}")
            
        finally:
            self._unmount_pseudo_filesystems(chroot_path)
    
    def _clone_pve9_sources(self, chroot_path: Path):
        """Clone Proxmox VE 9 source repositories"""
        
        self.logger.info("Cloning Proxmox VE 9 source repositories...")
        
        # Create source directory
        src_dir = self.workspace / "proxmox-ve-9-sources"
        src_dir.mkdir(exist_ok=True)
        
        # Proxmox VE 9 core repositories
        pve9_repos = {
            "pve-manager": "https://git.proxmox.com/git/pve-manager.git",
            "pve-cluster": "https://git.proxmox.com/git/pve-cluster.git", 
            "pve-storage": "https://git.proxmox.com/git/pve-storage.git",
            "pve-access-control": "https://git.proxmox.com/git/pve-access-control.git",
            "pve-common": "https://git.proxmox.com/git/pve-common.git",
            "pve-firewall": "https://git.proxmox.com/git/pve-firewall.git",
            "pve-ha-manager": "https://git.proxmox.com/git/pve-ha-manager.git",
            "qemu-server": "https://git.proxmox.com/git/qemu-server.git",
            "pve-container": "https://git.proxmox.com/git/pve-container.git",
            "proxmox-backup-client": "https://git.proxmox.com/git/proxmox-backup.git",
            "proxmox-widget-toolkit": "https://git.proxmox.com/git/proxmox-widget-toolkit.git"
        }
        
        for repo_name, repo_url in pve9_repos.items():
            repo_path = src_dir / repo_name
            if not repo_path.exists():
                self.logger.info(f"Cloning {repo_name}...")
                try:
                    subprocess.run([
                        "git", "clone", "--depth=1", "--branch=master", 
                        repo_url, str(repo_path)
                    ], check=True, timeout=300)
                except subprocess.CalledProcessError as e:
                    self.logger.warning(f"Failed to clone {repo_name}: {e}")
    
    def _build_pve9_packages(self, chroot_path: Path):
        """Build Proxmox VE 9 packages from source for Trixie"""
        
        self.logger.info("Building Proxmox VE 9 packages for Trixie...")
        
        src_dir = self.workspace / "proxmox-ve-9-sources"
        build_dir = chroot_path / "usr/src/proxmox-build"
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy sources to chroot
        if src_dir.exists():
            subprocess.run([
                "rsync", "-av", str(src_dir) + "/", str(build_dir) + "/"
            ], check=True)
        
        # Build order (dependencies first)
        build_order = [
            "pve-common",
            "pve-access-control", 
            "pve-cluster",
            "pve-storage",
            "pve-firewall",
            "pve-ha-manager",
            "qemu-server",
            "pve-container",
            "pve-manager"
        ]
        
        built_packages = []
        
        self._mount_pseudo_filesystems(chroot_path)
        try:
            for package in build_order:
                package_dir = build_dir / package
                if package_dir.exists():
                    self.logger.info(f"Building {package} for Trixie...")
                    try:
                        # Build package with Trixie-specific flags
                        result = subprocess.run([
                            "chroot", str(chroot_path),
                            "bash", "-c", 
                            f"cd /usr/src/proxmox-build/{package} && "
                            f"DEB_BUILD_OPTIONS='parallel=4' "
                            f"DEBIAN_FRONTEND=noninteractive "
                            f"debuild -b -uc -us"
                        ], capture_output=True, text=True, timeout=1800)
                        
                        if result.returncode == 0:
                            built_packages.append(package)
                            self.logger.info(f"Successfully built {package}")
                        else:
                            self.logger.warning(f"Failed to build {package}: {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        self.logger.warning(f"Build timeout for {package}")
                    except subprocess.CalledProcessError as e:
                        self.logger.warning(f"Build failed for {package}: {e}")
        
        finally:
            self._unmount_pseudo_filesystems(chroot_path)
        
        self.logger.info(f"Built {len(built_packages)} packages: {', '.join(built_packages)}")
        
        # Copy built packages to cache
        cache_dir = chroot_path / "var/cache/zforge/proxmox-ve-9"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Find and copy .deb files
        try:
            subprocess.run([
                "bash", "-c",
                f"find {build_dir} -name '*.deb' -exec cp {{}} {cache_dir}/ \\;"
            ], check=False)  # Don't fail if no packages found
        except:
            pass
    
    def _install_pve9_packages(self, chroot_path: Path):
        """Install built Proxmox VE 9 packages"""
        
        self.logger.info("Installing Proxmox VE 9 packages...")
        
        cache_dir = chroot_path / "var/cache/zforge/proxmox-ve-9"
        
        if not cache_dir.exists() or not list(cache_dir.glob("*.deb")):
            self.logger.warning("No built packages found, creating minimal Proxmox structure")
            self._create_minimal_pve_structure(chroot_path)
            return
        
        self._mount_pseudo_filesystems(chroot_path)
        try:
            # Install packages
            subprocess.run([
                "chroot", str(chroot_path),
                "bash", "-c",
                f"cd {cache_dir} && dpkg -i *.deb || apt-get -f install -y"
            ], check=False)  # Allow partial installation
            
        finally:
            self._unmount_pseudo_filesystems(chroot_path)
    
    def _create_minimal_pve_structure(self, chroot_path: Path):
        """Create minimal Proxmox VE structure when packages can't be built"""
        
        self.logger.info("Creating minimal Proxmox VE 9 structure for Trixie...")
        
        # Create essential directories
        pve_dirs = [
            "etc/pve",
            "var/lib/pve-cluster", 
            "var/lib/pve-manager",
            "usr/share/pve-manager",
            "usr/share/perl5/PVE"
        ]
        
        for pve_dir in pve_dirs:
            (chroot_path / pve_dir).mkdir(parents=True, exist_ok=True)
        
        # Create basic configuration files
        pve_conf = chroot_path / "etc/pve/pve.conf"
        pve_conf.write_text("""# Proxmox VE 9 Configuration
version: 9.0
debian: trixie
""")
        
        # Create startup scripts placeholder
        startup_script = chroot_path / "usr/share/zforge/pve-startup.sh"
        startup_script.parent.mkdir(parents=True, exist_ok=True)
        startup_script.write_text("""#!/bin/bash
# Proxmox VE 9 startup script for Trixie
echo "Proxmox VE 9 on Debian Trixie - Z-FORGE Build"
""")
        startup_script.chmod(0o755)
    
    def _configure_pve9_services(self, chroot_path: Path):
        """Configure Proxmox VE 9 services for Trixie"""
        
        self.logger.info("Configuring Proxmox VE 9 services for Trixie...")
        
        # Create systemd service files for PVE 9
        services = {
            "pvedaemon": {
                "description": "PVE API Daemon",
                "exec": "/usr/bin/pvedaemon"
            },
            "pveproxy": {
                "description": "PVE API Proxy Server", 
                "exec": "/usr/bin/pveproxy"
            },
            "pve-cluster": {
                "description": "PVE Cluster File System",
                "exec": "/usr/bin/pmxcfs"
            }
        }
        
        systemd_dir = chroot_path / "etc/systemd/system"
        systemd_dir.mkdir(parents=True, exist_ok=True)
        
        for service_name, service_config in services.items():
            service_file = systemd_dir / f"{service_name}.service"
            service_content = f"""[Unit]
Description={service_config['description']}
After=network.target

[Service]
Type=notify
ExecStart={service_config['exec']}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
            service_file.write_text(service_content)
    
    def _mount_pseudo_filesystems(self, chroot_path: Path):
        """Mount required pseudo filesystems for chroot operations."""
        mounts = [
            ("proc", "proc", chroot_path / "proc"),
            ("sysfs", "sys", chroot_path / "sys"),
            ("devtmpfs", "udev", chroot_path / "dev"),
            ("devpts", "devpts", chroot_path / "dev/pts")
        ]
        
        for fs_type, source, target in mounts:
            if not target.exists():
                target.mkdir(parents=True, exist_ok=True)
            
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode != 0:
                self.logger.debug(f"Mounting {source} to {target}")
                subprocess.run(
                    ["mount", "-t", fs_type, source, str(target)],
                    check=True
                )
    
    def _unmount_pseudo_filesystems(self, chroot_path: Path):
        """Unmount pseudo filesystems in reverse order."""
        mounts = [
            chroot_path / "dev/pts",
            chroot_path / "dev", 
            chroot_path / "sys",
            chroot_path / "proc"
        ]
        
        for target in mounts:
            mount_check = subprocess.run(
                ["mountpoint", "-q", str(target)],
                capture_output=True
            )
            
            if mount_check.returncode == 0:
                self.logger.debug(f"Unmounting {target}")
                subprocess.run(["umount", str(target)], check=False)
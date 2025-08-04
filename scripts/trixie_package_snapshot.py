#!/usr/bin/env python3
"""
Trixie Package Snapshot System
Creates a stable snapshot of Trixie packages for reproducible builds
"""

import os
import sys
import subprocess
import json
import hashlib
from pathlib import Path
from datetime import datetime
import urllib.request
import gzip
import tempfile
import logging

class TrixieSnapshot:
    """Manage Trixie package snapshots for stable builds"""
    
    def __init__(self):
        self.cache_dir = Path.home() / "zforge_cache" / "trixie_snapshot"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_file = self.cache_dir / "package_snapshot.json"
        self.packages_dir = self.cache_dir / "packages"
        self.packages_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger("TrixieSnapshot")
        
    def create_snapshot(self, package_list_file: str = None):
        """Create a snapshot of current Trixie package versions"""
        self.logger.info("Creating Trixie package snapshot...")
        
        # Get list of required packages
        packages = self._get_required_packages(package_list_file)
        
        # Download package information
        self._update_package_lists()
        
        # Create snapshot with exact versions
        snapshot = {
            "created": datetime.now().isoformat(),
            "debian_release": "trixie",
            "packages": {}
        }
        
        for pkg in packages:
            version = self._get_package_version(pkg)
            if version:
                snapshot["packages"][pkg] = {
                    "version": version,
                    "url": self._get_package_url(pkg, version),
                    "hash": None  # Will be filled when downloaded
                }
                self.logger.info(f"  {pkg}: {version}")
            else:
                self.logger.warning(f"  {pkg}: NOT FOUND")
        
        # Save snapshot
        with open(self.snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        self.logger.info(f"Snapshot saved to: {self.snapshot_file}")
        return snapshot
    
    def download_snapshot_packages(self):
        """Download all packages in the snapshot"""
        if not self.snapshot_file.exists():
            self.logger.error("No snapshot found. Run create_snapshot first.")
            return False
        
        with open(self.snapshot_file, 'r') as f:
            snapshot = json.load(f)
        
        self.logger.info("Downloading snapshot packages...")
        downloaded = 0
        failed = 0
        
        for pkg_name, pkg_info in snapshot["packages"].items():
            pkg_file = self.packages_dir / f"{pkg_name}_{pkg_info['version']}_amd64.deb"
            
            if pkg_file.exists():
                self.logger.info(f"  ✓ {pkg_name} (already cached)")
                downloaded += 1
                continue
            
            if self._download_package(pkg_name, pkg_info['version'], pkg_info['url']):
                downloaded += 1
                # Update hash in snapshot
                pkg_info['hash'] = self._calculate_file_hash(pkg_file)
            else:
                failed += 1
        
        # Update snapshot with hashes
        with open(self.snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        self.logger.info(f"Download complete: {downloaded} success, {failed} failed")
        return failed == 0
    
    def _get_required_packages(self, package_list_file: str = None) -> list:
        """Get list of required packages"""
        # Core packages needed for Proxmox v9 on Trixie
        packages = [
            # Base system
            "base-files", "base-passwd", "bash", "coreutils", "dash",
            "debianutils", "diffutils", "dpkg", "e2fsprogs", "findutils",
            "grep", "gzip", "hostname", "init-system-helpers", "libc-bin",
            "login", "mount", "ncurses-base", "ncurses-bin", "passwd",
            "perl-base", "sed", "sysvinit-utils", "tar", "util-linux",
            
            # Systemd
            "systemd", "systemd-sysv", "systemd-timesyncd", "libsystemd0",
            "libudev1", "udev",
            
            # Package management
            "apt", "apt-utils", "debian-archive-keyring", "gpgv",
            
            # Networking
            "iproute2", "isc-dhcp-client", "isc-dhcp-common",
            "netbase", "network-manager", "iputils-ping",
            
            # Live system
            "live-boot", "live-boot-initramfs-tools", "live-config",
            "live-config-systemd", "user-setup",
            
            # Bootloader
            "grub-common", "grub-pc", "grub-pc-bin", "grub-efi-amd64",
            "grub-efi-amd64-bin", "grub-efi-amd64-signed", "efibootmgr",
            "mokutil", "shim-signed", "shim-unsigned",
            
            # Kernel
            "linux-image-amd64", "linux-headers-amd64",
            
            # Proxmox dependencies
            "postfix", "bridge-utils", "ifupdown2", "openssh-server",
            "chrony", "ntp", "lvm2", "thin-provisioning-tools",
            "pve-kernel-6.8", "pve-headers-6.8", "pve-firmware",
            
            # ZFS
            "zfsutils-linux", "zfs-dkms", "zfs-initramfs",
            
            # Build tools
            "debootstrap", "squashfs-tools", "xorriso", "isolinux",
            "syslinux", "syslinux-common", "mtools", "dosfstools",
        ]
        
        # Add packages from file if provided
        if package_list_file and Path(package_list_file).exists():
            with open(package_list_file, 'r') as f:
                for line in f:
                    pkg = line.strip()
                    if pkg and not pkg.startswith('#'):
                        packages.append(pkg)
        
        return sorted(list(set(packages)))
    
    def _update_package_lists(self):
        """Update local package lists from Trixie"""
        self.logger.info("Updating package lists from Trixie...")
        
        # Download Packages files
        mirrors = [
            "http://deb.debian.org/debian/dists/trixie/main/binary-amd64/Packages.gz",
            "http://deb.debian.org/debian/dists/trixie/contrib/binary-amd64/Packages.gz",
            "http://deb.debian.org/debian/dists/trixie/non-free/binary-amd64/Packages.gz",
            "http://deb.debian.org/debian/dists/trixie/non-free-firmware/binary-amd64/Packages.gz",
        ]
        
        for mirror in mirrors:
            component = mirror.split('/')[-3]
            cache_file = self.cache_dir / f"Packages_{component}.gz"
            
            try:
                urllib.request.urlretrieve(mirror, cache_file)
                self.logger.info(f"  ✓ Downloaded {component} package list")
            except Exception as e:
                self.logger.warning(f"  ✗ Failed to download {component}: {e}")
    
    def _get_package_version(self, package: str) -> str:
        """Get current version of package in Trixie"""
        # Search through all package lists
        for packages_file in self.cache_dir.glob("Packages_*.gz"):
            with gzip.open(packages_file, 'rt') as f:
                content = f.read()
                
            # Parse package entries
            for entry in content.split('\n\n'):
                if f"Package: {package}\n" in entry:
                    for line in entry.split('\n'):
                        if line.startswith("Version: "):
                            return line.split(": ", 1)[1]
        
        return None
    
    def _get_package_url(self, package: str, version: str) -> str:
        """Get download URL for package"""
        # Search through package lists for filename
        for packages_file in self.cache_dir.glob("Packages_*.gz"):
            with gzip.open(packages_file, 'rt') as f:
                content = f.read()
                
            # Parse package entries
            for entry in content.split('\n\n'):
                if f"Package: {package}\n" in entry and f"Version: {version}\n" in entry:
                    for line in entry.split('\n'):
                        if line.startswith("Filename: "):
                            filename = line.split(": ", 1)[1]
                            return f"http://deb.debian.org/debian/{filename}"
        
        return None
    
    def _download_package(self, name: str, version: str, url: str) -> bool:
        """Download a specific package"""
        if not url:
            self.logger.error(f"  ✗ {name}: No URL")
            return False
        
        pkg_file = self.packages_dir / f"{name}_{version}_amd64.deb"
        
        try:
            self.logger.info(f"  ⬇ {name} {version}")
            urllib.request.urlretrieve(url, pkg_file)
            return True
        except Exception as e:
            self.logger.error(f"  ✗ {name}: {e}")
            return False
    
    def _calculate_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def create_local_repository(self):
        """Create a local APT repository from snapshot packages"""
        self.logger.info("Creating local APT repository...")
        
        # Create repository structure
        repo_dir = self.cache_dir / "repository"
        repo_dir.mkdir(exist_ok=True)
        
        # Copy all packages
        for deb_file in self.packages_dir.glob("*.deb"):
            subprocess.run(["cp", str(deb_file), str(repo_dir)], check=True)
        
        # Generate Packages file
        os.chdir(repo_dir)
        subprocess.run(["dpkg-scanpackages", ".", "/dev/null"], 
                      stdout=open("Packages", "w"), check=True)
        subprocess.run(["gzip", "-c", "Packages"], 
                      stdout=open("Packages.gz", "wb"), check=True)
        
        # Create Release file
        release_content = f"""Origin: Z-FORGE Trixie Snapshot
Label: Z-FORGE Trixie Snapshot
Suite: trixie-snapshot
Codename: trixie-snapshot
Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S UTC')}
Architectures: amd64
Components: main
Description: Trixie package snapshot for stable builds
"""
        
        with open("Release", "w") as f:
            f.write(release_content)
        
        self.logger.info(f"Local repository created at: {repo_dir}")
        
        # Create sources.list entry
        sources_entry = f"deb [trusted=yes] file://{repo_dir} ./\n"
        sources_file = self.cache_dir / "snapshot.list"
        with open(sources_file, "w") as f:
            f.write(sources_entry)
        
        self.logger.info(f"Add this to sources.list: {sources_entry}")
        
        return repo_dir


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    snapshot = TrixieSnapshot()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            package_file = sys.argv[2] if len(sys.argv) > 2 else None
            snapshot.create_snapshot(package_file)
            
        elif command == "download":
            if snapshot.download_snapshot_packages():
                print("\n✅ All packages downloaded successfully!")
            else:
                print("\n❌ Some packages failed to download")
                sys.exit(1)
                
        elif command == "repository":
            snapshot.create_local_repository()
            
        elif command == "all":
            # Do everything
            snapshot.create_snapshot()
            if snapshot.download_snapshot_packages():
                snapshot.create_local_repository()
                print("\n✅ Trixie snapshot ready for use!")
            
    else:
        print("Usage:")
        print("  python3 trixie_package_snapshot.py create [package_list.txt]")
        print("  python3 trixie_package_snapshot.py download")
        print("  python3 trixie_package_snapshot.py repository")
        print("  python3 trixie_package_snapshot.py all")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Pre-built ZFS 2.3.3 Installer for Z-FORGE
Downloads and installs pre-built ZFS packages to avoid compilation issues
"""

import os
import sys
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import List, Dict, Optional

class PrebuiltZFSInstaller:
    def __init__(self, chroot_path: str, zfs_version: str = "2.3.3"):
        self.chroot_path = Path(chroot_path)
        self.zfs_version = zfs_version
        self.github_base_url = f"https://github.com/openzfs/zfs/releases/download/zfs-{zfs_version}"
        
    def _run_chroot_command(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run command in chroot"""
        full_cmd = ["chroot", str(self.chroot_path)] + cmd
        return subprocess.run(full_cmd, check=check, capture_output=True, text=True)
        
    def download_prebuilt_packages(self) -> Optional[Path]:
        """Download pre-built ZFS packages from GitHub releases"""
        print(f"🔄 Downloading ZFS {self.zfs_version} from GitHub releases...")
        
        temp_dir = Path(tempfile.mkdtemp())
        package_files = [
            f"zfsutils-linux_{self.zfs_version}_amd64.deb",
            f"zfs-dkms_{self.zfs_version}_all.deb",
            f"libzfs4linux_{self.zfs_version}_amd64.deb",
            f"libzpool5linux_{self.zfs_version}_amd64.deb"
        ]
        
        downloaded_files = []
        for package_file in package_files:
            url = f"{self.github_base_url}/{package_file}"
            local_path = temp_dir / package_file
            
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
                downloaded_files.append(local_path)
                print(f"✅ Downloaded: {package_file}")
                
            except requests.RequestException as e:
                print(f"⚠️  Could not download {package_file}: {e}")
                
        if downloaded_files:
            return temp_dir
        return None
        
    def build_from_source_github(self) -> bool:
        """Download source and build ZFS from GitHub release"""
        print(f"🔨 Building ZFS {self.zfs_version} from source...")
        
        temp_dir = Path(tempfile.mkdtemp())
        source_url = f"{self.github_base_url}/zfs-{self.zfs_version}.tar.gz"
        source_file = temp_dir / f"zfs-{self.zfs_version}.tar.gz"
        
        try:
            # Download source tarball
            print("📦 Downloading source tarball...")
            response = requests.get(source_url, stream=True)
            response.raise_for_status()
            
            with open(source_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            # Extract to chroot
            extract_path = self.chroot_path / "usr/src/zfs-build"
            extract_path.mkdir(parents=True, exist_ok=True)
            
            subprocess.run([
                "tar", "-xzf", str(source_file), 
                "-C", str(extract_path), 
                "--strip-components=1"
            ], check=True)
            
            # Install build dependencies
            print("🔧 Installing build dependencies...")
            build_deps = [
                "build-essential", "autoconf", "automake", "libtool", 
                "dkms", "uuid-dev", "libattr1-dev", "libblkid-dev",
                "libelf-dev", "libudev-dev", "libssl-dev", "zlib1g-dev",
                "libaio-dev", "python3-dev", "python3-setuptools"
            ]
            
            self._run_chroot_command(["apt-get", "update"])
            self._run_chroot_command(["apt-get", "install", "-y"] + build_deps)
            
            # Build ZFS
            print("🏗️  Configuring and building ZFS...")
            build_commands = [
                ["./autogen.sh"],
                ["./configure", "--prefix=/usr", "--with-config=user,kernel", "--enable-systemd"],
                ["make", "-j4"],
                ["make", "install"]
            ]
            
            for cmd in build_commands:
                result = self._run_chroot_command(cmd, check=False)
                if result.returncode != 0:
                    print(f"❌ Build failed at: {' '.join(cmd)}")
                    print(f"Error: {result.stderr}")
                    return False
                    
            print("✅ ZFS built and installed from source")
            return True
            
        except Exception as e:
            print(f"❌ Source build failed: {e}")
            return False
            
    def install_debian_packages(self) -> bool:
        """Try to install ZFS from Debian repositories with fallbacks"""
        print("📦 Attempting Debian package installation...")
        
        # Enable contrib repository
        sources_file = self.chroot_path / "etc/apt/sources.list"
        if sources_file.exists():
            with open(sources_file, 'r') as f:
                content = f.read()
            
            if 'contrib' not in content:
                content = content.replace('main', 'main contrib non-free-firmware')
                with open(sources_file, 'w') as f:
                    f.write(content)
                    
        # Add Bookworm fallback
        fallback_sources = self.chroot_path / "etc/apt/sources.list.d/zfs-fallback.list"
        with open(fallback_sources, 'w') as f:
            f.write("deb http://deb.debian.org/debian bookworm main contrib non-free-firmware\n")
            f.write("deb http://deb.debian.org/debian bookworm-backports main contrib non-free-firmware\n")
            
        self._run_chroot_command(["apt-get", "update"])
        
        # Try different package combinations
        package_attempts = [
            ["zfsutils-linux", "zfs-dkms"],
            ["zfsutils-linux", "zfs-dkms", "-t", "bookworm-backports"],
            ["zfsutils-linux", "zfs-dkms", "-t", "bookworm"],
            ["zfsutils-linux"]  # Minimal fallback
        ]
        
        for packages in package_attempts:
            try:
                cmd = ["apt-get", "install", "-y", "--no-install-recommends"] + packages
                result = self._run_chroot_command(cmd, check=False)
                if result.returncode == 0:
                    print(f"✅ Installed ZFS packages: {' '.join(packages)}")
                    return True
                else:
                    print(f"⚠️  Failed: {' '.join(packages)}")
            except Exception as e:
                print(f"⚠️  Exception installing {packages}: {e}")
                
        return False
        
    def install(self) -> bool:
        """Main installation method with multiple strategies"""
        print(f"🚀 Starting ZFS {self.zfs_version} installation...")
        
        # Strategy 1: Try pre-built packages from GitHub
        package_dir = self.download_prebuilt_packages()
        if package_dir:
            try:
                # Copy packages to chroot and install
                chroot_pkg_dir = self.chroot_path / "tmp/zfs_packages"
                chroot_pkg_dir.mkdir(exist_ok=True)
                
                for pkg_file in package_dir.glob("*.deb"):
                    subprocess.run([
                        "cp", str(pkg_file), str(chroot_pkg_dir)
                    ], check=True)
                    
                result = self._run_chroot_command([
                    "dpkg", "-i", "/tmp/zfs_packages/*.deb"
                ], check=False)
                
                if result.returncode == 0:
                    print("✅ Pre-built ZFS packages installed successfully")
                    return True
                else:
                    # Fix dependencies
                    self._run_chroot_command(["apt-get", "install", "-f", "-y"])
                    
            except Exception as e:
                print(f"⚠️  Pre-built package installation failed: {e}")
        
        # Strategy 2: Try Debian repositories
        if self.install_debian_packages():
            return True
            
        # Strategy 3: Build from source
        if self.build_from_source_github():
            return True
            
        print("❌ All ZFS installation strategies failed")
        return False

def main():
    chroot_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/zforge_workspace/chroot"
    zfs_version = sys.argv[2] if len(sys.argv) > 2 else "2.3.3"
    
    installer = PrebuiltZFSInstaller(chroot_path, zfs_version)
    
    if installer.install():
        print("🎉 ZFS installation completed successfully!")
        sys.exit(0)
    else:
        print("💥 ZFS installation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
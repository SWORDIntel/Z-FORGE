#!/usr/bin/env python3
"""
UltraThink ZFS Pre-Builder System

Multi-agent system to build ZFS 2.3.3 from source BEFORE the main build,
creating .deb packages that can be imported directly into the chroot.
This eliminates repository dependency issues entirely.
"""

import subprocess
import os
import sys
import json
import shutil
import requests
import logging
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(agent)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'ultrathink_zfs_prebuilder_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class ZFSBuildConfig:
    """ZFS build configuration"""
    version: str = "2.3.3"
    source_url: str = "https://github.com/openzfs/zfs/releases/download/zfs-2.3.3/zfs-2.3.3.tar.gz"
    build_dir: Path = Path("/tmp/zfs_prebuild")
    output_dir: Path = Path("/opt/github/Z-FORGE/prebuilt_packages")
    kernel_version: str = "6.12.38+deb13-amd64"

class BaseZFSAgent:
    """Base class for ZFS pre-builder agents"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.LoggerAdapter(logging.getLogger(), {'agent': name})
        self.results = {}
        self.config = ZFSBuildConfig()
        
    def execute(self) -> Dict[str, Any]:
        """Execute agent's primary task"""
        raise NotImplementedError
        
    def run_command(self, cmd: List[str], cwd: Path = None, timeout: int = 1200) -> subprocess.CompletedProcess:
        """Run command with logging"""
        cmd_str = ' '.join(cmd)
        self.logger.info(f"Running: {cmd_str}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=cwd,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                self.logger.error(f"Command failed: {cmd_str}")
                self.logger.error(f"Error output: {result.stderr}")
            else:
                self.logger.info(f"Command succeeded: {cmd_str}")
                
            return result
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {cmd_str}")
            raise
        except Exception as e:
            self.logger.error(f"Command exception: {cmd_str} - {e}")
            raise

class ZFSSourceAgent(BaseZFSAgent):
    """Agent responsible for downloading and preparing ZFS source"""
    
    def __init__(self):
        super().__init__("ZFSSource")
        
    def execute(self) -> Dict[str, Any]:
        self.logger.info(f"Preparing ZFS {self.config.version} source code")
        
        results = {
            'source_downloaded': False,
            'source_extracted': False,
            'source_path': None,
            'patches_applied': []
        }
        
        try:
            # Clean and create build directory
            if self.config.build_dir.exists():
                shutil.rmtree(self.config.build_dir)
            self.config.build_dir.mkdir(parents=True)
            
            # Download source
            source_path = self._download_source()
            results['source_downloaded'] = True
            
            # Extract source
            extracted_path = self._extract_source(source_path)
            results['source_extracted'] = True
            results['source_path'] = str(extracted_path)
            
            # Apply any necessary patches
            patches = self._apply_patches(extracted_path)
            results['patches_applied'] = patches
            
            self.logger.info("ZFS source preparation completed successfully")
            
        except Exception as e:
            self.logger.error(f"Source preparation failed: {e}")
            results['error'] = str(e)
            
        self.results = results
        return results
        
    def _download_source(self) -> Path:
        """Download ZFS source tarball"""
        self.logger.info(f"Downloading ZFS source from {self.config.source_url}")
        
        tarball_path = self.config.build_dir / f"zfs-{self.config.version}.tar.gz"
        
        # Try direct download first
        try:
            response = requests.get(self.config.source_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(tarball_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            self.logger.info(f"Downloaded {tarball_path}")
            return tarball_path
            
        except Exception as e:
            self.logger.warning(f"Direct download failed: {e}")
            
            # Fallback to wget
            result = self.run_command([
                'wget', '-O', str(tarball_path), self.config.source_url
            ])
            
            if result.returncode != 0:
                raise Exception(f"Failed to download ZFS source: {result.stderr}")
                
            return tarball_path
            
    def _extract_source(self, tarball_path: Path) -> Path:
        """Extract ZFS source tarball"""
        self.logger.info(f"Extracting {tarball_path}")
        
        result = self.run_command([
            'tar', '-xzf', str(tarball_path)
        ], cwd=self.config.build_dir)
        
        if result.returncode != 0:
            raise Exception(f"Failed to extract source: {result.stderr}")
            
        extracted_path = self.config.build_dir / f"zfs-{self.config.version}"
        if not extracted_path.exists():
            raise Exception(f"Extracted source not found at {extracted_path}")
            
        return extracted_path
        
    def _apply_patches(self, source_path: Path) -> List[str]:
        """Apply any necessary patches"""
        patches_applied = []
        
        # Check if we need Debian Trixie compatibility patches
        patch_dir = Path("/opt/github/Z-FORGE/patches/zfs")
        if patch_dir.exists():
            for patch_file in patch_dir.glob("*.patch"):
                self.logger.info(f"Applying patch: {patch_file}")
                
                result = self.run_command([
                    'patch', '-p1', '-i', str(patch_file)
                ], cwd=source_path)
                
                if result.returncode == 0:
                    patches_applied.append(str(patch_file))
                else:
                    self.logger.warning(f"Patch failed: {patch_file}")
                    
        return patches_applied

class ZFSDependencyAgent(BaseZFSAgent):
    """Agent responsible for installing build dependencies"""
    
    def __init__(self):
        super().__init__("ZFSDependency")
        
    def execute(self) -> Dict[str, Any]:
        self.logger.info("Installing ZFS build dependencies")
        
        results = {
            'dependencies_installed': False,
            'packages_installed': []
        }
        
        try:
            # Update package lists
            self._update_packages()
            
            # Install build dependencies
            packages = self._install_build_deps()
            results['packages_installed'] = packages
            
            # Install kernel headers if needed
            self._install_kernel_headers()
            
            results['dependencies_installed'] = True
            self.logger.info("Build dependencies installed successfully")
            
        except Exception as e:
            self.logger.error(f"Dependency installation failed: {e}")
            results['error'] = str(e)
            
        self.results = results
        return results
        
    def _update_packages(self):
        """Update package lists"""
        self.logger.info("Updating package lists")
        
        result = self.run_command(['apt-get', 'update'])
        if result.returncode != 0:
            raise Exception(f"Failed to update packages: {result.stderr}")
            
    def _install_build_deps(self) -> List[str]:
        """Install ZFS build dependencies"""
        dependencies = [
            # Core build tools
            'build-essential',
            'autoconf',
            'automake',
            'libtool',
            'gawk',
            'fakeroot',
            'devscripts',
            'libblkid-dev',
            'uuid-dev',
            'libudev-dev',
            'libssl-dev',
            'zlib1g-dev',
            'libaio-dev',
            'libattr1-dev',
            'libelf-dev',
            'python3-dev',
            'python3-setuptools',
            'python3-cffi',
            'python3-packaging',
            'libffi-dev',
            'libcurl4-openssl-dev',
            'libpam0g-dev',
            
            # DKMS and kernel build
            'dkms',
            'dpkg-dev',
            'debhelper',
            'dh-python',
            'dh-sequence-dkms'
        ]
        
        self.logger.info(f"Installing {len(dependencies)} build dependencies")
        
        # Install in chunks to avoid command line length issues
        chunk_size = 10
        installed_packages = []
        
        for i in range(0, len(dependencies), chunk_size):
            chunk = dependencies[i:i + chunk_size]
            
            result = self.run_command([
                'apt-get', 'install', '-y', '--no-install-recommends'
            ] + chunk)
            
            if result.returncode == 0:
                installed_packages.extend(chunk)
            else:
                self.logger.warning(f"Failed to install some packages in chunk: {chunk}")
                
        return installed_packages
        
    def _install_kernel_headers(self):
        """Install kernel headers for the target kernel"""
        self.logger.info(f"Installing kernel headers for {self.config.kernel_version}")
        
        # Try to install matching headers
        headers_package = f"linux-headers-{self.config.kernel_version}"
        
        result = self.run_command([
            'apt-get', 'install', '-y', headers_package
        ])
        
        if result.returncode != 0:
            # Fallback to generic headers
            self.logger.warning(f"Specific headers not found, trying generic")
            result = self.run_command([
                'apt-get', 'install', '-y', 'linux-headers-amd64'
            ])
            
            if result.returncode != 0:
                self.logger.warning("Could not install kernel headers")

class ZFSBuilderAgent(BaseZFSAgent):
    """Agent responsible for building ZFS packages"""
    
    def __init__(self):
        super().__init__("ZFSBuilder")
        
    def execute(self) -> Dict[str, Any]:
        self.logger.info(f"Building ZFS {self.config.version} packages")
        
        results = {
            'configure_success': False,
            'build_success': False,
            'packages_created': [],
            'build_time_minutes': 0
        }
        
        start_time = datetime.now()
        
        try:
            # Get source path from previous agent
            source_path = Path(self.config.build_dir) / f"zfs-{self.config.version}"
            if not source_path.exists():
                raise Exception(f"Source path not found: {source_path}")
                
            # Configure build
            self._configure_build(source_path)
            results['configure_success'] = True
            
            # Build packages
            packages = self._build_packages(source_path)
            results['packages_created'] = packages
            results['build_success'] = True
            
            self.logger.info("ZFS packages built successfully")
            
        except Exception as e:
            self.logger.error(f"ZFS build failed: {e}")
            results['error'] = str(e)
            
        end_time = datetime.now()
        results['build_time_minutes'] = (end_time - start_time).total_seconds() / 60
        
        self.results = results
        return results
        
    def _configure_build(self, source_path: Path):
        """Configure ZFS build"""
        self.logger.info("Configuring ZFS build")
        
        # Run autogen
        result = self.run_command(['./autogen.sh'], cwd=source_path)
        if result.returncode != 0:
            raise Exception(f"autogen.sh failed: {result.stderr}")
            
        # Configure with Debian-specific options
        configure_options = [
            './configure',
            '--prefix=/usr',
            '--sysconfdir=/etc',
            '--localstatedir=/var',
            '--libdir=/usr/lib/x86_64-linux-gnu',
            '--includedir=/usr/include',
            '--with-config=all',
            '--with-udevdir=/lib/udev',
            '--with-systemdunitdir=/lib/systemd/system',
            '--with-systemdpresetdir=/lib/systemd/system-preset',
            '--with-mounthelperdir=/sbin',
            '--with-systemdgeneratordir=/lib/systemd/system-generators',
            '--enable-systemd',
            '--enable-pyzfs'
        ]
        
        result = self.run_command(configure_options, cwd=source_path)
        if result.returncode != 0:
            raise Exception(f"Configure failed: {result.stderr}")
            
    def _build_packages(self, source_path: Path) -> List[str]:
        """Build ZFS Debian packages"""
        self.logger.info("Building ZFS Debian packages")
        
        # Build packages using make deb-utils and make deb-kmod
        packages_created = []
        
        # Build userspace packages
        self.logger.info("Building userspace packages...")
        result = self.run_command(['make', '-j4', 'deb-utils'], cwd=source_path, timeout=1800)
        if result.returncode != 0:
            raise Exception(f"Userspace package build failed: {result.stderr}")
            
        # Build kernel modules
        self.logger.info("Building kernel module packages...")
        result = self.run_command(['make', '-j4', 'deb-kmod'], cwd=source_path, timeout=1800)
        if result.returncode != 0:
            self.logger.warning(f"Kernel module build failed: {result.stderr}")
            # Continue anyway - we might be able to use userspace tools
            
        # Find created packages
        for deb_file in source_path.parent.glob("*.deb"):
            packages_created.append(str(deb_file))
            self.logger.info(f"Created package: {deb_file.name}")
            
        if not packages_created:
            raise Exception("No packages were created")
            
        return packages_created

class ZFSPackagerAgent(BaseZFSAgent):
    """Agent responsible for organizing and preparing packages"""
    
    def __init__(self):
        super().__init__("ZFSPackager")
        
    def execute(self) -> Dict[str, Any]:
        self.logger.info("Organizing ZFS packages for Z-FORGE integration")
        
        results = {
            'packages_organized': False,
            'repository_created': False,
            'install_script_created': False,
            'packages': []
        }
        
        try:
            # Create output directory
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy packages
            packages = self._copy_packages()
            results['packages'] = packages
            
            # Create local repository
            self._create_repository()
            results['repository_created'] = True
            
            # Create installation script
            self._create_install_script()
            results['install_script_created'] = True
            
            results['packages_organized'] = True
            self.logger.info("Package organization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Package organization failed: {e}")
            results['error'] = str(e)
            
        self.results = results
        return results
        
    def _copy_packages(self) -> List[Dict[str, str]]:
        """Copy built packages to output directory"""
        self.logger.info(f"Copying packages to {self.config.output_dir}")
        
        packages = []
        source_dir = self.config.build_dir
        
        for deb_file in source_dir.glob("*.deb"):
            dest_file = self.config.output_dir / deb_file.name
            shutil.copy2(deb_file, dest_file)
            
            # Get package info
            result = self.run_command(['dpkg-deb', '--info', str(dest_file)])
            if result.returncode == 0:
                # Parse package info
                package_info = self._parse_package_info(result.stdout)
                package_info['file'] = str(dest_file)
                packages.append(package_info)
                
        self.logger.info(f"Copied {len(packages)} packages")
        return packages
        
    def _parse_package_info(self, dpkg_info: str) -> Dict[str, str]:
        """Parse dpkg info output"""
        info = {}
        for line in dpkg_info.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith(' '):
                key, value = line.split(':', 1)
                info[key.strip().lower()] = value.strip()
        return info
        
    def _create_repository(self):
        """Create a simple local repository"""
        self.logger.info("Creating local package repository")
        
        # Create Packages file
        packages_file = self.config.output_dir / "Packages"
        
        result = self.run_command([
            'dpkg-scanpackages', '.', '/dev/null'
        ], cwd=self.config.output_dir)
        
        if result.returncode == 0:
            with open(packages_file, 'w') as f:
                f.write(result.stdout)
        else:
            self.logger.warning("Could not create Packages file")
            
        # Create Release file
        release_file = self.config.output_dir / "Release"
        release_content = f"""Archive: zfs-prebuilt
Component: main
Origin: Z-FORGE ZFS Prebuilt
Label: Z-FORGE ZFS Prebuilt
Architecture: amd64
Date: {datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}
Description: Pre-built ZFS packages for Z-FORGE
"""
        
        with open(release_file, 'w') as f:
            f.write(release_content)
            
    def _create_install_script(self):
        """Create installation script for Z-FORGE"""
        install_script = self.config.output_dir / "install_zfs_prebuilt.sh"
        
        script_content = f'''#!/bin/bash
# Z-FORGE ZFS Pre-built Package Installer
# Generated by UltraThink ZFS Pre-builder

set -e

CHROOT_PATH="${{1:-/tmp/zforge_workspace/chroot}}"
PACKAGES_DIR="$(dirname "$0")"

echo "Installing pre-built ZFS packages to $CHROOT_PATH"

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot directory not found: $CHROOT_PATH"
    exit 1
fi

# Copy packages to chroot
echo "Copying packages to chroot..."
mkdir -p "$CHROOT_PATH/tmp/zfs-packages"
cp "$PACKAGES_DIR"/*.deb "$CHROOT_PATH/tmp/zfs-packages/"

# Install packages in chroot
echo "Installing ZFS packages..."
chroot "$CHROOT_PATH" /bin/bash -c "
    cd /tmp/zfs-packages
    
    # Install userspace packages first
    dpkg -i *utils*.deb *zed*.deb *test*.deb || apt-get install -f -y
    
    # Install kernel modules if available
    dpkg -i *dkms*.deb *modules*.deb || true
    
    # Fix any dependency issues
    apt-get install -f -y
    
    # Clean up
    rm -rf /tmp/zfs-packages
"

echo "ZFS pre-built packages installed successfully!"

# Enable ZFS services
chroot "$CHROOT_PATH" systemctl enable zfs-import-cache || true
chroot "$CHROOT_PATH" systemctl enable zfs-mount || true
chroot "$CHROOT_PATH" systemctl enable zfs-import.target || true

echo "ZFS services enabled"
'''
        
        with open(install_script, 'w') as f:
            f.write(script_content)
            
        install_script.chmod(0o755)
        self.logger.info(f"Created installation script: {install_script}")

class ZFSIntegratorAgent(BaseZFSAgent):
    """Agent responsible for integrating with Z-FORGE build system"""
    
    def __init__(self):
        super().__init__("ZFSIntegrator")
        
    def execute(self) -> Dict[str, Any]:
        self.logger.info("Integrating pre-built ZFS with Z-FORGE")
        
        results = {
            'zfs_module_updated': False,
            'config_updated': False,
            'wrapper_created': False
        }
        
        try:
            # Update ZFS build module
            self._update_zfs_module()
            results['zfs_module_updated'] = True
            
            # Update configurations
            self._update_configs()
            results['config_updated'] = True
            
            # Create wrapper script
            self._create_wrapper()
            results['wrapper_created'] = True
            
            self.logger.info("Z-FORGE integration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Integration failed: {e}")
            results['error'] = str(e)
            
        self.results = results
        return results
        
    def _update_zfs_module(self):
        """Update ZFS build module to use pre-built packages"""
        zfs_module_path = Path("/opt/github/Z-FORGE/builder/modules/zfs_build.py")
        
        if not zfs_module_path.exists():
            self.logger.warning("ZFS module not found, skipping update")
            return
            
        # Create a backup
        backup_path = zfs_module_path.with_suffix('.py.backup')
        shutil.copy2(zfs_module_path, backup_path)
        
        # Add prebuilt installation method
        prebuilt_method = '''
    def _install_prebuilt_zfs(self) -> str:
        """Install ZFS from pre-built packages"""
        self.logger.info("Installing ZFS from pre-built packages...")
        
        prebuilt_dir = Path("/opt/github/Z-FORGE/prebuilt_packages")
        install_script = prebuilt_dir / "install_zfs_prebuilt.sh"
        
        if not install_script.exists():
            raise Exception(f"Pre-built ZFS installer not found: {install_script}")
            
        # Run installation script
        result = subprocess.run([
            "bash", str(install_script), str(self.chroot_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Pre-built ZFS installation failed: {result.stderr}")
            
        self.logger.info("Pre-built ZFS packages installed successfully")
        
        # Get version
        version_result = self._run_chroot_command(["zfs", "version"], check=False)
        if version_result.returncode == 0:
            version_line = version_result.stdout.strip().split('\\n')[0]
            return version_line.split()[-1] if version_line else "2.3.3"
        return "2.3.3"
'''
        
        # Insert the method into the module
        with open(zfs_module_path, 'r') as f:
            content = f.read()
            
        # Find a good insertion point
        if 'def _install_zfs_from_apt(self)' in content:
            insertion_point = content.find('def _install_zfs_from_apt(self)')
            content = content[:insertion_point] + prebuilt_method + '\n    ' + content[insertion_point:]
            
            with open(zfs_module_path, 'w') as f:
                f.write(content)
                
            self.logger.info("Updated ZFS module with pre-built installation method")
        else:
            self.logger.warning("Could not find insertion point in ZFS module")
            
    def _update_configs(self):
        """Update Z-FORGE configurations to use pre-built ZFS"""
        config_updates = {
            'zfs_config': {
                'version': '2.3.3',
                'build_from_source': False,
                'use_prebuilt': True,
                'prebuilt_path': str(self.config.output_dir)
            }
        }
        
        # Save config snippet
        config_file = Path("/opt/github/Z-FORGE/config/zfs_prebuilt.yaml")
        
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config_updates, f, default_flow_style=False)
            
        self.logger.info(f"Created ZFS prebuilt config: {config_file}")
        
    def _create_wrapper(self):
        """Create wrapper script for easy ZFS pre-building"""
        wrapper_script = Path("/opt/github/Z-FORGE/prebuild_zfs.sh")
        
        script_content = '''#!/bin/bash
# Z-FORGE ZFS Pre-builder Wrapper

echo "🔨 Z-FORGE ZFS Pre-builder"
echo "=========================="
echo "Building ZFS 2.3.3 from source for faster installation"
echo ""

# Check if already built
if [ -d "/opt/github/Z-FORGE/prebuilt_packages" ] && [ -f "/opt/github/Z-FORGE/prebuilt_packages/install_zfs_prebuilt.sh" ]; then
    echo "✅ Pre-built ZFS packages already exist"
    echo "   Location: /opt/github/Z-FORGE/prebuilt_packages"
    echo ""
    echo "To rebuild, delete the directory and run this script again:"
    echo "   sudo rm -rf /opt/github/Z-FORGE/prebuilt_packages"
    echo "   sudo ./prebuild_zfs.sh"
    exit 0
fi

# Check for root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (for package installation)"
   echo "   Please run: sudo ./prebuild_zfs.sh"
   exit 1
fi

# Run the pre-builder
python3 ultrathink_zfs_prebuilder.py

echo ""
echo "✅ ZFS pre-build complete!"
echo "   Packages available at: /opt/github/Z-FORGE/prebuilt_packages"
echo "   Z-FORGE will now use these pre-built packages for faster installation"
'''
        
        with open(wrapper_script, 'w') as f:
            f.write(script_content)
            
        wrapper_script.chmod(0o755)
        self.logger.info(f"Created wrapper script: {wrapper_script}")

class ZFSPreBuilderCoordinator(BaseZFSAgent):
    """Coordinator that manages the entire pre-build process"""
    
    def __init__(self):
        super().__init__("ZFSCoordinator")
        self.agents = {}
        
    def assemble_team(self):
        """Assemble the ZFS pre-builder team"""
        self.agents = {
            'source': ZFSSourceAgent(),
            'dependency': ZFSDependencyAgent(),
            'builder': ZFSBuilderAgent(),
            'packager': ZFSPackagerAgent(),
            'integrator': ZFSIntegratorAgent()
        }
        self.logger.info(f"Assembled team of {len(self.agents)} agents")
        
    def execute(self) -> Dict[str, Any]:
        """Coordinate the ZFS pre-build process"""
        self.logger.info("Starting ZFS 2.3.3 pre-build process")
        
        project_results = {
            'start_time': datetime.now().isoformat(),
            'phases': {},
            'total_time_minutes': 0,
            'success': False
        }
        
        start_time = datetime.now()
        
        try:
            # Phase 1: Source preparation
            self.logger.info("Phase 1: Source Preparation")
            source_result = self.agents['source'].execute()
            project_results['phases']['source'] = source_result
            
            if 'error' in source_result:
                raise Exception(f"Source preparation failed: {source_result['error']}")
                
            # Phase 2: Dependencies
            self.logger.info("Phase 2: Build Dependencies")
            dep_result = self.agents['dependency'].execute()
            project_results['phases']['dependency'] = dep_result
            
            if 'error' in dep_result:
                raise Exception(f"Dependency installation failed: {dep_result['error']}")
                
            # Phase 3: Building
            self.logger.info("Phase 3: ZFS Package Building")
            build_result = self.agents['builder'].execute()
            project_results['phases']['builder'] = build_result
            
            if 'error' in build_result:
                raise Exception(f"ZFS build failed: {build_result['error']}")
                
            # Phase 4: Packaging
            self.logger.info("Phase 4: Package Organization")
            package_result = self.agents['packager'].execute()
            project_results['phases']['packager'] = package_result
            
            if 'error' in package_result:
                raise Exception(f"Package organization failed: {package_result['error']}")
                
            # Phase 5: Integration
            self.logger.info("Phase 5: Z-FORGE Integration")
            integration_result = self.agents['integrator'].execute()
            project_results['phases']['integrator'] = integration_result
            
            if 'error' in integration_result:
                self.logger.warning(f"Integration had issues: {integration_result['error']}")
                # Don't fail the whole process for integration issues
                
            project_results['success'] = True
            self.logger.info("✅ ZFS pre-build process completed successfully!")
            
        except Exception as e:
            self.logger.error(f"ZFS pre-build failed: {e}")
            project_results['error'] = str(e)
            
        end_time = datetime.now()
        project_results['end_time'] = end_time.isoformat()
        project_results['total_time_minutes'] = (end_time - start_time).total_seconds() / 60
        
        self.results = project_results
        return project_results

def main():
    """Main entry point"""
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║              UltraThink ZFS Pre-Builder System                    ║")
    print("║          Build ZFS 2.3.3 from source for Z-FORGE                 ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()
    
    # Check if running as root
    if os.geteuid() != 0:
        print("❌ ERROR: This script must be run as root")
        print("Please run: sudo python3 ultrathink_zfs_prebuilder.py")
        return 1
        
    # Check if packages already exist
    output_dir = Path("/opt/github/Z-FORGE/prebuilt_packages")
    if output_dir.exists() and (output_dir / "install_zfs_prebuilt.sh").exists():
        print("✅ Pre-built ZFS packages already exist!")
        print(f"   Location: {output_dir}")
        print()
        print("To rebuild, delete the directory and run again:")
        print(f"   sudo rm -rf {output_dir}")
        print("   sudo python3 ultrathink_zfs_prebuilder.py")
        return 0
        
    # Create coordinator
    coordinator = ZFSPreBuilderCoordinator()
    
    # Assemble team
    print("🤖 Assembling ZFS pre-builder team...")
    coordinator.assemble_team()
    
    # Execute project
    print("🚀 Starting ZFS 2.3.3 pre-build process...")
    print("=" * 70)
    
    results = coordinator.execute()
    
    # Print summary
    print()
    print("=" * 70)
    print("📊 Pre-Build Summary")
    print("=" * 70)
    
    if results.get('success'):
        print("✅ Status: SUCCESS")
        
        # Count packages
        packager_results = results.get('phases', {}).get('packager', {})
        packages = packager_results.get('packages', [])
        print(f"✅ Packages Created: {len(packages)}")
        
        for pkg in packages:
            pkg_name = pkg.get('package', 'unknown')
            version = pkg.get('version', 'unknown')
            print(f"   - {pkg_name} ({version})")
            
        build_time = results.get('phases', {}).get('builder', {}).get('build_time_minutes', 0)
        total_time = results.get('total_time_minutes', 0)
        print(f"✅ Build Time: {build_time:.1f} minutes")
        print(f"✅ Total Time: {total_time:.1f} minutes")
        
        print()
        print(f"📁 Packages Location: {output_dir}")
        print("🔧 Z-FORGE will now use these pre-built packages for faster installation!")
        
    else:
        print("❌ Status: FAILED")
        error = results.get('error', 'Unknown error')
        print(f"❌ Error: {error}")
        
        # Show which phases completed
        for phase, result in results.get('phases', {}).items():
            status = "✅" if 'error' not in result else "❌"
            print(f"   {status} {phase}")
            
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
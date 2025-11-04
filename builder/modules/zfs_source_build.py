#!/usr/bin/env python3
"""
ZFS 2.3.3 Source Build Module for Z-FORGE
Comprehensive source-based ZFS build with hardware optimizations and DKMS integration
"""

import os
import sys
import json
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.request import urlretrieve
from urllib.error import URLError

# Add builder modules to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from builder.core.module import BaseModule

import logging
logger = logging.getLogger(__name__)

class ZFSSourceBuildModule(BaseModule):
    """
    Advanced ZFS 2.3.3 source build module with hardware optimizations,
    DKMS integration, and comprehensive error handling.
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # ZFS source configuration
        self.zfs_version = "2.3.3"
        self.zfs_url = f"https://github.com/openzfs/zfs/releases/download/zfs-{self.zfs_version}/zfs-{self.zfs_version}.tar.gz"
        self.zfs_sha256 = "30a512f34ec5c841b8b2b32cc9c1a03fd49391b26c9164d3fb30573fb5d81ac3"  # Official ZFS 2.3.3 hash
        
        # Build paths
        self.build_dir = workspace / "zfs_build"
        self.source_dir = self.build_dir / f"zfs-{self.zfs_version}"
        self.package_dir = self.build_dir / "packages"
        self.checkpoint_file = self.build_dir / "zfs_build_checkpoint.json"
        self.chroot_path = workspace / "chroot"
        
        # Hardware optimization detection
        self.cpu_info = self._detect_cpu_features()
        self.optimization_flags = self._generate_optimization_flags()
        
        # Build configuration
        self.build_type = config.get('build_type', 'release')  # debug, release, production
        self.parallel_jobs = config.get('parallel_jobs', os.cpu_count() or 4)
    
    def execute(self, resume_data: Optional[Dict[str, Any]] = None, lockfile: Optional[Any] = None) -> Dict[str, Any]:
        """Execute the ZFS source build process"""
        self.logger.info("Starting ZFS 2.3.3 source build...")
        
        try:
            # Check if already completed
            if resume_data and resume_data.get('completed', False):
                self.logger.info("ZFS source build already completed, skipping.")
                return {
                    'status': 'success',
                    'zfs_version': self.zfs_version,
                    'completed': True
                }
            
            # Execute build stages
            if not self._run_build_process():
                return {
                    'status': 'error',
                    'error': 'ZFS source build failed',
                    'module': self.__class__.__name__
                }
            
            self.logger.info("ZFS 2.3.3 source build completed successfully!")
            
            return {
                'status': 'success',
                'zfs_version': self.zfs_version,
                'build_type': self.build_type,
                'completed': True
            }
            
        except Exception as e:
            self.logger.error(f"ZFS source build failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _run_build_process(self) -> bool:
        """Run the complete ZFS build process"""
        build_stages = [
            ("Download ZFS source", self._download_zfs_source),
            ("Extract source", self._extract_source),
            ("Install build dependencies", self._install_build_dependencies),
            ("Configure build", self._configure_build),
            ("Build ZFS", self._build_zfs),
            ("Install ZFS", self._install_zfs),
            ("Validate installation", self._validate_installation)
        ]
        
        for stage_name, stage_func in build_stages:
            self.logger.info(f"Executing: {stage_name}")
            if not stage_func():
                self.logger.error(f"Failed at stage: {stage_name}")
                return False
        
        return True
    
    def _detect_cpu_features(self) -> Dict[str, bool]:
        """Detect CPU features for optimization"""
        features = {
            'avx512': False,
            'avx2': False,
            'sse4_2': False,
            'aes': False,
            'meteor_lake': False,
            'hybrid_cpu': False
        }
        
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            
            # Check for CPU features
            features['avx512'] = 'avx512f' in cpuinfo
            features['avx2'] = 'avx2' in cpuinfo
            features['sse4_2'] = 'sse4_2' in cpuinfo
            features['aes'] = 'aes' in cpuinfo
            
            # Meteor Lake detection (Intel 13th gen mobile)
            if 'Intel' in cpuinfo and any(x in cpuinfo for x in ['i5-1340', 'i7-1360', 'i7-1370']):
                features['meteor_lake'] = True
            
            # Hybrid CPU detection (P-cores + E-cores)
            cpu_count = int(subprocess.check_output(['nproc']).decode().strip())
            if cpu_count >= 12:  # Likely hybrid architecture
                features['hybrid_cpu'] = True
                
        except Exception as e:
            self.logger.warning(f"CPU feature detection failed: {e}")
            
        self.logger.info(f"Detected CPU features: {features}")
        return features
    
    def _generate_optimization_flags(self) -> List[str]:
        """Generate compiler optimization flags based on CPU features"""
        flags = [
            '-O3',
            '-march=native',
            '-mtune=native',
            '-fstack-protector-strong',
            '-fPIC',
            '-DNDEBUG'
        ]
        
        # Hardware-specific optimizations
        if self.cpu_info['avx512']:
            flags.extend(['-mavx512f', '-mavx512cd', '-mavx512vl', '-mavx512bw', '-mavx512dq'])
            self.logger.info("Enabled AVX-512 optimizations")
            
        if self.cpu_info['avx2']:
            flags.append('-mavx2')
            
        if self.cpu_info['aes']:
            flags.append('-maes')
            
        # Meteor Lake specific optimizations
        if self.cpu_info['meteor_lake']:
            flags.extend([
                '-mcpu=alderlake',
                '-mprefer-vector-width=256',
                '-fomit-frame-pointer'
            ])
            self.logger.info("Enabled Meteor Lake optimizations")
            
        # Build type specific flags
        if self.build_type == 'debug':
            flags = [f for f in flags if f not in ['-O3', '-DNDEBUG']]
            flags.extend(['-O1', '-g', '-DDEBUG'])
        elif self.build_type == 'production':
            flags.extend(['-flto', '-ffat-lto-objects'])
            
        self.logger.info(f"Generated optimization flags: {' '.join(flags)}")
        return flags
    
    def _download_zfs_source(self) -> bool:
        """Download and verify ZFS source code"""
        tarball_path = self.build_dir / f"zfs-{self.zfs_version}.tar.gz"
        
        # Check if already downloaded and valid
        if tarball_path.exists() and self._verify_sha256(tarball_path, self.zfs_sha256):
            self.logger.info("ZFS source already downloaded and verified")
            return True
        
        self.logger.info(f"Downloading ZFS {self.zfs_version} source...")
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            urlretrieve(self.zfs_url, tarball_path)
            
            # Verify download
            if not self._verify_sha256(tarball_path, self.zfs_sha256):
                raise ValueError("Downloaded file failed SHA256 verification")
                
            self.logger.info("ZFS source downloaded and verified successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download ZFS source: {e}")
            return False
    
    def _extract_source(self) -> bool:
        """Extract ZFS source code"""
        tarball_path = self.build_dir / f"zfs-{self.zfs_version}.tar.gz"
        
        if self.source_dir.exists():
            self.logger.info("ZFS source already extracted")
            return True
            
        self.logger.info("Extracting ZFS source...")
        
        try:
            subprocess.run([
                'tar', '-xzf', str(tarball_path), '-C', str(self.build_dir)
            ], check=True, capture_output=True, text=True)
            
            if not self.source_dir.exists():
                raise FileNotFoundError(f"Source directory not found: {self.source_dir}")
                
            self.logger.info("ZFS source extracted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to extract ZFS source: {e}")
            return False
    
    def _install_build_dependencies(self) -> bool:
        """Install ZFS build dependencies in chroot"""
        self.logger.info("Installing ZFS build dependencies...")
        
        packages = [
            'build-essential',
            'autoconf',
            'automake',
            'libtool',
            'gawk',
            'fakeroot',
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
            'libffi-dev',
            'dkms',
            'po-debconf',
            'debhelper',
            'dh-autoreconf',
            'dh-python'
        ]
        
        try:
            # Install in chroot
            return self._run_in_chroot(['apt-get', 'install', '-y'] + packages)
            
        except Exception as e:
            self.logger.error(f"Failed to install build dependencies: {e}")
            return False
    
    def _configure_build(self) -> bool:
        """Configure ZFS build with optimizations"""
        self.logger.info("Configuring ZFS build...")
        
        try:
            # Copy source to chroot
            chroot_source = self.chroot_path / "tmp" / f"zfs-{self.zfs_version}"
            if chroot_source.exists():
                subprocess.run(['sudo', 'rm', '-rf', str(chroot_source)], check=True)
            
            chroot_source.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['sudo', 'cp', '-r', str(self.source_dir), str(chroot_source)], check=True)
            
            # Generate configure script
            self.logger.info("Running autogen.sh...")
            if not self._run_in_chroot(['bash', '-c', f'cd /tmp/zfs-{self.zfs_version} && ./autogen.sh']):
                return False
            
            # Configure options
            configure_opts = [
                './configure',
                '--enable-systemd',
                '--with-systemdunitdir=/lib/systemd/system',
                '--with-systemdpresetdir=/lib/systemd/system-preset',
                '--with-systemdgeneratordir=/lib/systemd/system-generators',
                '--with-config=all',
                '--enable-pyzfs',
                '--with-python=python3'
            ]
            
            if self.build_type == 'debug':
                configure_opts.append('--enable-debug')
            else:
                configure_opts.append('--disable-debug')
            
            # Set optimization flags
            cflags = ' '.join(self.optimization_flags)
            configure_cmd = f'cd /tmp/zfs-{self.zfs_version} && CFLAGS="{cflags}" CXXFLAGS="{cflags}" {" ".join(configure_opts)}'
            
            self.logger.info(f"Running configure...")
            return self._run_in_chroot(['bash', '-c', configure_cmd])
            
        except Exception as e:
            self.logger.error(f"Configure failed: {e}")
            return False
    
    def _build_zfs(self) -> bool:
        """Build ZFS from source with parallel compilation"""
        self.logger.info(f"Building ZFS with {self.parallel_jobs} parallel jobs...")
        
        try:
            # Build userspace and kernel modules
            build_cmd = f'cd /tmp/zfs-{self.zfs_version} && make -j{self.parallel_jobs}'
            
            self.logger.info("Building ZFS...")
            return self._run_in_chroot(['bash', '-c', build_cmd])
            
        except Exception as e:
            self.logger.error(f"ZFS build failed: {e}")
            return False
    
    def _install_zfs(self) -> bool:
        """Install ZFS userspace utilities and kernel modules"""
        self.logger.info("Installing ZFS...")
        
        try:
            # Install userspace utilities
            install_cmd = f'cd /tmp/zfs-{self.zfs_version} && make install'
            if not self._run_in_chroot(['bash', '-c', install_cmd]):
                return False
            
            # Update library cache
            if not self._run_in_chroot(['ldconfig']):
                return False
            
            # Create ZFS directories
            zfs_dirs = [
                '/etc/zfs',
                '/etc/zfs/zfs-list.cache',
                '/etc/zfs/zed.d'
            ]
            
            for zfs_dir in zfs_dirs:
                self._run_in_chroot(['mkdir', '-p', zfs_dir], check=False)
            
            # Configure ZFS services
            self._configure_zfs_services()
            
            self.logger.info("ZFS installation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"ZFS installation failed: {e}")
            return False
    
    def _configure_zfs_services(self) -> bool:
        """Configure ZFS systemd services"""
        self.logger.info("Configuring ZFS systemd services...")
        
        services = [
            'zfs-import-cache',
            'zfs-import-scan', 
            'zfs-mount',
            'zfs-share',
            'zfs.target',
            'zfs-zed'
        ]
        
        try:
            # Enable ZFS services
            for service in services:
                self._run_in_chroot(['systemctl', 'enable', service], check=False)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"SystemD service configuration failed: {e}")
            return True  # Non-critical failure
    
    def _validate_installation(self) -> bool:
        """Validate ZFS installation"""
        self.logger.info("Validating ZFS installation...")
        
        try:
            # Check if binaries exist
            binaries = ['zpool', 'zfs']
            for binary in binaries:
                if not self._run_in_chroot(['which', binary]):
                    self.logger.error(f"ZFS binary not found: {binary}")
                    return False
            
            # Test version commands
            self._run_in_chroot(['zpool', 'version'], check=False)
            self._run_in_chroot(['zfs', 'version'], check=False)
            
            self.logger.info("ZFS installation validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"ZFS validation failed: {e}")
            return False
    
    def _run_in_chroot(self, command: List[str], check: bool = True) -> bool:
        """Run command in chroot environment"""
        try:
            # Use arch-chroot if available, otherwise regular chroot
            if subprocess.run(['which', 'arch-chroot'], capture_output=True).returncode == 0:
                full_cmd = ['sudo', 'arch-chroot', str(self.chroot_path)] + command
            else:
                full_cmd = ['sudo', 'chroot', str(self.chroot_path)] + command
            
            # Set non-interactive environment for package commands
            if command[0] in ['apt-get', 'apt', 'dpkg']:
                env = os.environ.copy()
                env['DEBIAN_FRONTEND'] = 'noninteractive'
                env['APT_LISTCHANGES_FRONTEND'] = 'none'
            else:
                env = None
            
            result = subprocess.run(full_cmd, check=check, capture_output=True, text=True, env=env)
            
            if result.stdout:
                self.logger.debug(f"Command output: {result.stdout.strip()}")
            if result.stderr:
                self.logger.debug(f"Command stderr: {result.stderr.strip()}")
                
            return result.returncode == 0
            
        except subprocess.CalledProcessError as e:
            if check:
                self.logger.error(f"Chroot command failed: {' '.join(command)}")
                self.logger.error(f"Error: {e}")
            return False
    
    def _verify_sha256(self, filepath: Path, expected_hash: str) -> bool:
        """Verify file SHA256 hash"""
        try:
            with open(filepath, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash == expected_hash
        except Exception:
            return False
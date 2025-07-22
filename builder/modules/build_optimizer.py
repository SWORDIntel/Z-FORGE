#!/usr/bin/env python3
"""
Build Optimizer Module for Z-FORGE
Optimizes build process based on build machine hardware (NOT target hardware)
"""

import os
import subprocess
import multiprocessing
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import psutil

class BuildOptimizer:
    """Optimize build process for the build machine's hardware"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.optimizations = {}
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Detect build hardware and apply optimizations"""
        try:
            self.logger.info("Detecting build machine hardware for optimization...")
            
            # Detect hardware capabilities
            hw_info = self._detect_hardware()
            
            # Apply build optimizations
            self._apply_cpu_optimizations(hw_info)
            self._apply_memory_optimizations(hw_info)
            self._apply_storage_optimizations(hw_info)
            self._apply_compiler_optimizations(hw_info)
            
            # Save optimization settings
            self._save_optimizations()
            
            return {
                'status': 'success',
                'hardware': hw_info,
                'optimizations': self.optimizations
            }
            
        except Exception as e:
            self.logger.error(f"Build optimization failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _detect_hardware(self) -> Dict:
        """Detect build machine hardware"""
        hw_info = {
            'cpu': self._detect_cpu(),
            'memory': self._detect_memory(),
            'storage': self._detect_storage(),
            'virtualization': self._detect_virtualization()
        }
        
        self.logger.info(f"Build machine: {hw_info['cpu']['count']} CPUs, "
                        f"{hw_info['memory']['total_gb']:.1f}GB RAM")
        
        return hw_info
    
    def _detect_cpu(self) -> Dict:
        """Detect CPU capabilities"""
        cpu_info = {
            'count': multiprocessing.cpu_count(),
            'model': 'Unknown',
            'features': []
        }
        
        try:
            # Get CPU model
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        cpu_info['model'] = line.split(':')[1].strip()
                        break
            
            # Detect CPU features
            cpuinfo = Path('/proc/cpuinfo').read_text()
            
            # Check for specific features
            features_to_check = {
                'aes': 'AES-NI acceleration',
                'avx2': 'AVX2 SIMD',
                'avx512': 'AVX-512 SIMD',
                'sse4_2': 'SSE4.2',
                'ssse3': 'SSSE3'
            }
            
            for feature, desc in features_to_check.items():
                if feature in cpuinfo:
                    cpu_info['features'].append(desc)
            
        except Exception as e:
            self.logger.debug(f"CPU detection error: {e}")
        
        return cpu_info
    
    def _detect_memory(self) -> Dict:
        """Detect memory configuration"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total_gb': mem.total / (1024**3),
            'available_gb': mem.available / (1024**3),
            'swap_gb': swap.total / (1024**3)
        }
    
    def _detect_storage(self) -> Dict:
        """Detect storage type and performance"""
        storage_info = {
            'type': 'HDD',  # Default
            'workspace_device': None
        }
        
        try:
            # Check if workspace is on SSD
            workspace_dev = self._get_device_for_path(self.workspace)
            if workspace_dev:
                storage_info['workspace_device'] = workspace_dev
                
                # Check if it's an SSD
                rotational_file = f"/sys/block/{workspace_dev}/queue/rotational"
                if Path(rotational_file).exists():
                    with open(rotational_file, 'r') as f:
                        if f.read().strip() == '0':
                            storage_info['type'] = 'SSD'
                
                # Check if it's NVMe
                if workspace_dev.startswith('nvme'):
                    storage_info['type'] = 'NVMe'
                    
        except Exception as e:
            self.logger.debug(f"Storage detection error: {e}")
        
        return storage_info
    
    def _detect_virtualization(self) -> Dict:
        """Detect if running in a VM"""
        virt_info = {
            'is_vm': False,
            'type': None
        }
        
        try:
            result = subprocess.run(
                ['systemd-detect-virt'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip() != 'none':
                virt_info['is_vm'] = True
                virt_info['type'] = result.stdout.strip()
                
        except:
            pass
        
        return virt_info
    
    def _apply_cpu_optimizations(self, hw_info: Dict):
        """Apply CPU-based optimizations"""
        cpu = hw_info['cpu']
        
        # Set optimal number of build jobs
        if cpu['count'] >= 8:
            # Leave 2 cores for system on high-core machines
            jobs = cpu['count'] - 2
        elif cpu['count'] >= 4:
            # Leave 1 core for system
            jobs = cpu['count'] - 1
        else:
            # Use all cores on low-core systems
            jobs = cpu['count']
        
        self.optimizations['make_jobs'] = jobs
        self.optimizations['parallel_downloads'] = min(jobs, 8)
        
        # Set compression threads
        self.optimizations['xz_threads'] = min(jobs, 4)
        self.optimizations['zstd_threads'] = jobs
        
        # Export for make
        os.environ['MAKEFLAGS'] = f'-j{jobs}'
        
        self.logger.info(f"Build parallelism: {jobs} jobs")
    
    def _apply_memory_optimizations(self, hw_info: Dict):
        """Apply memory-based optimizations"""
        mem = hw_info['memory']
        
        # Use tmpfs for build if enough RAM
        if mem['available_gb'] > 16:
            self.optimizations['use_tmpfs'] = True
            self.optimizations['tmpfs_size'] = '8G'
            self.logger.info("Using tmpfs for faster builds")
        else:
            self.optimizations['use_tmpfs'] = False
        
        # Set compiler memory limits
        if mem['total_gb'] < 4:
            # Limit compiler memory usage on low-RAM systems
            os.environ['CFLAGS'] = os.environ.get('CFLAGS', '') + ' -fno-var-tracking-assignments'
            self.optimizations['low_memory_mode'] = True
    
    def _apply_storage_optimizations(self, hw_info: Dict):
        """Apply storage-based optimizations"""
        storage = hw_info['storage']
        
        if storage['type'] == 'NVMe':
            # NVMe can handle high parallelism
            self.optimizations['io_nice'] = False
            self.optimizations['parallel_io'] = True
        elif storage['type'] == 'SSD':
            # SSD is good but not as fast as NVMe
            self.optimizations['io_nice'] = False
            self.optimizations['parallel_io'] = True
        else:
            # HDD needs more careful I/O
            self.optimizations['io_nice'] = True
            self.optimizations['parallel_io'] = False
            
            # Use ionice for HDD builds
            os.environ['IONICE'] = 'ionice -c 3'
    
    def _apply_compiler_optimizations(self, hw_info: Dict):
        """Apply compiler optimizations for build speed"""
        cpu = hw_info['cpu']
        
        # Base flags for faster compilation (not for target!)
        cflags = ['-pipe']  # Use pipes instead of temp files
        
        # Add optimization based on CPU
        if 'AVX2 SIMD' in cpu['features']:
            # Modern CPU, can use aggressive optimizations
            cflags.append('-O2')
        else:
            # Older CPU, use lighter optimization
            cflags.append('-O1')
        
        # Speed up compilation
        if hw_info['memory']['available_gb'] > 8:
            cflags.append('-fno-var-tracking')  # Saves memory and time
        
        # Set environment
        os.environ['BUILD_CFLAGS'] = ' '.join(cflags)
        self.optimizations['compiler_flags'] = cflags
        
        # Use ccache if available
        if subprocess.run(['which', 'ccache'], capture_output=True).returncode == 0:
            os.environ['CC'] = 'ccache gcc'
            os.environ['CXX'] = 'ccache g++'
            self.optimizations['ccache'] = True
            self.logger.info("Using ccache for faster rebuilds")
    
    def _get_device_for_path(self, path: Path) -> Optional[str]:
        """Get the device name for a given path"""
        try:
            # Get device number
            stat = os.stat(path)
            major = os.major(stat.st_dev)
            minor = os.minor(stat.st_dev)
            
            # Find device name
            for device in Path('/sys/block').iterdir():
                dev_file = device / 'dev'
                if dev_file.exists():
                    with open(dev_file, 'r') as f:
                        if f.read().strip() == f"{major}:{minor}":
                            return device.name
        except:
            pass
        
        return None
    
    def _save_optimizations(self):
        """Save optimization settings for other modules"""
        # Store in cache directory instead of workspace (which may not exist yet)
        cache_dir = Path.home() / ".cache" / "zforge"
        cache_dir.mkdir(parents=True, exist_ok=True)
        opt_file = cache_dir / "build_optimizations.conf"
        
        # Also save to workspace if it exists
        if self.workspace.exists():
            workspace_opt_file = self.workspace / "build_optimizations.conf"
            workspace_copy = True
        else:
            workspace_copy = False
        
        with open(opt_file, 'w') as f:
            f.write("# Build machine optimizations\n")
            f.write("# These settings are for the BUILD process only\n")
            f.write("# NOT for the target system!\n\n")
            
            for key, value in self.optimizations.items():
                f.write(f"{key}={value}\n")
        
        # Copy to workspace if it exists
        if workspace_copy:
            shutil.copy2(opt_file, workspace_opt_file)
            self.logger.info(f"Optimization settings saved to {workspace_opt_file}")
        
        self.logger.info(f"Optimization settings cached at {opt_file}")
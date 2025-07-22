#!/usr/bin/env python3
"""
ZFS Compression Optimizer Module for Z-FORGE
Dynamically selects optimal ZFS compression based on system capabilities
"""

import os
import subprocess
import multiprocessing
import psutil
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional

class ZFSCompressionOptimizer:
    """Analyzes system and selects optimal ZFS compression settings"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.chroot_path = workspace / "chroot"
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """
        Analyze system and determine optimal compression settings
        
        Returns:
            Dict with compression recommendations
        """
        try:
            self.logger.info("Analyzing system for optimal ZFS compression...")
            
            # Gather system information
            system_info = self._analyze_system()
            
            # Determine optimal compression for different use cases
            compression_map = self._determine_compression(system_info)
            
            # Update ZFS configuration
            self._update_zfs_config(compression_map)
            
            # Create tuning script
            self._create_tuning_script(compression_map, system_info)
            
            return {
                'status': 'success',
                'system_info': system_info,
                'compression_recommendations': compression_map,
                'default_compression': compression_map['default']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to optimize compression: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _analyze_system(self) -> Dict:
        """Analyze system capabilities"""
        self.logger.info("Gathering system information...")
        
        # CPU information
        cpu_count = multiprocessing.cpu_count()
        
        # Check CPU features
        cpu_features = self._check_cpu_features()
        
        # Memory information
        try:
            memory = psutil.virtual_memory()
            total_ram_gb = memory.total / (1024**3)
        except:
            # Fallback if psutil not available
            total_ram_gb = self._get_memory_fallback()
        
        # Check for hardware acceleration
        has_qat = self._check_qat_support()
        has_avx2 = 'avx2' in cpu_features
        has_avx512 = 'avx512' in cpu_features
        
        # Determine system class
        if cpu_count >= 32 and total_ram_gb >= 128:
            system_class = 'high_end'
        elif cpu_count >= 16 and total_ram_gb >= 64:
            system_class = 'server'
        elif cpu_count >= 8 and total_ram_gb >= 32:
            system_class = 'workstation'
        elif cpu_count >= 4 and total_ram_gb >= 16:
            system_class = 'desktop'
        else:
            system_class = 'basic'
        
        system_info = {
            'cpu_count': cpu_count,
            'total_ram_gb': total_ram_gb,
            'cpu_features': cpu_features,
            'has_qat': has_qat,
            'has_avx2': has_avx2,
            'has_avx512': has_avx512,
            'system_class': system_class
        }
        
        self.logger.info(f"System analysis: {system_class} class, {cpu_count} CPUs, {total_ram_gb:.1f}GB RAM")
        self.logger.info(f"Hardware features: AVX2={has_avx2}, AVX512={has_avx512}, QAT={has_qat}")
        
        return system_info
    
    def _check_cpu_features(self) -> set:
        """Check CPU features from /proc/cpuinfo"""
        features = set()
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('flags'):
                        flags = line.split(':')[1].strip().split()
                        features.update(flags)
                        break
        except:
            self.logger.warning("Could not read CPU features")
        
        return features
    
    def _check_qat_support(self) -> bool:
        """Check for Intel QuickAssist Technology"""
        try:
            # Check for QAT devices
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            if 'QuickAssist' in result.stdout or 'QAT' in result.stdout:
                return True
            
            # Check for QAT kernel module
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            if 'qat' in result.stdout:
                return True
        except:
            pass
        
        return False
    
    def _get_memory_fallback(self) -> float:
        """Get memory info without psutil"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_kb = int(line.split()[1])
                        return mem_kb / (1024**2)  # Convert to GB
        except:
            return 16.0  # Default fallback
    
    def _determine_compression(self, system_info: Dict) -> Dict:
        """Determine optimal compression settings based on system capabilities"""
        self.logger.info("Determining optimal compression settings...")
        
        compression_map = {}
        system_class = system_info['system_class']
        
        # Default compression (minimum zstd-3 as requested)
        if system_class == 'high_end':
            # High-end systems can handle higher compression
            default = 'zstd-5'
            if system_info['has_avx512']:
                default = 'zstd-6'
        elif system_class == 'server':
            default = 'zstd-4'
            if system_info['has_avx2']:
                default = 'zstd-5'
        elif system_class == 'workstation':
            default = 'zstd-3'
            if system_info['has_avx2']:
                default = 'zstd-4'
        else:
            # Basic systems still get zstd-3 minimum
            default = 'zstd-3'
        
        compression_map['default'] = default
        
        # Purpose-specific compression
        # OS datasets - balance between speed and compression
        compression_map['os'] = 'zstd-3'  # Fast for system responsiveness
        
        # VM storage - moderate compression
        if system_class in ['high_end', 'server']:
            compression_map['vm_storage'] = 'zstd-4'
        else:
            compression_map['vm_storage'] = 'zstd-3'
        
        # Backup storage - maximum compression
        if system_class == 'high_end':
            compression_map['backup'] = 'zstd-9'
        elif system_class == 'server':
            compression_map['backup'] = 'zstd-7'
        else:
            compression_map['backup'] = 'zstd-5'
        
        # Media storage - light compression
        compression_map['media'] = 'zstd-1'  # Media files are usually already compressed
        
        # Database storage - balanced
        compression_map['database'] = 'zstd-3'
        
        # Logs and archives - high compression
        compression_map['logs'] = 'zstd-6'
        compression_map['archives'] = 'zstd-7'
        
        # Check if QAT acceleration is available
        if system_info['has_qat']:
            self.logger.info("QAT acceleration detected - enabling QAT compression")
            compression_map['qat_enabled'] = True
            # QAT works best with specific algorithms
            compression_map['qat_default'] = 'gzip-9'
        
        self.logger.info(f"Recommended default compression: {default}")
        
        return compression_map
    
    def _update_zfs_config(self, compression_map: Dict):
        """Update ZFS configuration with optimal compression settings"""
        config_file = self.workspace / "config" / "zfs_compression.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(config_file, 'w') as f:
            json.dump(compression_map, f, indent=2)
        
        self.logger.info(f"Saved compression configuration to {config_file}")
    
    def _create_tuning_script(self, compression_map: Dict, system_info: Dict):
        """Create script to apply compression settings"""
        script_path = self.chroot_path / "usr" / "local" / "bin" / "zfs-compression-tune.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        script_content = f"""#!/bin/bash
# ZFS Compression Tuning Script
# Generated by Z-FORGE based on system analysis

# System Profile: {system_info['system_class']}
# CPUs: {system_info['cpu_count']}, RAM: {system_info['total_ram_gb']:.1f}GB
# Default Compression: {compression_map['default']}

echo "Applying ZFS compression settings..."

# Function to set compression on a dataset
set_compression() {{
    local dataset=$1
    local compression=$2
    
    if zfs list "$dataset" >/dev/null 2>&1; then
        echo "Setting compression=$compression on $dataset"
        zfs set compression="$compression" "$dataset"
    fi
}}

# Default compression for new datasets
DEFAULT_COMPRESSION="{compression_map['default']}"

# Apply compression based on dataset purpose
# OS datasets
set_compression "rpool/ROOT" "{compression_map['os']}"
set_compression "rpool/var" "{compression_map['os']}"

# Storage pool datasets (if they exist)
set_compression "tank/vms" "{compression_map['vm_storage']}"
set_compression "tank/backup" "{compression_map['backup']}"
set_compression "tank/media" "{compression_map['media']}"
set_compression "tank/database" "{compression_map['database']}"
set_compression "tank/logs" "{compression_map['logs']}"
set_compression "tank/archives" "{compression_map['archives']}"

# Set default for pools
for pool in $(zpool list -H -o name); do
    echo "Setting default compression=$DEFAULT_COMPRESSION on $pool"
    zfs set compression="$DEFAULT_COMPRESSION" "$pool"
done

"""
        
        # Add QAT configuration if available
        if compression_map.get('qat_enabled'):
            script_content += """
# Enable QAT acceleration
if [ -e /sys/module/zfs/parameters/zfs_qat_compress_disable ]; then
    echo 0 > /sys/module/zfs/parameters/zfs_qat_compress_disable
    echo "QAT compression acceleration enabled"
fi

if [ -e /sys/module/zfs/parameters/zfs_qat_checksum_disable ]; then
    echo 0 > /sys/module/zfs/parameters/zfs_qat_checksum_disable
    echo "QAT checksum acceleration enabled"
fi
"""
        
        # Add AVX acceleration settings based on CPU features
        if system_info['has_avx512']:
            script_content += """
# Enable AVX-512 optimizations
if [ -e /sys/module/zfs/parameters/zfs_avx512_available ]; then
    echo 1 > /sys/module/zfs/parameters/zfs_avx512_available
fi
"""
        elif system_info['has_avx2']:
            script_content += """
# Enable AVX2 optimizations
if [ -e /sys/module/zfs/parameters/zfs_avx2_available ]; then
    echo 1 > /sys/module/zfs/parameters/zfs_avx2_available
fi
"""
        
        script_content += """
echo "ZFS compression tuning complete!"
echo "Current compression settings:"
zfs get -H -o name,value compression | grep -v "@"
"""
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        self.logger.info(f"Created compression tuning script at {script_path}")
        
        # Also create a systemd service to apply settings at boot
        self._create_systemd_service()
    
    def _create_systemd_service(self):
        """Create systemd service for compression tuning"""
        service_path = self.chroot_path / "etc" / "systemd" / "system" / "zfs-compression-tune.service"
        service_path.parent.mkdir(parents=True, exist_ok=True)
        
        service_content = """[Unit]
Description=ZFS Compression Tuning
After=zfs.target
Before=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/zfs-compression-tune.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
        
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        # Enable the service
        try:
            subprocess.run(
                ["chroot", str(self.chroot_path), "systemctl", "enable", "zfs-compression-tune.service"],
                check=False
            )
        except:
            pass
        
        self.logger.info("Created systemd service for compression tuning")
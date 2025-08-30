#!/usr/bin/env python3
"""
Enterprise Server Hardware Detection System for Z-FORGE
Specialized for Dell PowerEdge servers with Mellanox networking

This module provides comprehensive hardware detection optimized for:
- Dell PowerEdge R750, R7525, R740, R730XD series
- Mellanox ConnectX-6/7 network adapters  
- Enterprise storage controllers (PERC, LSI MegaRAID)
- Server-grade GPUs (Tesla, Instinct)
- Intel Xeon and AMD EPYC processors
"""

import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class EnterpriseHardwareProfile:
    """Enterprise hardware profile for server-grade systems"""
    server_model: str
    cpu_model: str
    cpu_cores: int
    memory_gb: int
    storage_controllers: List[str]
    network_adapters: List[str]
    gpus: List[str]
    chassis_type: str
    idrac_version: str
    power_supplies: int
    optimization_flags: Dict[str, Any]

class EnterpriseHardwareDetector:
    """
    Advanced hardware detection system for enterprise servers
    
    Focuses on server-grade components with performance optimization:
    - Dell PowerEdge series detection
    - Mellanox high-performance networking
    - Enterprise RAID controllers
    - Server GPU acceleration
    - Memory topology optimization
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.detected_hardware: Optional[EnterpriseHardwareProfile] = None
        
        # Enterprise hardware vendor mappings
        self.dell_server_models = {
            'PowerEdge R750': {'cores': 32, 'memory': 512, 'type': 'rack'},
            'PowerEdge R7525': {'cores': 64, 'memory': 1024, 'type': 'rack'},  
            'PowerEdge R740': {'cores': 28, 'memory': 384, 'type': 'rack'},
            'PowerEdge R730XD': {'cores': 24, 'memory': 256, 'type': 'storage'},
            'PowerEdge R6525': {'cores': 32, 'memory': 512, 'type': 'rack'},
            'PowerEdge T640': {'cores': 20, 'memory': 128, 'type': 'tower'}
        }
        
        self.mellanox_adapters = {
            'ConnectX-6': {'speed': '100Gb', 'ports': 2, 'features': ['RoCE', 'SR-IOV']},
            'ConnectX-7': {'speed': '200Gb', 'ports': 2, 'features': ['RoCE', 'SR-IOV', 'GPUDirect']},
            'ConnectX-5': {'speed': '50Gb', 'ports': 2, 'features': ['RoCE', 'SR-IOV']},
            'ConnectX-4': {'speed': '25Gb', 'ports': 2, 'features': ['RoCE']}
        }
        
        self.enterprise_storage = {
            'PERC H755': {'type': 'SAS', 'raid': [0, 1, 5, 6, 10, 50, 60], 'nvme': True},
            'PERC H740P': {'type': 'SAS', 'raid': [0, 1, 5, 6, 10, 50, 60], 'nvme': True},
            'PERC H730': {'type': 'SAS', 'raid': [0, 1, 5, 6, 10, 50, 60], 'nvme': False},
            'LSI 9361': {'type': 'SAS', 'raid': [0, 1, 5, 6, 10, 50, 60], 'nvme': False},
            'LSI 9440': {'type': 'SAS', 'raid': [0, 1, 5, 6, 10, 50, 60], 'nvme': True}
        }
        
    def detect_enterprise_hardware(self) -> EnterpriseHardwareProfile:
        """
        Comprehensive enterprise server hardware detection
        
        Returns:
            EnterpriseHardwareProfile with complete server specifications
        """
        self.logger.info("Starting enterprise server hardware detection...")
        
        # Detect server model and chassis
        server_model = self._detect_dell_server_model()
        chassis_type = self._detect_chassis_type()
        
        # CPU and memory detection
        cpu_info = self._detect_enterprise_cpu()
        memory_info = self._detect_enterprise_memory()
        
        # Storage controllers
        storage_controllers = self._detect_storage_controllers()
        
        # Network adapters (focus on Mellanox)
        network_adapters = self._detect_mellanox_adapters()
        
        # Enterprise GPUs
        gpus = self._detect_enterprise_gpus()
        
        # Management interface
        idrac_version = self._detect_idrac_version()
        
        # Power and cooling
        power_supplies = self._detect_power_supplies()
        
        # Generate optimization flags
        optimization_flags = self._generate_optimization_flags({
            'server_model': server_model,
            'cpu_info': cpu_info,
            'memory_info': memory_info,
            'storage_controllers': storage_controllers,
            'network_adapters': network_adapters
        })
        
        self.detected_hardware = EnterpriseHardwareProfile(
            server_model=server_model,
            cpu_model=cpu_info.get('model', 'Unknown'),
            cpu_cores=cpu_info.get('cores', 0),
            memory_gb=memory_info.get('total_gb', 0),
            storage_controllers=storage_controllers,
            network_adapters=network_adapters,
            gpus=gpus,
            chassis_type=chassis_type,
            idrac_version=idrac_version,
            power_supplies=power_supplies,
            optimization_flags=optimization_flags
        )
        
        self.logger.info(f"Detected enterprise server: {server_model}")
        self.logger.info(f"CPU: {cpu_info.get('model', 'Unknown')} ({cpu_info.get('cores', 0)} cores)")
        self.logger.info(f"Memory: {memory_info.get('total_gb', 0)}GB")
        self.logger.info(f"Storage Controllers: {', '.join(storage_controllers)}")
        self.logger.info(f"Network Adapters: {', '.join(network_adapters)}")
        
        return self.detected_hardware
        
    def _detect_dell_server_model(self) -> str:
        """Detect Dell PowerEdge server model using DMI"""
        try:
            result = subprocess.run(['dmidecode', '-s', 'system-product-name'], 
                                  capture_output=True, text=True, check=True)
            product_name = result.stdout.strip()
            
            # Match against known Dell PowerEdge models
            for model_name in self.dell_server_models.keys():
                if model_name.lower() in product_name.lower():
                    return model_name
                    
            # Generic Dell detection
            if 'poweredge' in product_name.lower():
                return f"Dell {product_name}"
                
            return "Unknown Dell Server"
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("Could not detect Dell server model")
            return "Unknown Server"
    
    def _detect_chassis_type(self) -> str:
        """Detect server chassis type (rack/tower/blade)"""
        try:
            result = subprocess.run(['dmidecode', '-s', 'chassis-type'], 
                                  capture_output=True, text=True, check=True)
            chassis_type = result.stdout.strip().lower()
            
            chassis_mapping = {
                'rack mount chassis': 'rack',
                'desktop': 'tower', 
                'tower': 'tower',
                'blade': 'blade',
                'main server chassis': 'rack'
            }
            
            return chassis_mapping.get(chassis_type, 'unknown')
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return 'unknown'
    
    def _detect_enterprise_cpu(self) -> Dict[str, Any]:
        """Detect enterprise CPU (Intel Xeon/AMD EPYC) with advanced features"""
        try:
            # Get CPU model
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            
            model_match = re.search(r'model name\s+:\s+(.+)', cpuinfo)
            cpu_model = model_match.group(1) if model_match else "Unknown"
            
            # Count physical cores (not threads)
            cores_match = re.search(r'cpu cores\s+:\s+(\d+)', cpuinfo)
            cores_per_socket = int(cores_match.group(1)) if cores_match else 1
            
            # Count sockets
            sockets = len(re.findall(r'physical id\s+:\s+\d+', cpuinfo))
            sockets = max(sockets, 1)
            
            total_cores = cores_per_socket * sockets
            
            # Detect advanced features
            features = []
            flags = re.search(r'flags\s+:\s+(.+)', cpuinfo)
            if flags:
                flag_list = flags.group(1).split()
                if 'avx512f' in flag_list:
                    features.append('AVX-512')
                if 'avx2' in flag_list:
                    features.append('AVX2')
                if 'aes' in flag_list:
                    features.append('AES-NI')
                if 'vmx' in flag_list or 'svm' in flag_list:
                    features.append('Virtualization')
            
            # Detect CPU frequency
            freq_match = re.search(r'cpu MHz\s+:\s+(\d+\.?\d*)', cpuinfo)
            frequency = float(freq_match.group(1)) if freq_match else 0.0
            
            return {
                'model': cpu_model,
                'cores': total_cores,
                'sockets': sockets,
                'cores_per_socket': cores_per_socket,
                'frequency_mhz': frequency,
                'features': features,
                'is_xeon': 'Xeon' in cpu_model,
                'is_epyc': 'EPYC' in cpu_model
            }
            
        except Exception as e:
            self.logger.error(f"CPU detection failed: {e}")
            return {'model': 'Unknown', 'cores': 0}
    
    def _detect_enterprise_memory(self) -> Dict[str, Any]:
        """Detect enterprise memory configuration with NUMA topology"""
        try:
            # Total memory from /proc/meminfo
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            mem_match = re.search(r'MemTotal:\s+(\d+)\s+kB', meminfo)
            total_kb = int(mem_match.group(1)) if mem_match else 0
            total_gb = total_kb // (1024 * 1024)
            
            # Detect NUMA nodes
            numa_nodes = 0
            try:
                result = subprocess.run(['numactl', '--hardware'], 
                                      capture_output=True, text=True, check=True)
                numa_match = re.search(r'available: (\d+) nodes', result.stdout)
                numa_nodes = int(numa_match.group(1)) if numa_match else 0
            except:
                pass
            
            # Detect memory speed using dmidecode
            memory_speed = 0
            memory_type = "Unknown"
            try:
                result = subprocess.run(['dmidecode', '-t', 'memory'], 
                                      capture_output=True, text=True, check=True)
                
                speed_match = re.search(r'Speed: (\d+) MT/s', result.stdout)
                if speed_match:
                    memory_speed = int(speed_match.group(1))
                
                type_match = re.search(r'Type: (DDR\d+)', result.stdout)
                if type_match:
                    memory_type = type_match.group(1)
            except:
                pass
            
            return {
                'total_gb': total_gb,
                'numa_nodes': numa_nodes,
                'memory_speed_mts': memory_speed,
                'memory_type': memory_type,
                'is_registered': memory_speed > 2400,  # Enterprise memory is typically faster
                'ecc_capable': numa_nodes > 0  # Multi-socket systems typically have ECC
            }
            
        except Exception as e:
            self.logger.error(f"Memory detection failed: {e}")
            return {'total_gb': 0}
    
    def _detect_storage_controllers(self) -> List[str]:
        """Detect enterprise storage controllers (PERC, LSI, etc.)"""
        controllers = []
        
        try:
            # Use lspci to detect storage controllers
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            pci_devices = result.stdout
            
            # Look for Dell PERC controllers
            perc_patterns = [
                r'PERC\s+H\d+',
                r'MegaRAID\s+SAS\s+\d+',
                r'LSI.*MegaRAID',
                r'Broadcom.*MegaRAID'
            ]
            
            for pattern in perc_patterns:
                matches = re.findall(pattern, pci_devices, re.IGNORECASE)
                controllers.extend(matches)
            
            # Detect NVMe controllers
            nvme_match = re.findall(r'Non-Volatile memory controller.*', pci_devices)
            if nvme_match:
                controllers.append(f"NVMe Controllers ({len(nvme_match)})")
            
        except Exception as e:
            self.logger.error(f"Storage controller detection failed: {e}")
        
        return controllers if controllers else ['Unknown Storage Controller']
    
    def _detect_mellanox_adapters(self) -> List[str]:
        """Detect Mellanox ConnectX network adapters"""
        adapters = []
        
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            pci_devices = result.stdout
            
            # Look for Mellanox devices
            mellanox_patterns = [
                r'Mellanox.*ConnectX-\d+',
                r'ConnectX-\d+.*Ethernet',
                r'Mellanox.*InfiniBand'
            ]
            
            for pattern in mellanox_patterns:
                matches = re.findall(pattern, pci_devices, re.IGNORECASE)
                adapters.extend(matches)
            
            # Also check for other enterprise network cards
            enterprise_net = re.findall(r'Intel.*Ethernet.*10G|25G|40G|100G', pci_devices, re.IGNORECASE)
            adapters.extend(enterprise_net)
            
            # Look for Broadcom enterprise adapters
            broadcom_net = re.findall(r'Broadcom.*NetXtreme.*', pci_devices, re.IGNORECASE)
            adapters.extend(broadcom_net)
            
        except Exception as e:
            self.logger.error(f"Network adapter detection failed: {e}")
        
        return adapters if adapters else ['Unknown Network Adapter']
    
    def _detect_enterprise_gpus(self) -> List[str]:
        """Detect enterprise/server GPUs (Tesla, Instinct, etc.)"""
        gpus = []
        
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            pci_devices = result.stdout
            
            # Look for enterprise GPUs
            gpu_patterns = [
                r'NVIDIA.*Tesla.*',
                r'NVIDIA.*Quadro.*',  
                r'AMD.*Instinct.*',
                r'Intel.*Data Center GPU.*'
            ]
            
            for pattern in gpu_patterns:
                matches = re.findall(pattern, pci_devices, re.IGNORECASE)
                gpus.extend(matches)
            
        except Exception as e:
            self.logger.error(f"GPU detection failed: {e}")
        
        return gpus
    
    def _detect_idrac_version(self) -> str:
        """Detect Dell iDRAC version"""
        try:
            # Try to detect iDRAC version from DMI
            result = subprocess.run(['dmidecode', '-t', 'bios'], 
                                  capture_output=True, text=True, check=True)
            
            # Look for iDRAC references in BIOS info
            idrac_match = re.search(r'iDRAC\s+(\d+)', result.stdout, re.IGNORECASE)
            if idrac_match:
                return f"iDRAC {idrac_match.group(1)}"
            
            # Check for Dell BIOS which typically indicates iDRAC presence
            if 'dell' in result.stdout.lower():
                return "iDRAC (Version Unknown)"
                
        except Exception as e:
            self.logger.error(f"iDRAC detection failed: {e}")
        
        return "Not Detected"
    
    def _detect_power_supplies(self) -> int:
        """Detect number of power supplies"""
        try:
            # Try to read power supply info from DMI
            result = subprocess.run(['dmidecode', '-t', 'chassis'], 
                                  capture_output=True, text=True, check=True)
            
            # Look for power supply indicators
            if 'redundant' in result.stdout.lower():
                return 2  # Redundant typically means dual PSU
            elif 'power' in result.stdout.lower():
                return 1
                
        except Exception as e:
            self.logger.error(f"Power supply detection failed: {e}")
        
        return 1  # Default assumption
    
    def _generate_optimization_flags(self, hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization flags based on detected hardware"""
        flags = {
            'compiler_flags': [],
            'kernel_params': [],
            'driver_params': {},
            'performance_profile': 'enterprise'
        }
        
        # CPU-specific optimizations
        cpu_info = hardware_info.get('cpu_info', {})
        if cpu_info.get('is_xeon'):
            flags['compiler_flags'].extend(['-march=skylake-avx512', '-mtune=skylake-avx512'])
        elif cpu_info.get('is_epyc'):
            flags['compiler_flags'].extend(['-march=znver2', '-mtune=znver2'])
        
        # AVX optimizations
        cpu_features = cpu_info.get('features', [])
        if 'AVX-512' in cpu_features:
            flags['compiler_flags'].append('-mavx512f')
        elif 'AVX2' in cpu_features:
            flags['compiler_flags'].append('-mavx2')
        
        # AES-NI acceleration
        if 'AES-NI' in cpu_features:
            flags['compiler_flags'].append('-maes')
            
        # Memory optimizations
        memory_info = hardware_info.get('memory_info', {})
        if memory_info.get('numa_nodes', 0) > 1:
            flags['kernel_params'].append('numa=on')
            flags['performance_profile'] = 'numa_optimized'
        
        # Storage controller optimizations
        storage_controllers = hardware_info.get('storage_controllers', [])
        for controller in storage_controllers:
            if 'PERC' in controller:
                flags['driver_params']['megaraid_sas'] = 'use_seqnum_jbod_fp=1'
            elif 'NVMe' in controller:
                flags['kernel_params'].append('nvme.poll_queues=4')
        
        # Network adapter optimizations
        network_adapters = hardware_info.get('network_adapters', [])
        for adapter in network_adapters:
            if 'Mellanox' in adapter or 'ConnectX' in adapter:
                flags['driver_params']['mlx5_core'] = 'enable_roce=1'
                flags['kernel_params'].append('intel_iommu=on')
        
        return flags
    
    def generate_16gb_iso_architecture(self) -> Dict[str, Any]:
        """
        Generate 16GB ISO architecture optimized for enterprise servers
        
        Returns:
            Architecture specification for enterprise server ISO
        """
        if not self.detected_hardware:
            raise RuntimeError("Hardware detection must be completed first")
        
        # Calculate driver allocation based on detected hardware
        driver_budget = self._calculate_driver_budget()
        
        architecture = {
            'iso_size_gb': 16,
            'driver_allocation': driver_budget,
            'enterprise_features': {
                'dell_poweredge_support': True,
                'mellanox_drivers': 'ConnectX-6/7' in str(self.detected_hardware.network_adapters),
                'enterprise_storage': len(self.detected_hardware.storage_controllers) > 0,
                'server_gpu_support': len(self.detected_hardware.gpus) > 0,
                'numa_optimization': self.detected_hardware.optimization_flags.get('performance_profile') == 'numa_optimized'
            },
            'compilation_zones': {
                'zone_1_dell_drivers': {'size_gb': 4, 'priority': 'critical'},
                'zone_2_mellanox_drivers': {'size_gb': 3, 'priority': 'critical'},
                'zone_3_storage_drivers': {'size_gb': 2, 'priority': 'high'}, 
                'zone_4_server_gpu_drivers': {'size_gb': 2, 'priority': 'high'},
                'zone_5_enterprise_network': {'size_gb': 2, 'priority': 'medium'},
                'zone_6_system_libraries': {'size_gb': 2, 'priority': 'medium'},
                'zone_7_monitoring_drivers': {'size_gb': 1, 'priority': 'low'}
            },
            'performance_targets': {
                'network_throughput': '100Gbps+',
                'storage_iops': '1M+',
                'gpu_compute': 'Enterprise Grade',
                'memory_bandwidth': 'Full NUMA Utilization'
            }
        }
        
        self.logger.info(f"Generated 16GB enterprise ISO architecture")
        self.logger.info(f"Driver zones: {len(architecture['compilation_zones'])}")
        self.logger.info(f"Enterprise features: {architecture['enterprise_features']}")
        
        return architecture
    
    def _calculate_driver_budget(self) -> Dict[str, float]:
        """Calculate driver compilation budget based on detected hardware"""
        budget = {}
        
        # Base allocation
        total_budget_gb = 14  # Reserve 2GB for base system
        
        # Dell-specific drivers (always include for Dell servers)
        if 'Dell' in self.detected_hardware.server_model:
            budget['dell_drivers'] = 4.0  # iDRAC, PERC, power management
        
        # Mellanox drivers based on detected adapters
        mellanox_count = sum(1 for adapter in self.detected_hardware.network_adapters 
                           if 'Mellanox' in adapter or 'ConnectX' in adapter)
        if mellanox_count > 0:
            budget['mellanox_drivers'] = 3.0  # OFED, RoCE, SR-IOV
        
        # Storage controller drivers
        if self.detected_hardware.storage_controllers:
            budget['storage_drivers'] = 2.0  # RAID, NVMe, SAS
        
        # Server GPU drivers
        if self.detected_hardware.gpus:
            budget['gpu_drivers'] = 2.0  # CUDA, ROCm, compute
        
        # Enterprise networking (Intel, Broadcom)
        budget['enterprise_network'] = 2.0
        
        # System libraries and monitoring
        budget['system_libraries'] = 1.0
        
        return budget

    def execute(self, resume_data: Optional[Dict[str, Any]] = None, lockfile=None) -> Dict[str, Any]:
        """Execute enterprise hardware detection and generate ISO architecture"""
        try:
            # Detect enterprise hardware
            hardware_profile = self.detect_enterprise_hardware()
            
            # Generate 16GB ISO architecture
            iso_architecture = self.generate_16gb_iso_architecture()
            
            # Save hardware profile for other modules
            hardware_file = self.workspace / "enterprise_hardware_profile.json"
            with open(hardware_file, 'w') as f:
                json.dump(asdict(hardware_profile), f, indent=2)
            
            # Save ISO architecture
            iso_file = self.workspace / "enterprise_iso_architecture.json"  
            with open(iso_file, 'w') as f:
                json.dump(iso_architecture, f, indent=2)
            
            return {
                'status': 'success',
                'hardware_profile': asdict(hardware_profile),
                'iso_architecture': iso_architecture,
                'recommendations': self._generate_recommendations(hardware_profile)
            }
            
        except Exception as e:
            self.logger.error(f"Enterprise hardware detection failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _generate_recommendations(self, profile: EnterpriseHardwareProfile) -> List[str]:
        """Generate optimization recommendations based on detected hardware"""
        recommendations = []
        
        if 'PowerEdge' in profile.server_model:
            recommendations.append("Enable Dell OpenManage for hardware monitoring")
            recommendations.append("Configure iDRAC for out-of-band management")
        
        if any('Mellanox' in adapter for adapter in profile.network_adapters):
            recommendations.append("Install Mellanox OFED for maximum network performance")
            recommendations.append("Enable SR-IOV for virtualization workloads")
        
        if profile.cpu_cores >= 32:
            recommendations.append("Enable NUMA optimization for multi-socket systems")
            recommendations.append("Use CPU affinity for network interrupt handling")
        
        if profile.memory_gb >= 128:
            recommendations.append("Configure huge pages for memory-intensive workloads")
            recommendations.append("Enable memory interleaving for bandwidth optimization")
        
        return recommendations


if __name__ == '__main__':
    # Test hardware detection
    logging.basicConfig(level=logging.INFO)
    
    workspace = Path("/tmp/enterprise_test")
    workspace.mkdir(exist_ok=True)
    
    config = {"enterprise_mode": True}
    
    detector = EnterpriseHardwareDetector(workspace, config)
    result = detector.execute()
    
    print(f"Detection result: {result['status']}")
    if result['status'] == 'success':
        print(f"Server: {result['hardware_profile']['server_model']}")
        print(f"CPU: {result['hardware_profile']['cpu_model']}")
        print(f"Memory: {result['hardware_profile']['memory_gb']}GB")
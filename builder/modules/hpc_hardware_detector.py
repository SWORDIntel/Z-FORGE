#!/usr/bin/env python3
"""
HPC Hardware Detection System for Z-FORGE
Specialized for NVIDIA Tesla K40/K80, Intel Xeon Phi, and Dell PowerEdge T30

This module provides comprehensive hardware detection optimized for:
- NVIDIA Tesla K40/K80 GPUs (Kepler architecture, CUDA 11.x)
- Intel Xeon Phi Co-processors (Knights Landing/Knights Corner)
- Dell PowerEdge T30 Server (entry-level tower server)
- Legacy HPC hardware requiring specialized drivers and toolchains
"""

import subprocess
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import time

@dataclass
class HPCHardwareProfile:
    """HPC hardware profile for specialized scientific computing systems"""
    server_model: str
    cpu_model: str
    cpu_cores: int
    memory_gb: int
    gpu_devices: List[Dict[str, Any]]
    xeon_phi_devices: List[Dict[str, Any]]
    storage_controllers: List[str]
    network_adapters: List[str]
    chassis_type: str
    pcie_slots: Dict[str, int]  # speed -> count
    memory_architecture: Dict[str, Any]
    optimization_flags: Dict[str, Any]
    cuda_compatibility: Dict[str, Any]
    phi_compatibility: Dict[str, Any]

class HPCHardwareDetector:
    """
    Advanced hardware detection system for HPC and scientific computing
    
    Focuses on legacy HPC components with specialized requirements:
    - NVIDIA Tesla K40/K80 (Kepler architecture, requires CUDA 11.x)
    - Intel Xeon Phi (Knights Landing x200 series, Knights Corner)
    - Dell PowerEdge T30 (entry-level tower server)
    - AVX-512, MCDRAM, and specialized memory architectures
    - PCIe 3.0 optimization (no PCIe 4.0 on target hardware)
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.detected_hardware: Optional[HPCHardwareProfile] = None
        
        # NVIDIA Tesla GPU database (Kepler architecture focus)
        self.tesla_gpu_db = {
            'Tesla K40': {
                'arch': 'Kepler', 'compute': '3.5', 'memory_gb': 12, 'memory_type': 'GDDR5',
                'cuda_cores': 2880, 'memory_bandwidth': 288, 'max_cuda': '11.8',
                'driver_series': '470.x', 'power_watts': 235
            },
            'Tesla K80': {
                'arch': 'Kepler', 'compute': '3.7', 'memory_gb': 24, 'memory_type': 'GDDR5', 
                'cuda_cores': 4992, 'memory_bandwidth': 480, 'max_cuda': '11.8',
                'driver_series': '470.x', 'power_watts': 300, 'dual_gpu': True
            },
            'Tesla K20': {
                'arch': 'Kepler', 'compute': '3.5', 'memory_gb': 5, 'memory_type': 'GDDR5',
                'cuda_cores': 2496, 'memory_bandwidth': 208, 'max_cuda': '11.8',
                'driver_series': '470.x', 'power_watts': 225
            },
            'Tesla M40': {
                'arch': 'Maxwell', 'compute': '5.2', 'memory_gb': 24, 'memory_type': 'GDDR5',
                'cuda_cores': 3072, 'memory_bandwidth': 288, 'max_cuda': '11.8',
                'driver_series': '470.x', 'power_watts': 250
            }
        }
        
        # Intel Xeon Phi database (Knights Landing/Corner)
        self.xeon_phi_db = {
            'Xeon Phi 7210': {
                'arch': 'Knights Landing', 'cores': 64, 'threads': 256, 
                'base_freq': 1.3, 'boost_freq': 1.5, 'mcdram_gb': 16,
                'avx512': True, 'memory_bandwidth': 490, 'tdp_watts': 215
            },
            'Xeon Phi 7230': {
                'arch': 'Knights Landing', 'cores': 64, 'threads': 256,
                'base_freq': 1.3, 'boost_freq': 1.5, 'mcdram_gb': 16,
                'avx512': True, 'memory_bandwidth': 490, 'tdp_watts': 215
            },
            'Xeon Phi 7250': {
                'arch': 'Knights Landing', 'cores': 68, 'threads': 272,
                'base_freq': 1.4, 'boost_freq': 1.6, 'mcdram_gb': 16,
                'avx512': True, 'memory_bandwidth': 490, 'tdp_watts': 215
            },
            'Xeon Phi 7290': {
                'arch': 'Knights Landing', 'cores': 72, 'threads': 288,
                'base_freq': 1.5, 'boost_freq': 1.7, 'mcdram_gb': 16,
                'avx512': True, 'memory_bandwidth': 490, 'tdp_watts': 245
            },
            'Xeon Phi 5110P': {
                'arch': 'Knights Corner', 'cores': 60, 'threads': 240,
                'base_freq': 1.053, 'boost_freq': 1.1, 'memory_gb': 8,
                'avx512': False, 'memory_bandwidth': 320, 'tdp_watts': 225
            }
        }
        
        # Dell T30 configuration database
        self.dell_t30_configs = {
            'base': {'max_memory': 64, 'memory_slots': 4, 'pcie_slots': {'x16': 1, 'x8': 2, 'x4': 1}},
            'sata_ports': 4, 'usb3_ports': 4, 'cpu_socket': 'LGA1151',
            'chipset': 'C236', 'form_factor': 'tower', 'psu_max': 290
        }
        
        # Memory architecture patterns
        self.memory_architectures = {
            'standard_ddr4': {'channels': 2, 'max_speed': 2400, 'ecc': True},
            'xeon_phi_hybrid': {'ddr4_channels': 6, 'mcdram_gb': 16, 'bandwidth_ratio': '5:1'},
            'tesla_unified': {'host_memory': True, 'gpu_memory': True, 'unified_addressing': True}
        }
        
    def detect_hpc_hardware(self) -> HPCHardwareProfile:
        """
        Comprehensive HPC hardware detection for scientific computing systems
        
        Returns:
            HPCHardwareProfile with complete HPC system specifications
        """
        self.logger.info("Starting HPC hardware detection for scientific computing systems...")
        
        # Detect server model and chassis
        server_model = self._detect_server_model()
        chassis_type = self._detect_chassis_type()
        
        # CPU and memory detection (with HPC focus)
        cpu_info = self._detect_hpc_cpu()
        memory_info = self._detect_hpc_memory()
        
        # GPU detection (Tesla focus)
        gpu_devices = self._detect_tesla_gpus()
        
        # Intel Xeon Phi detection
        phi_devices = self._detect_xeon_phi()
        
        # Storage and network
        storage_controllers = self._detect_storage_controllers()
        network_adapters = self._detect_network_adapters()
        
        # PCIe slot configuration
        pcie_slots = self._detect_pcie_configuration()
        
        # Memory architecture analysis
        memory_architecture = self._analyze_memory_architecture(memory_info, phi_devices)
        
        # CUDA compatibility analysis
        cuda_compatibility = self._analyze_cuda_compatibility(gpu_devices)
        
        # Xeon Phi compatibility analysis
        phi_compatibility = self._analyze_phi_compatibility(phi_devices)
        
        # Generate optimization flags
        optimization_flags = self._generate_hpc_optimization_flags({
            'server_model': server_model,
            'cpu_info': cpu_info,
            'memory_info': memory_info,
            'gpu_devices': gpu_devices,
            'phi_devices': phi_devices
        })
        
        self.detected_hardware = HPCHardwareProfile(
            server_model=server_model,
            cpu_model=cpu_info.get('model', 'Unknown'),
            cpu_cores=cpu_info.get('cores', 0),
            memory_gb=memory_info.get('total_gb', 0),
            gpu_devices=gpu_devices,
            xeon_phi_devices=phi_devices,
            storage_controllers=storage_controllers,
            network_adapters=network_adapters,
            chassis_type=chassis_type,
            pcie_slots=pcie_slots,
            memory_architecture=memory_architecture,
            optimization_flags=optimization_flags,
            cuda_compatibility=cuda_compatibility,
            phi_compatibility=phi_compatibility
        )
        
        self._log_detection_summary()
        
        return self.detected_hardware
        
    def _detect_server_model(self) -> str:
        """Detect server model with focus on Dell T30 and HPC systems"""
        try:
            result = subprocess.run(['dmidecode', '-s', 'system-product-name'], 
                                  capture_output=True, text=True, check=True)
            product_name = result.stdout.strip()
            
            # Dell PowerEdge T30 detection
            if 't30' in product_name.lower() or 'poweredge t30' in product_name.lower():
                return "Dell PowerEdge T30"
            
            # Generic Dell detection
            if 'poweredge' in product_name.lower():
                return f"Dell {product_name}"
            
            # Other HPC vendor detection
            if any(vendor in product_name.lower() for vendor in ['supermicro', 'hp', 'lenovo']):
                return product_name
                
            return "Unknown HPC Server"
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("Could not detect server model")
            return "Unknown Server"
    
    def _detect_chassis_type(self) -> str:
        """Detect chassis type with HPC focus"""
        try:
            result = subprocess.run(['dmidecode', '-s', 'chassis-type'], 
                                  capture_output=True, text=True, check=True)
            chassis_type = result.stdout.strip().lower()
            
            chassis_mapping = {
                'tower': 'tower',
                'desktop': 'tower', 
                'rack mount chassis': 'rack',
                'main server chassis': 'rack',
                'blade': 'blade'
            }
            
            return chassis_mapping.get(chassis_type, 'unknown')
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return 'unknown'
    
    def _detect_hpc_cpu(self) -> Dict[str, Any]:
        """Detect HPC CPU with focus on Xeon E3/E5 and Xeon Phi host CPUs"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            
            model_match = re.search(r'model name\s+:\s+(.+)', cpuinfo)
            cpu_model = model_match.group(1) if model_match else "Unknown"
            
            # Physical core detection
            cores_match = re.search(r'cpu cores\s+:\s+(\d+)', cpuinfo)
            cores_per_socket = int(cores_match.group(1)) if cores_match else 1
            
            # Socket count
            sockets = len(set(re.findall(r'physical id\s+:\s+(\d+)', cpuinfo)))
            sockets = max(sockets, 1)
            
            total_cores = cores_per_socket * sockets
            
            # HPC-specific feature detection
            features = []
            flags = re.search(r'flags\s+:\s+(.+)', cpuinfo)
            if flags:
                flag_list = flags.group(1).split()
                
                # AVX-512 variants (critical for Xeon Phi)
                avx512_variants = [f for f in flag_list if f.startswith('avx512')]
                if avx512_variants:
                    features.append('AVX-512')
                    features.extend(avx512_variants)
                
                if 'avx2' in flag_list:
                    features.append('AVX2')
                if 'fma' in flag_list:
                    features.append('FMA')
                if 'aes' in flag_list:
                    features.append('AES-NI')
                if 'vmx' in flag_list or 'svm' in flag_list:
                    features.append('Virtualization')
                if 'rdrand' in flag_list:
                    features.append('RDRAND')
                if 'rdseed' in flag_list:
                    features.append('RDSEED')
            
            # Frequency detection
            freq_match = re.search(r'cpu MHz\s+:\s+(\d+\.?\d*)', cpuinfo)
            frequency = float(freq_match.group(1)) if freq_match else 0.0
            
            # CPU family detection for HPC optimization
            cpu_family = 'unknown'
            if 'Xeon' in cpu_model:
                if 'E3' in cpu_model:
                    cpu_family = 'xeon_e3'
                elif 'E5' in cpu_model:
                    cpu_family = 'xeon_e5'
                elif 'Phi' in cpu_model:
                    cpu_family = 'xeon_phi'
                else:
                    cpu_family = 'xeon_other'
            elif 'Core' in cpu_model:
                cpu_family = 'core'
            
            return {
                'model': cpu_model,
                'family': cpu_family,
                'cores': total_cores,
                'sockets': sockets,
                'cores_per_socket': cores_per_socket,
                'frequency_mhz': frequency,
                'features': features,
                'avx512_support': 'AVX-512' in features,
                'is_xeon': 'Xeon' in cpu_model,
                'is_hpc_grade': any(x in cpu_model.upper() for x in ['XEON', 'EPYC', 'CORE I7', 'CORE I9'])
            }
            
        except Exception as e:
            self.logger.error(f"HPC CPU detection failed: {e}")
            return {'model': 'Unknown', 'cores': 0}
    
    def _detect_hpc_memory(self) -> Dict[str, Any]:
        """Detect HPC memory with focus on ECC, high-speed, and MCDRAM"""
        try:
            # Basic memory info
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            mem_match = re.search(r'MemTotal:\s+(\d+)\s+kB', meminfo)
            total_kb = int(mem_match.group(1)) if mem_match else 0
            total_gb = total_kb // (1024 * 1024)
            
            # NUMA topology (important for Xeon Phi systems)
            numa_nodes = 0
            numa_info = {}
            try:
                result = subprocess.run(['numactl', '--hardware'], 
                                      capture_output=True, text=True, check=True)
                numa_match = re.search(r'available: (\d+) nodes', result.stdout)
                numa_nodes = int(numa_match.group(1)) if numa_match else 0
                
                # Parse NUMA node memory distribution
                node_matches = re.findall(r'node (\d+) cpus: ([0-9\s]+)', result.stdout)
                for node_id, cpu_list in node_matches:
                    numa_info[f'node_{node_id}'] = {
                        'cpus': [int(x) for x in cpu_list.split() if x.strip()],
                        'memory_gb': 0  # Will be filled by dmidecode if available
                    }
                    
            except:
                pass
            
            # Detailed memory information from dmidecode
            memory_details = self._get_memory_details_dmidecode()
            
            # Check for MCDRAM (Xeon Phi specific)
            mcdram_info = self._detect_mcdram()
            
            return {
                'total_gb': total_gb,
                'numa_nodes': numa_nodes,
                'numa_info': numa_info,
                'memory_details': memory_details,
                'mcdram': mcdram_info,
                'is_ecc': memory_details.get('is_ecc', False),
                'max_speed_mts': memory_details.get('max_speed', 0),
                'memory_type': memory_details.get('type', 'Unknown'),
                'registered': memory_details.get('registered', False)
            }
            
        except Exception as e:
            self.logger.error(f"HPC memory detection failed: {e}")
            return {'total_gb': 0}
    
    def _get_memory_details_dmidecode(self) -> Dict[str, Any]:
        """Get detailed memory information using dmidecode"""
        details = {
            'slots_total': 0,
            'slots_used': 0,
            'modules': [],
            'max_speed': 0,
            'type': 'Unknown',
            'is_ecc': False,
            'registered': False
        }
        
        try:
            result = subprocess.run(['dmidecode', '-t', 'memory'], 
                                  capture_output=True, text=True, check=True)
            
            # Parse memory modules
            modules = []
            current_module = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                
                if line.startswith('Memory Device'):
                    if current_module:
                        modules.append(current_module)
                    current_module = {}
                    
                elif ':' in line and current_module is not None:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    if key == 'size' and value != 'No Module Installed':
                        current_module['size'] = value
                        details['slots_used'] += 1
                    elif key == 'type' and value != 'Unknown':
                        current_module['type'] = value
                        details['type'] = value
                    elif key == 'speed' and 'MT/s' in value:
                        speed = int(value.replace(' MT/s', ''))
                        current_module['speed'] = speed
                        details['max_speed'] = max(details['max_speed'], speed)
                    elif key == 'type_detail':
                        if 'ECC' in value:
                            details['is_ecc'] = True
                        if 'Registered' in value:
                            details['registered'] = True
            
            if current_module:
                modules.append(current_module)
            
            details['modules'] = modules
            details['slots_total'] = len(modules)
            
        except Exception as e:
            self.logger.warning(f"Memory details detection failed: {e}")
        
        return details
    
    def _detect_mcdram(self) -> Dict[str, Any]:
        """Detect Intel Xeon Phi MCDRAM (Multi-Channel DRAM)"""
        mcdram = {
            'present': False,
            'size_gb': 0,
            'mode': 'unknown',
            'bandwidth_gb_s': 0
        }
        
        try:
            # Check for Xeon Phi specific memory controllers
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            
            # Look for Xeon Phi memory controllers
            if 'Knights Landing' in result.stdout or 'Knights Corner' in result.stdout:
                mcdram['present'] = True
                mcdram['size_gb'] = 16  # Standard MCDRAM size
                mcdram['bandwidth_gb_s'] = 490  # Theoretical peak
                
                # Try to determine MCDRAM mode
                try:
                    # Check /proc/mtrr or other system files for MCDRAM configuration
                    with open('/proc/iomem', 'r') as f:
                        iomem = f.read()
                    
                    if 'mcdram' in iomem.lower():
                        mcdram['mode'] = 'cache'  # Most common mode
                    else:
                        mcdram['mode'] = 'flat'   # Direct addressable memory
                        
                except:
                    mcdram['mode'] = 'unknown'
            
        except Exception as e:
            self.logger.debug(f"MCDRAM detection: {e}")
        
        return mcdram
    
    def _detect_tesla_gpus(self) -> List[Dict[str, Any]]:
        """Detect NVIDIA Tesla GPUs with focus on K40/K80 (Kepler)"""
        gpus = []
        
        try:
            # First try nvidia-ml-py if available
            try:
                import pynvml
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    
                    # Check if it's a Tesla GPU
                    if 'Tesla' in name:
                        gpu_info = self._get_detailed_gpu_info(handle, name, i)
                        gpus.append(gpu_info)
                        
            except ImportError:
                self.logger.info("pynvml not available, using nvidia-smi")
                gpus = self._detect_gpus_nvidia_smi()
            
        except Exception as e:
            self.logger.warning(f"Tesla GPU detection failed: {e}")
            # Fallback to lspci detection
            gpus = self._detect_gpus_lspci()
        
        return gpus
    
    def _get_detailed_gpu_info(self, handle, name: str, index: int) -> Dict[str, Any]:
        """Get detailed Tesla GPU information using pynvml"""
        try:
            import pynvml
            
            # Basic info
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            # Try to get compute capability
            major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
            compute_capability = f"{major}.{minor}"
            
            # GPU specifications from database
            gpu_specs = {}
            for model_name, specs in self.tesla_gpu_db.items():
                if model_name.replace('Tesla ', '') in name:
                    gpu_specs = specs.copy()
                    break
            
            return {
                'index': index,
                'name': name,
                'memory_total_mb': memory_info.total // 1024 // 1024,
                'memory_free_mb': memory_info.free // 1024 // 1024,
                'compute_capability': compute_capability,
                'architecture': gpu_specs.get('arch', 'Unknown'),
                'cuda_cores': gpu_specs.get('cuda_cores', 0),
                'memory_bandwidth_gb_s': gpu_specs.get('memory_bandwidth', 0),
                'max_cuda_version': gpu_specs.get('max_cuda', 'Unknown'),
                'recommended_driver': gpu_specs.get('driver_series', 'Unknown'),
                'power_watts': gpu_specs.get('power_watts', 0),
                'is_dual_gpu': gpu_specs.get('dual_gpu', False),
                'optimization_profile': 'hpc_kepler' if 'Kepler' in gpu_specs.get('arch', '') else 'hpc_other'
            }
            
        except Exception as e:
            self.logger.warning(f"Detailed GPU info failed for {name}: {e}")
            return {'index': index, 'name': name, 'error': str(e)}
    
    def _detect_gpus_nvidia_smi(self) -> List[Dict[str, Any]]:
        """Fallback GPU detection using nvidia-smi"""
        gpus = []
        
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.total,compute_cap', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, check=True)
            
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 4:
                        index, name, memory_mb, compute_cap = parts[:4]
                        
                        if 'Tesla' in name:
                            # Look up specifications
                            gpu_specs = {}
                            for model_name, specs in self.tesla_gpu_db.items():
                                if model_name.replace('Tesla ', '') in name:
                                    gpu_specs = specs.copy()
                                    break
                            
                            gpus.append({
                                'index': int(index),
                                'name': name,
                                'memory_total_mb': int(memory_mb),
                                'compute_capability': compute_cap,
                                'architecture': gpu_specs.get('arch', 'Unknown'),
                                'cuda_cores': gpu_specs.get('cuda_cores', 0),
                                'max_cuda_version': gpu_specs.get('max_cuda', 'Unknown'),
                                'recommended_driver': gpu_specs.get('driver_series', 'Unknown'),
                                'optimization_profile': 'hpc_kepler' if 'Kepler' in gpu_specs.get('arch', '') else 'hpc_other'
                            })
                            
        except subprocess.CalledProcessError:
            self.logger.warning("nvidia-smi not available or failed")
        
        return gpus
    
    def _detect_gpus_lspci(self) -> List[Dict[str, Any]]:
        """Final fallback GPU detection using lspci"""
        gpus = []
        
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            
            tesla_patterns = [
                r'NVIDIA.*Tesla.*K[48]0',
                r'NVIDIA.*Tesla.*K20',
                r'NVIDIA.*Tesla.*M40'
            ]
            
            for pattern in tesla_patterns:
                matches = re.findall(pattern, result.stdout, re.IGNORECASE)
                for i, match in enumerate(matches):
                    # Extract model name
                    name_match = re.search(r'Tesla.*?([KM]\d+)', match)
                    if name_match:
                        model = name_match.group(1)
                        full_name = f"Tesla {model}"
                        
                        # Look up specifications
                        gpu_specs = {}
                        for model_name, specs in self.tesla_gpu_db.items():
                            if model in model_name:
                                gpu_specs = specs.copy()
                                break
                        
                        gpus.append({
                            'index': i,
                            'name': full_name,
                            'detected_via': 'lspci',
                            'compute_capability': gpu_specs.get('compute', 'Unknown'),
                            'architecture': gpu_specs.get('arch', 'Unknown'),
                            'memory_total_mb': gpu_specs.get('memory_gb', 0) * 1024,
                            'cuda_cores': gpu_specs.get('cuda_cores', 0),
                            'max_cuda_version': gpu_specs.get('max_cuda', 'Unknown'),
                            'recommended_driver': gpu_specs.get('driver_series', 'Unknown'),
                            'optimization_profile': 'hpc_kepler' if 'Kepler' in gpu_specs.get('arch', '') else 'hpc_other'
                        })
        
        except Exception as e:
            self.logger.warning(f"lspci GPU detection failed: {e}")
        
        return gpus
    
    def _detect_xeon_phi(self) -> List[Dict[str, Any]]:
        """Detect Intel Xeon Phi Co-processors (Knights Landing/Corner)"""
        phi_devices = []
        
        try:
            # Check lspci for Xeon Phi devices
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            
            phi_patterns = [
                r'Intel.*Xeon Phi.*(\d{4})',  # Xeon Phi with model number
                r'Knights Landing.*(\d{4})',
                r'Knights Corner.*(\d{4})'
            ]
            
            for pattern in phi_patterns:
                matches = re.findall(pattern, result.stdout, re.IGNORECASE)
                for match in matches:
                    model_num = match if isinstance(match, str) else match[0]
                    
                    # Look up in database
                    phi_specs = {}
                    model_name = f"Xeon Phi {model_num}"
                    
                    for db_name, specs in self.xeon_phi_db.items():
                        if model_num in db_name:
                            phi_specs = specs.copy()
                            model_name = db_name
                            break
                    
                    phi_device = {
                        'name': model_name,
                        'model_number': model_num,
                        'architecture': phi_specs.get('arch', 'Unknown'),
                        'cores': phi_specs.get('cores', 0),
                        'threads': phi_specs.get('threads', 0),
                        'base_frequency_ghz': phi_specs.get('base_freq', 0),
                        'boost_frequency_ghz': phi_specs.get('boost_freq', 0),
                        'avx512_support': phi_specs.get('avx512', False),
                        'memory_bandwidth_gb_s': phi_specs.get('memory_bandwidth', 0),
                        'tdp_watts': phi_specs.get('tdp_watts', 0),
                        'optimization_profile': 'phi_' + phi_specs.get('arch', 'unknown').lower().replace(' ', '_')
                    }
                    
                    # Add MCDRAM info for Knights Landing
                    if phi_specs.get('mcdram_gb', 0) > 0:
                        phi_device['mcdram_gb'] = phi_specs['mcdram_gb']
                        phi_device['has_mcdram'] = True
                    else:
                        phi_device['has_mcdram'] = False
                    
                    phi_devices.append(phi_device)
                    
        except Exception as e:
            self.logger.warning(f"Xeon Phi detection failed: {e}")
        
        return phi_devices
    
    def _detect_storage_controllers(self) -> List[str]:
        """Detect storage controllers with HPC focus"""
        controllers = []
        
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            pci_devices = result.stdout
            
            # HPC-focused storage patterns
            storage_patterns = [
                r'RAID.*controller.*',
                r'SATA.*controller.*',
                r'SAS.*controller.*',
                r'NVMe.*controller.*',
                r'LSI.*RAID.*',
                r'Intel.*RAID.*',
                r'Dell.*PERC.*'
            ]
            
            for pattern in storage_patterns:
                matches = re.findall(pattern, pci_devices, re.IGNORECASE)
                controllers.extend(matches)
            
        except Exception as e:
            self.logger.error(f"Storage controller detection failed: {e}")
        
        return controllers if controllers else ['Unknown Storage Controller']
    
    def _detect_network_adapters(self) -> List[str]:
        """Detect network adapters with HPC focus (InfiniBand, 10GbE+)"""
        adapters = []
        
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
            pci_devices = result.stdout
            
            # HPC networking patterns
            hpc_net_patterns = [
                r'Mellanox.*InfiniBand.*',
                r'Intel.*10.*Gigabit.*',
                r'Intel.*40.*Gigabit.*',
                r'Chelsio.*10.*Gigabit.*',
                r'QLogic.*InfiniBand.*',
                r'Ethernet.*10G.*'
            ]
            
            for pattern in hpc_net_patterns:
                matches = re.findall(pattern, pci_devices, re.IGNORECASE)
                adapters.extend(matches)
            
            # Also get basic ethernet controllers
            eth_matches = re.findall(r'Ethernet.*controller.*', pci_devices, re.IGNORECASE)
            adapters.extend(eth_matches[:2])  # Limit to avoid spam
            
        except Exception as e:
            self.logger.error(f"Network adapter detection failed: {e}")
        
        return adapters if adapters else ['Unknown Network Adapter']
    
    def _detect_pcie_configuration(self) -> Dict[str, int]:
        """Detect PCIe slot configuration and capabilities"""
        pcie_config = {'x1': 0, 'x4': 0, 'x8': 0, 'x16': 0}
        
        try:
            result = subprocess.run(['lspci', '-vv'], capture_output=True, text=True, check=True)
            
            # Parse PCIe link widths
            for line in result.stdout.split('\n'):
                if 'LnkCap:' in line or 'LnkSta:' in line:
                    # Extract width information
                    width_match = re.search(r'Width x(\d+)', line)
                    if width_match:
                        width = int(width_match.group(1))
                        if width <= 1:
                            pcie_config['x1'] += 1
                        elif width <= 4:
                            pcie_config['x4'] += 1
                        elif width <= 8:
                            pcie_config['x8'] += 1
                        else:
                            pcie_config['x16'] += 1
            
        except Exception as e:
            self.logger.warning(f"PCIe configuration detection failed: {e}")
        
        return pcie_config
    
    def _analyze_memory_architecture(self, memory_info: Dict[str, Any], 
                                   phi_devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze memory architecture for HPC optimization"""
        architecture = {
            'type': 'standard_ddr4',
            'numa_aware': False,
            'has_hbm': False,
            'has_mcdram': False,
            'optimization_strategy': 'standard'
        }
        
        # Check for NUMA
        if memory_info.get('numa_nodes', 0) > 1:
            architecture['numa_aware'] = True
            architecture['numa_nodes'] = memory_info['numa_nodes']
        
        # Check for MCDRAM (Xeon Phi)
        if any(device.get('has_mcdram', False) for device in phi_devices):
            architecture['has_mcdram'] = True
            architecture['type'] = 'xeon_phi_hybrid'
            architecture['optimization_strategy'] = 'phi_mcdram_aware'
        
        # Memory speed classification
        max_speed = memory_info.get('max_speed_mts', 0)
        if max_speed >= 3200:
            architecture['speed_class'] = 'high_performance'
        elif max_speed >= 2400:
            architecture['speed_class'] = 'standard'
        else:
            architecture['speed_class'] = 'low_performance'
        
        return architecture
    
    def _analyze_cuda_compatibility(self, gpu_devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze CUDA compatibility and optimization requirements"""
        compatibility = {
            'has_cuda_gpus': len(gpu_devices) > 0,
            'max_cuda_version': '0.0',
            'min_driver_version': 'unknown',
            'compute_capabilities': [],
            'optimization_profile': 'none'
        }
        
        if gpu_devices:
            # Determine maximum supported CUDA version
            max_cuda_versions = []
            driver_versions = []
            compute_caps = []
            
            for gpu in gpu_devices:
                max_cuda = gpu.get('max_cuda_version', '0.0')
                if max_cuda != 'Unknown':
                    max_cuda_versions.append(max_cuda)
                
                driver = gpu.get('recommended_driver', 'unknown')
                if driver != 'Unknown':
                    driver_versions.append(driver)
                
                compute_cap = gpu.get('compute_capability', '0.0')
                if compute_cap != 'Unknown':
                    compute_caps.append(compute_cap)
            
            if max_cuda_versions:
                # Use the lowest common denominator for compatibility
                compatibility['max_cuda_version'] = min(max_cuda_versions)
            
            if driver_versions:
                # Use most common driver version
                compatibility['min_driver_version'] = max(set(driver_versions), key=driver_versions.count)
            
            compatibility['compute_capabilities'] = list(set(compute_caps))
            
            # Determine optimization profile
            if any('Kepler' in gpu.get('architecture', '') for gpu in gpu_devices):
                compatibility['optimization_profile'] = 'legacy_kepler'
            elif any('Maxwell' in gpu.get('architecture', '') for gpu in gpu_devices):
                compatibility['optimization_profile'] = 'legacy_maxwell'
            else:
                compatibility['optimization_profile'] = 'modern_cuda'
        
        return compatibility
    
    def _analyze_phi_compatibility(self, phi_devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze Intel Xeon Phi compatibility and optimization requirements"""
        compatibility = {
            'has_phi_devices': len(phi_devices) > 0,
            'architectures': [],
            'requires_mpss': False,
            'avx512_support': False,
            'mcdram_available': False,
            'optimization_profile': 'none'
        }
        
        if phi_devices:
            architectures = []
            
            for device in phi_devices:
                arch = device.get('architecture', 'Unknown')
                architectures.append(arch)
                
                if arch in ['Knights Landing', 'Knights Corner']:
                    compatibility['requires_mpss'] = True
                
                if device.get('avx512_support', False):
                    compatibility['avx512_support'] = True
                
                if device.get('has_mcdram', False):
                    compatibility['mcdram_available'] = True
            
            compatibility['architectures'] = list(set(architectures))
            
            # Determine optimization profile
            if 'Knights Landing' in architectures:
                compatibility['optimization_profile'] = 'knights_landing'
            elif 'Knights Corner' in architectures:
                compatibility['optimization_profile'] = 'knights_corner'
            else:
                compatibility['optimization_profile'] = 'generic_phi'
        
        return compatibility
    
    def _generate_hpc_optimization_flags(self, hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate HPC-specific optimization flags"""
        flags = {
            'compiler_flags': [],
            'linker_flags': [],
            'cuda_flags': [],
            'phi_flags': [],
            'openmp_flags': [],
            'mpi_flags': [],
            'kernel_params': [],
            'driver_params': {},
            'performance_profile': 'hpc_optimized'
        }
        
        cpu_info = hardware_info.get('cpu_info', {})
        gpu_devices = hardware_info.get('gpu_devices', [])
        phi_devices = hardware_info.get('phi_devices', [])
        
        # CPU-specific optimizations
        if cpu_info.get('is_xeon'):
            if 'E3' in cpu_info.get('model', ''):
                flags['compiler_flags'].extend(['-march=broadwell', '-mtune=broadwell'])
            elif 'E5' in cpu_info.get('model', ''):
                flags['compiler_flags'].extend(['-march=haswell', '-mtune=haswell'])
        
        # AVX-512 optimizations
        if cpu_info.get('avx512_support', False):
            flags['compiler_flags'].extend(['-mavx512f', '-mavx512cd', '-mavx512er', '-mavx512pf'])
            flags['openmp_flags'].append('-DOMP_USE_AVX512')
        elif 'AVX2' in cpu_info.get('features', []):
            flags['compiler_flags'].append('-mavx2')
        
        # AES-NI acceleration
        if 'AES-NI' in cpu_info.get('features', []):
            flags['compiler_flags'].append('-maes')
        
        # GPU-specific optimizations
        if gpu_devices:
            for gpu in gpu_devices:
                compute_cap = gpu.get('compute_capability', '0.0')
                if compute_cap.startswith('3.'):  # Kepler
                    flags['cuda_flags'].extend(['-gencode', f'arch=compute_35,code=sm_35'])
                    flags['cuda_flags'].extend(['-Xptxas', '-O3'])
        
        # Xeon Phi optimizations
        if phi_devices:
            flags['phi_flags'].extend(['-mmic', '-qopt-streaming-stores', 'always'])
            flags['openmp_flags'].extend(['-qopenmp', '-qopt-threads-per-core=4'])
            
            # MCDRAM optimization
            if any(device.get('has_mcdram', False) for device in phi_devices):
                flags['kernel_params'].append('memmap=16G!4G')  # Reserve MCDRAM
        
        # Memory optimizations
        memory_info = hardware_info.get('memory_info', {})
        if memory_info.get('numa_nodes', 0) > 1:
            flags['kernel_params'].append('numa=on')
            flags['mpi_flags'].append('-bind-to numa')
        
        # High-performance computing flags
        flags['compiler_flags'].extend(['-O3', '-ffast-math', '-funroll-loops'])
        flags['linker_flags'].extend(['-lm', '-lpthread'])
        
        return flags
    
    def _log_detection_summary(self):
        """Log comprehensive detection summary"""
        if not self.detected_hardware:
            return
        
        hw = self.detected_hardware
        
        self.logger.info("=== HPC Hardware Detection Summary ===")
        self.logger.info(f"Server: {hw.server_model} ({hw.chassis_type})")
        self.logger.info(f"CPU: {hw.cpu_model} ({hw.cpu_cores} cores)")
        self.logger.info(f"Memory: {hw.memory_gb}GB ({hw.memory_architecture.get('type', 'unknown')})")
        
        if hw.gpu_devices:
            self.logger.info(f"Tesla GPUs: {len(hw.gpu_devices)} detected")
            for gpu in hw.gpu_devices:
                self.logger.info(f"  - {gpu.get('name', 'Unknown')} "
                                f"({gpu.get('compute_capability', 'N/A')} compute, "
                                f"{gpu.get('memory_total_mb', 0)}MB)")
        
        if hw.xeon_phi_devices:
            self.logger.info(f"Xeon Phi: {len(hw.xeon_phi_devices)} detected")
            for phi in hw.xeon_phi_devices:
                self.logger.info(f"  - {phi.get('name', 'Unknown')} "
                                f"({phi.get('cores', 0)} cores, "
                                f"{phi.get('threads', 0)} threads)")
        
        cuda_compat = hw.cuda_compatibility
        if cuda_compat.get('has_cuda_gpus', False):
            self.logger.info(f"CUDA: Max version {cuda_compat.get('max_cuda_version', 'N/A')}, "
                            f"Driver {cuda_compat.get('min_driver_version', 'N/A')}")
        
        phi_compat = hw.phi_compatibility
        if phi_compat.get('has_phi_devices', False):
            self.logger.info(f"Xeon Phi: {', '.join(phi_compat.get('architectures', []))} "
                            f"(AVX-512: {phi_compat.get('avx512_support', False)})")
        
        self.logger.info("========================================")
    
    def generate_32gb_iso_architecture(self) -> Dict[str, Any]:
        """
        Generate 32GB ISO architecture optimized for HPC hardware
        
        Returns:
            Architecture specification for HPC-optimized 32GB ISO
        """
        if not self.detected_hardware:
            raise RuntimeError("Hardware detection must be completed first")
        
        hw = self.detected_hardware
        
        # Calculate comprehensive driver allocation
        driver_budget = self._calculate_hpc_driver_budget()
        
        architecture = {
            'iso_size_gb': 32,
            'driver_allocation': driver_budget,
            'hpc_features': {
                'tesla_gpu_support': len(hw.gpu_devices) > 0,
                'xeon_phi_support': len(hw.xeon_phi_devices) > 0,
                'cuda_toolkit_version': hw.cuda_compatibility.get('max_cuda_version', 'none'),
                'intel_parallel_studio': hw.phi_compatibility.get('has_phi_devices', False),
                'avx512_optimization': any(device.get('avx512_support', False) for device in hw.xeon_phi_devices),
                'mcdram_support': hw.memory_architecture.get('has_mcdram', False),
                'numa_optimization': hw.memory_architecture.get('numa_aware', False)
            },
            'compilation_zones': {
                'zone_1_cuda_toolkit': {
                    'size_gb': 8, 'priority': 'critical',
                    'includes': ['CUDA 11.8', 'cuDNN', 'NCCL', 'Thrust']
                },
                'zone_2_intel_tools': {
                    'size_gb': 6, 'priority': 'critical',
                    'includes': ['Intel Parallel Studio XE', 'MKL', 'TBB', 'MPSS']
                },
                'zone_3_hpc_libraries': {
                    'size_gb': 4, 'priority': 'high',
                    'includes': ['OpenMPI', 'FFTW', 'BLAS', 'LAPACK', 'ScaLAPACK']
                },
                'zone_4_tesla_drivers': {
                    'size_gb': 3, 'priority': 'high',
                    'includes': ['NVIDIA 470.x LTS', 'Tesla K40/K80 firmware']
                },
                'zone_5_phi_runtime': {
                    'size_gb': 2, 'priority': 'high',
                    'includes': ['Xeon Phi runtime', 'MPSS', 'COI libraries']
                },
                'zone_6_scientific_python': {
                    'size_gb': 3, 'priority': 'medium',
                    'includes': ['NumPy', 'SciPy', 'Pandas', 'Matplotlib', 'CuPy']
                },
                'zone_7_compilers': {
                    'size_gb': 2, 'priority': 'medium',
                    'includes': ['GCC 9/10/11', 'Clang/LLVM', 'Intel ICC']
                },
                'zone_8_monitoring': {
                    'size_gb': 2, 'priority': 'medium',
                    'includes': ['NVIDIA-ML', 'Intel VTune', 'Ganglia', 'Nagios']
                },
                'zone_9_development': {
                    'size_gb': 1, 'priority': 'low',
                    'includes': ['GDB', 'Valgrind', 'Intel Inspector', 'PAPI']
                },
                'zone_10_base_system': {
                    'size_gb': 1, 'priority': 'critical',
                    'includes': ['Debian base', 'ZFS', 'Boot system']
                }
            },
            'performance_targets': {
                'tesla_memory_bandwidth': '288-480 GB/s',
                'phi_memory_bandwidth': '490 GB/s (MCDRAM)',
                'host_memory_bandwidth': '50-100 GB/s',
                'cuda_compile_time': '<5 minutes per kernel',
                'phi_compile_time': '<10 minutes per application',
                'scientific_compute': 'Optimized for double precision'
            },
            'native_compilation': {
                'enabled': True,
                'hardware_specific': True,
                'compile_time_estimate': '45-90 minutes',
                'memory_requirement': '16GB minimum',
                'cpu_optimization': 'Per-target AVX/AVX2/AVX-512',
                'gpu_optimization': 'Compute capability specific',
                'phi_optimization': 'MCDRAM and many-core aware'
            }
        }
        
        self.logger.info(f"Generated 32GB HPC ISO architecture")
        self.logger.info(f"Compilation zones: {len(architecture['compilation_zones'])}")
        self.logger.info(f"HPC features: {sum(architecture['hpc_features'].values())} enabled")
        self.logger.info(f"Native compilation: {architecture['native_compilation']['enabled']}")
        
        return architecture
    
    def _calculate_hpc_driver_budget(self) -> Dict[str, float]:
        """Calculate HPC driver compilation budget based on detected hardware"""
        budget = {}
        total_budget_gb = 30  # Reserve 2GB for base system
        
        hw = self.detected_hardware
        
        # CUDA toolkit (always include for HPC)
        budget['cuda_toolkit'] = 8.0  # Complete CUDA 11.8 + tools
        
        # Intel tools for Xeon Phi
        if hw.xeon_phi_devices:
            budget['intel_parallel_studio'] = 6.0  # Full Intel toolchain
        else:
            budget['intel_parallel_studio'] = 2.0  # Basic Intel tools
        
        # Tesla GPU drivers
        tesla_count = len(hw.gpu_devices)
        if tesla_count > 0:
            budget['tesla_drivers'] = min(3.0 + (tesla_count - 1) * 0.5, 5.0)
        
        # HPC libraries (always substantial for scientific computing)
        budget['hpc_libraries'] = 4.0  # MPI, FFTW, BLAS, etc.
        
        # Scientific Python stack
        budget['scientific_python'] = 3.0  # NumPy, SciPy, CuPy
        
        # Compilers and development tools
        budget['compilers'] = 2.0  # Multiple compiler versions
        
        # Monitoring and profiling
        budget['monitoring_tools'] = 2.0  # Performance analysis
        
        return budget

    def execute(self, resume_data: Optional[Dict[str, Any]] = None, lockfile=None) -> Dict[str, Any]:
        """Execute HPC hardware detection and generate ISO architecture"""
        try:
            self.logger.info("Starting HPC hardware detection and analysis...")
            
            # Detect HPC hardware
            hardware_profile = self.detect_hpc_hardware()
            
            # Generate 32GB ISO architecture
            iso_architecture = self.generate_32gb_iso_architecture()
            
            # Save hardware profile
            hardware_file = self.workspace / "hpc_hardware_profile.json"
            with open(hardware_file, 'w') as f:
                json.dump(asdict(hardware_profile), f, indent=2)
            
            # Save ISO architecture  
            iso_file = self.workspace / "hpc_iso_architecture.json"
            with open(iso_file, 'w') as f:
                json.dump(iso_architecture, f, indent=2)
            
            # Generate recommendations
            recommendations = self._generate_hpc_recommendations(hardware_profile)
            
            return {
                'status': 'success',
                'hardware_profile': asdict(hardware_profile),
                'iso_architecture': iso_architecture,
                'recommendations': recommendations,
                'optimization_summary': self._generate_optimization_summary(hardware_profile)
            }
            
        except Exception as e:
            self.logger.error(f"HPC hardware detection failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _generate_hpc_recommendations(self, profile: HPCHardwareProfile) -> List[str]:
        """Generate HPC-specific optimization recommendations"""
        recommendations = []
        
        # Tesla GPU recommendations
        if profile.gpu_devices:
            for gpu in profile.gpu_devices:
                if 'Tesla K' in gpu.get('name', ''):
                    recommendations.append(f"Install NVIDIA driver 470.x LTS for {gpu['name']}")
                    recommendations.append("Use CUDA 11.8 for maximum Kepler compatibility")
                    recommendations.append("Enable ECC memory on Tesla GPUs for scientific accuracy")
        
        # Xeon Phi recommendations
        if profile.xeon_phi_devices:
            for phi in profile.xeon_phi_devices:
                if phi.get('has_mcdram', False):
                    recommendations.append("Configure MCDRAM in flat mode for maximum memory")
                    recommendations.append("Use numactl for MCDRAM memory allocation")
                if phi.get('avx512_support', False):
                    recommendations.append("Enable AVX-512 compilation for Xeon Phi workloads")
            recommendations.append("Install Intel MPSS for Xeon Phi support")
        
        # Memory recommendations
        if profile.memory_architecture.get('numa_aware', False):
            recommendations.append("Enable NUMA-aware memory allocation for HPC workloads")
            recommendations.append("Use thread affinity for optimal memory bandwidth")
        
        # General HPC recommendations
        if profile.cpu_cores >= 16:
            recommendations.append("Use OpenMP for shared-memory parallelization")
            recommendations.append("Configure MPI for distributed computing")
        
        # Storage recommendations
        if any('NVMe' in controller for controller in profile.storage_controllers):
            recommendations.append("Use NVMe storage for HPC scratch space")
            recommendations.append("Configure high-performance filesystem (Lustre/GPFS)")
        
        # Performance recommendations
        recommendations.append("Compile with profile-guided optimization (PGO)")
        recommendations.append("Use Intel MKL for optimized mathematical operations")
        recommendations.append("Enable transparent huge pages for large datasets")
        
        return recommendations
    
    def _generate_optimization_summary(self, profile: HPCHardwareProfile) -> Dict[str, Any]:
        """Generate optimization summary for HPC workloads"""
        summary = {
            'cpu_optimization': 'standard',
            'memory_optimization': 'standard',
            'gpu_optimization': 'none',
            'phi_optimization': 'none',
            'compilation_targets': [],
            'runtime_optimizations': []
        }
        
        # CPU optimization level
        if profile.optimization_flags.get('performance_profile') == 'hpc_optimized':
            summary['cpu_optimization'] = 'hpc_optimized'
            
        # Memory optimization
        if profile.memory_architecture.get('numa_aware', False):
            summary['memory_optimization'] = 'numa_aware'
        if profile.memory_architecture.get('has_mcdram', False):
            summary['memory_optimization'] = 'mcdram_hybrid'
        
        # GPU optimization
        if profile.gpu_devices:
            if any('Kepler' in gpu.get('architecture', '') for gpu in profile.gpu_devices):
                summary['gpu_optimization'] = 'kepler_legacy'
            else:
                summary['gpu_optimization'] = 'modern_cuda'
        
        # Xeon Phi optimization
        if profile.xeon_phi_devices:
            if any('Knights Landing' in device.get('architecture', '') 
                  for device in profile.xeon_phi_devices):
                summary['phi_optimization'] = 'knights_landing'
            else:
                summary['phi_optimization'] = 'generic_phi'
        
        # Compilation targets
        targets = []
        if profile.optimization_flags.get('compiler_flags'):
            if '-mavx512f' in profile.optimization_flags['compiler_flags']:
                targets.append('AVX-512')
            elif '-mavx2' in profile.optimization_flags['compiler_flags']:
                targets.append('AVX2')
        summary['compilation_targets'] = targets
        
        # Runtime optimizations
        runtime_opts = []
        if profile.cuda_compatibility.get('has_cuda_gpus', False):
            runtime_opts.append('CUDA runtime optimization')
        if profile.phi_compatibility.get('has_phi_devices', False):
            runtime_opts.append('Xeon Phi runtime optimization')
        if profile.memory_architecture.get('numa_aware', False):
            runtime_opts.append('NUMA-aware scheduling')
        summary['runtime_optimizations'] = runtime_opts
        
        return summary


if __name__ == '__main__':
    # Test HPC hardware detection
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    workspace = Path("/tmp/hpc_test")
    workspace.mkdir(exist_ok=True)
    
    config = {
        "hpc_mode": True,
        "target_hardware": ["Tesla K40/K80", "Xeon Phi", "Dell T30"],
        "iso_size_gb": 32
    }
    
    detector = HPCHardwareDetector(workspace, config)
    result = detector.execute()
    
    print(f"\n=== HPC Detection Result ===")
    print(f"Status: {result['status']}")
    
    if result['status'] == 'success':
        hw = result['hardware_profile']
        print(f"Server: {hw['server_model']}")
        print(f"CPU: {hw['cpu_model']} ({hw['cpu_cores']} cores)")
        print(f"Memory: {hw['memory_gb']}GB")
        print(f"Tesla GPUs: {len(hw['gpu_devices'])}")
        print(f"Xeon Phi: {len(hw['xeon_phi_devices'])}")
        
        print(f"\nOptimization Summary:")
        opt_summary = result['optimization_summary']
        print(f"  CPU: {opt_summary['cpu_optimization']}")
        print(f"  Memory: {opt_summary['memory_optimization']}")
        print(f"  GPU: {opt_summary['gpu_optimization']}")
        print(f"  Phi: {opt_summary['phi_optimization']}")
        
        print(f"\nRecommendations: {len(result['recommendations'])}")
        for i, rec in enumerate(result['recommendations'][:5], 1):
            print(f"  {i}. {rec}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
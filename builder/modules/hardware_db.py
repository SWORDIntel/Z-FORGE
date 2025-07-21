#!/usr/bin/env python3
"""
Hardware Detection Database for Z-FORGE
Detects hardware and provides optimal configurations
"""
import re
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class HardwareProfile:
    """Hardware profile with optimal settings"""
    name: str
    vendor: str
    model: str
    type: str  # server, workstation, laptop
    optimal_settings: Dict[str, Any]
    known_issues: List[str]
    special_features: List[str]
    tested: bool = False

class HardwareDatabase:
    """Database of known hardware with optimal configurations"""
    
    # Dell PowerEdge Servers
    DELL_SERVERS = {
        "PowerEdge R730": HardwareProfile(
            name="Dell PowerEdge R730",
            vendor="Dell Inc.",
            model="PowerEdge R730",
            type="server",
            optimal_settings={
                "zfs": {
                    "arc_max_percent": 50,
                    "l2arc_write_max": "32M",
                    "l2arc_write_boost": "64M",
                    "zfs_txg_timeout": 5
                },
                "kernel": {
                    "vm_swappiness": 10,
                    "transparent_hugepages": "never",
                    "numa_balancing": 1
                },
                "cpu": {
                    "governor": "performance",
                    "energy_perf_bias": "performance"
                },
                "perc_controller": {
                    "mode": "IT",  # Recommended for ZFS
                    "cache": "disabled",
                    "bbu": "check_status"
                }
            },
            known_issues=[
                "PERC H730 needs IT mode for ZFS",
                "iDRAC may need firmware update for Linux",
                "Broadcom NIC may need driver update"
            ],
            special_features=[
                "iDRAC remote management",
                "Redundant power supplies",
                "Hot-swap drives",
                "IPMI support"
            ],
            tested=True
        ),
        "PowerEdge R740": HardwareProfile(
            name="Dell PowerEdge R740",
            vendor="Dell Inc.",
            model="PowerEdge R740",
            type="server",
            optimal_settings={
                "zfs": {
                    "arc_max_percent": 60,
                    "l2arc_write_max": "64M",
                    "recordsize": "128K",
                    "ashift": 12
                },
                "kernel": {
                    "vm_swappiness": 5,
                    "transparent_hugepages": "never"
                },
                "cpu": {
                    "governor": "performance",
                    "intel_pstate": "disable"
                }
            },
            known_issues=[
                "BOSS card conflicts with some Linux installers",
                "NVMe drives need proper cooling"
            ],
            special_features=[
                "NVMe support",
                "GPU support",
                "iDRAC9",
                "OpenManage support"
            ],
            tested=True
        ),
        "PowerEdge R640": HardwareProfile(
            name="Dell PowerEdge R640",
            vendor="Dell Inc.",
            model="PowerEdge R640",
            type="server",
            optimal_settings={
                "zfs": {
                    "arc_max_percent": 50,
                    "compression": "lz4",
                    "sync": "standard"
                },
                "kernel": {
                    "vm_swappiness": 10,
                    "numa_balancing": 1
                },
                "network": {
                    "ring_buffer_size": 4096,
                    "interrupt_coalescing": "adaptive"
                }
            },
            known_issues=[
                "Some BIOS versions have Linux compatibility issues"
            ],
            special_features=[
                "High density 1U form factor",
                "NVMe ready",
                "25GbE networking option"
            ],
            tested=True
        )
    }
    
    # HP/HPE Servers
    HP_SERVERS = {
        "ProLiant DL380 Gen10": HardwareProfile(
            name="HPE ProLiant DL380 Gen10",
            vendor="HPE",
            model="ProLiant DL380 Gen10",
            type="server",
            optimal_settings={
                "zfs": {
                    "arc_max_percent": 55,
                    "l2arc_noprefetch": 1,
                    "zfs_vdev_cache_size": 0
                },
                "kernel": {
                    "vm_swappiness": 10,
                    "kernel.numa_balancing": 1
                },
                "storage": {
                    "smart_array": "hba_mode",
                    "cache_ratio": "50_50"
                }
            },
            known_issues=[
                "Smart Array needs HBA mode for ZFS",
                "iLO may need license for advanced features"
            ],
            special_features=[
                "iLO 5 management",
                "Persistent memory support",
                "InfoSight analytics"
            ],
            tested=True
        )
    }
    
    # Supermicro Servers
    SUPERMICRO_SERVERS = {
        "X11DPH-T": HardwareProfile(
            name="Supermicro X11DPH-T",
            vendor="Supermicro",
            model="X11DPH-T",
            type="server",
            optimal_settings={
                "zfs": {
                    "arc_max_percent": 70,
                    "l2arc_write_max": "64M",
                    "metaslab_debug_load": 0
                },
                "kernel": {
                    "vm_swappiness": 1,
                    "vm_dirty_ratio": 10
                },
                "bios": {
                    "power_mode": "performance",
                    "c_states": "disabled"
                }
            },
            known_issues=[
                "IPMI may need Java for web interface",
                "Some NVMe slots share PCIe lanes"
            ],
            special_features=[
                "Dual 10GbE",
                "Up to 4 GPU support",
                "16 DIMM slots"
            ],
            tested=True
        )
    }
    
    # Consumer/Prosumer Hardware
    CONSUMER_HARDWARE = {
        # Dell Precision Workstations
        "Precision G8": HardwareProfile(
            name="Dell Precision Microstation G8",
            vendor="Dell Inc.",
            model="Precision G8",
            type="workstation",
            optimal_settings={
                "zfs": {
                    "arc_max_percent": 30,
                    "l2arc_write_max": "32M",
                    "zfs_txg_timeout": "5",
                    "zfs_vdev_async_write_max_active": "10",
                    "zfs_vdev_sync_write_max_active": "10",
                    # Intel 750 optimizations
                    "zfs_vdev_queue_depth_pct": "300",
                    "zil_slog_bulk": "786432"
                },
                "kernel": {
                    "vm_swappiness": 1,
                    "transparent_hugepages": "never",
                    "nmi_watchdog": "0",
                    "intel_idle.max_cstate": "1",
                    # Intel 750 NVMe optimizations
                    "nvme_core.io_timeout": "30",
                    "nvme_core.default_ps_max_latency_us": "0"
                },
                "cpu": {
                    "governor": "performance",
                    "energy_perf_bias": "performance"
                },
                "nvme": {
                    "intel_750": {
                        "power_management": "disabled",
                        "write_cache": "enabled",
                        "volatile_write_cache": "enabled"
                    }
                }
            },
            known_issues=[
                "Intel 750 may need BIOS PCIe power management disabled",
                "Ensure adequate cooling for Intel 750 NVMe",
                "May require BIOS update for NVMe boot support"
            ],
            special_features=[
                "Intel 750 Series PCIe SSD optimization",
                "Professional GPU support (Quadro/RTX)",
                "ECC memory support",
                "Dual NVMe capability",
                "Thunderbolt support"
            ],
            tested=True
        ),
        "AMD Ryzen 9 5950X": HardwareProfile(
            name="AMD Ryzen 9 5950X System",
            vendor="AMD",
            model="Ryzen 9 5950X",
            type="workstation",
            optimal_settings={
                "zfs": {
                    "arc_max_percent": 50,
                    "l2arc_write_max": "8M"
                },
                "kernel": {
                    "vm_swappiness": 10,
                    "amd_pstate": "active"
                },
                "cpu": {
                    "governor": "schedutil",
                    "boost": "enabled"
                }
            },
            known_issues=[
                "fTPM may cause stuttering",
                "USB issues on some chipsets"
            ],
            special_features=[
                "16 cores/32 threads",
                "PCIe 4.0 support",
                "ECC memory support (unofficial)"
            ],
            tested=True
        ),
        "Intel Core i9-13900K": HardwareProfile(
            name="Intel Core i9-13900K System",
            vendor="Intel",
            model="Core i9-13900K",
            type="workstation",
            optimal_settings={
                "zfs": {
                    "arc_max_percent": 40,
                    "primarycache": "all"
                },
                "kernel": {
                    "vm_swappiness": 10,
                    "intel_pstate": "active"
                },
                "cpu": {
                    "governor": "powersave",
                    "turbo": "enabled"
                }
            },
            known_issues=[
                "High power consumption",
                "Needs good cooling"
            ],
            special_features=[
                "24 cores (8P+16E)",
                "DDR5 support",
                "PCIe 5.0"
            ],
            tested=True
        )
    }
    
    def __init__(self):
        self.profiles = {}
        self._load_all_profiles()
        self.detected_hardware = None
    
    def _load_all_profiles(self):
        """Load all hardware profiles"""
        # Combine all profiles
        for profile_dict in [self.DELL_SERVERS, self.HP_SERVERS, 
                           self.SUPERMICRO_SERVERS, self.CONSUMER_HARDWARE]:
            self.profiles.update(profile_dict)
    
    def detect_hardware(self) -> Dict[str, Any]:
        """Detect current system hardware"""
        hardware_info = {
            "system": self._detect_system_info(),
            "cpu": self._detect_cpu(),
            "memory": self._detect_memory(),
            "storage": self._detect_storage(),
            "network": self._detect_network(),
            "gpu": self._detect_gpu()
        }
        
        self.detected_hardware = hardware_info
        return hardware_info
    
    def _detect_system_info(self) -> Dict[str, str]:
        """Detect system manufacturer and model"""
        info = {}
        
        try:
            # Try DMI info first
            vendor = subprocess.check_output(
                ["dmidecode", "-s", "system-manufacturer"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            model = subprocess.check_output(
                ["dmidecode", "-s", "system-product-name"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            
            info["vendor"] = vendor
            info["model"] = model
            
            # Get BIOS info
            bios_version = subprocess.check_output(
                ["dmidecode", "-s", "bios-version"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            info["bios_version"] = bios_version
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to /sys/class/dmi
            try:
                vendor_path = Path("/sys/class/dmi/id/sys_vendor")
                model_path = Path("/sys/class/dmi/id/product_name")
                
                if vendor_path.exists():
                    info["vendor"] = vendor_path.read_text().strip()
                if model_path.exists():
                    info["model"] = model_path.read_text().strip()
                    
            except Exception as e:
                logger.warning(f"Could not detect system info: {e}")
        
        return info
    
    def _detect_cpu(self) -> Dict[str, Any]:
        """Detect CPU information"""
        cpu_info = {}
        
        try:
            # Parse /proc/cpuinfo
            with open("/proc/cpuinfo") as f:
                cpuinfo = f.read()
            
            # Get CPU model
            model_match = re.search(r"model name\s*:\s*(.+)", cpuinfo)
            if model_match:
                cpu_info["model"] = model_match.group(1).strip()
            
            # Count cores
            cores = len(re.findall(r"processor\s*:", cpuinfo))
            cpu_info["cores"] = cores
            
            # Detect CPU vendor
            vendor_match = re.search(r"vendor_id\s*:\s*(.+)", cpuinfo)
            if vendor_match:
                cpu_info["vendor"] = vendor_match.group(1).strip()
            
            # Check for specific features
            cpu_info["features"] = []
            if "avx2" in cpuinfo:
                cpu_info["features"].append("AVX2")
            if "aes" in cpuinfo:
                cpu_info["features"].append("AES-NI")
            if " ht " in cpuinfo or "hypervisor" in cpuinfo:
                cpu_info["features"].append("HyperThreading")
                
        except Exception as e:
            logger.warning(f"Could not detect CPU info: {e}")
        
        return cpu_info
    
    def _detect_memory(self) -> Dict[str, Any]:
        """Detect memory information"""
        mem_info = {}
        
        try:
            # Get total memory
            with open("/proc/meminfo") as f:
                meminfo = f.read()
            
            total_match = re.search(r"MemTotal:\s*(\d+)", meminfo)
            if total_match:
                mem_info["total_gb"] = int(total_match.group(1)) // (1024 * 1024)
            
            # Try to get memory speed and type
            try:
                dmidecode = subprocess.check_output(
                    ["dmidecode", "-t", "memory"],
                    stderr=subprocess.DEVNULL
                ).decode()
                
                # Extract memory type
                if "DDR5" in dmidecode:
                    mem_info["type"] = "DDR5"
                elif "DDR4" in dmidecode:
                    mem_info["type"] = "DDR4"
                elif "DDR3" in dmidecode:
                    mem_info["type"] = "DDR3"
                
                # Extract speed
                speed_match = re.search(r"Speed:\s*(\d+)\s*MHz", dmidecode)
                if speed_match:
                    mem_info["speed_mhz"] = int(speed_match.group(1))
                    
            except:
                pass
                
        except Exception as e:
            logger.warning(f"Could not detect memory info: {e}")
        
        return mem_info
    
    def _detect_storage(self) -> List[Dict[str, Any]]:
        """Detect storage devices"""
        storage_devices = []
        
        try:
            # Use lsblk to get block devices
            lsblk_output = subprocess.check_output(
                ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MODEL,ROTA,SERIAL"],
                stderr=subprocess.DEVNULL
            ).decode()
            
            lsblk_data = json.loads(lsblk_output)
            
            for device in lsblk_data.get("blockdevices", []):
                if device["type"] == "disk":
                    dev_info = {
                        "name": device["name"],
                        "size": device["size"],
                        "model": device.get("model", "Unknown"),
                        "rotational": device.get("rota", "1") == "1",
                        "serial": device.get("serial", "")
                    }
                    
                    # Detect interface type
                    if device["name"].startswith("nvme"):
                        dev_info["interface"] = "NVMe"
                        
                        # Check for Intel 750 Series
                        if "INTEL SSDPE" in dev_info["model"].upper() or "750" in dev_info["model"]:
                            dev_info["special"] = "Intel 750 Series"
                            dev_info["optimizations"] = {
                                "queue_depth": 256,
                                "io_poll": True,
                                "io_poll_delay": 0
                            }
                            
                    elif device["name"].startswith("sd"):
                        # Could be SATA or SAS
                        dev_info["interface"] = "SATA/SAS"
                    
                    storage_devices.append(dev_info)
                    
        except Exception as e:
            logger.warning(f"Could not detect storage devices: {e}")
        
        return storage_devices
    
    def _detect_network(self) -> List[Dict[str, Any]]:
        """Detect network interfaces"""
        network_devices = []
        
        try:
            # Get network interfaces
            ip_output = subprocess.check_output(
                ["ip", "-j", "link", "show"],
                stderr=subprocess.DEVNULL
            ).decode()
            
            interfaces = json.loads(ip_output)
            
            for iface in interfaces:
                if iface["ifname"] not in ["lo", "docker0", "virbr0"]:
                    dev_info = {
                        "name": iface["ifname"],
                        "mac": iface.get("address", ""),
                        "state": iface.get("operstate", "unknown")
                    }
                    
                    # Try to get speed
                    try:
                        ethtool = subprocess.check_output(
                            ["ethtool", iface["ifname"]],
                            stderr=subprocess.DEVNULL
                        ).decode()
                        
                        speed_match = re.search(r"Speed:\s*(\d+)Mb/s", ethtool)
                        if speed_match:
                            dev_info["speed_mbps"] = int(speed_match.group(1))
                            
                    except:
                        pass
                    
                    network_devices.append(dev_info)
                    
        except Exception as e:
            logger.warning(f"Could not detect network devices: {e}")
        
        return network_devices
    
    def _detect_gpu(self) -> List[Dict[str, Any]]:
        """Detect GPU devices"""
        gpu_devices = []
        
        try:
            lspci_output = subprocess.check_output(
                ["lspci", "-nn"],
                stderr=subprocess.DEVNULL
            ).decode()
            
            # Look for VGA controllers
            for line in lspci_output.split('\n'):
                if "VGA compatible controller" in line or "3D controller" in line:
                    gpu_info = {"pci_info": line}
                    
                    if "NVIDIA" in line:
                        gpu_info["vendor"] = "NVIDIA"
                    elif "AMD" in line or "ATI" in line:
                        gpu_info["vendor"] = "AMD"
                    elif "Intel" in line:
                        gpu_info["vendor"] = "Intel"
                    
                    gpu_devices.append(gpu_info)
                    
        except Exception as e:
            logger.warning(f"Could not detect GPU devices: {e}")
        
        return gpu_devices
    
    def get_hardware_profile(self, system_info: Dict[str, str] = None) -> Optional[HardwareProfile]:
        """Get matching hardware profile"""
        if not system_info:
            system_info = self._detect_system_info()
        
        # Try exact model match
        model = system_info.get("model", "")
        for profile_name, profile in self.profiles.items():
            if profile.model in model or model in profile.model:
                logger.info(f"Found exact hardware match: {profile_name}")
                return profile
        
        # Try vendor match with fuzzy model
        vendor = system_info.get("vendor", "")
        for profile_name, profile in self.profiles.items():
            if profile.vendor.lower() in vendor.lower():
                # Fuzzy match on model
                if any(part in model for part in profile.model.split()):
                    logger.info(f"Found partial hardware match: {profile_name}")
                    return profile
        
        logger.info("No specific hardware profile found, using defaults")
        return None
    
    def get_optimal_settings(self) -> Dict[str, Any]:
        """Get optimal settings for detected hardware"""
        if not self.detected_hardware:
            self.detect_hardware()
        
        # Get hardware profile
        profile = self.get_hardware_profile(self.detected_hardware["system"])
        
        if profile:
            return profile.optimal_settings
        else:
            # Return generic optimized settings
            return self._get_generic_settings()
    
    def _get_generic_settings(self) -> Dict[str, Any]:
        """Get generic optimized settings"""
        settings = {
            "zfs": {
                "arc_max_percent": 50,
                "l2arc_write_max": "8M",
                "compression": "lz4"
            },
            "kernel": {
                "vm_swappiness": 10,
                "transparent_hugepages": "madvise"
            }
        }
        
        # Adjust based on detected hardware
        if self.detected_hardware:
            # Adjust ARC based on memory
            total_mem = self.detected_hardware["memory"].get("total_gb", 16)
            if total_mem >= 64:
                settings["zfs"]["arc_max_percent"] = 60
            elif total_mem >= 32:
                settings["zfs"]["arc_max_percent"] = 50
            else:
                settings["zfs"]["arc_max_percent"] = 40
            
            # Adjust based on CPU
            cpu_vendor = self.detected_hardware["cpu"].get("vendor", "")
            if cpu_vendor == "GenuineIntel":
                settings["kernel"]["intel_pstate"] = "active"
            elif cpu_vendor == "AuthenticAMD":
                settings["kernel"]["amd_pstate"] = "active"
        
        return settings
    
    def generate_report(self) -> str:
        """Generate hardware detection report"""
        if not self.detected_hardware:
            self.detect_hardware()
        
        report = ["Z-FORGE Hardware Detection Report", "=" * 50, ""]
        
        # System info
        sys_info = self.detected_hardware["system"]
        report.append(f"System: {sys_info.get('vendor', 'Unknown')} {sys_info.get('model', 'Unknown')}")
        report.append(f"BIOS: {sys_info.get('bios_version', 'Unknown')}")
        report.append("")
        
        # CPU info
        cpu_info = self.detected_hardware["cpu"]
        report.append(f"CPU: {cpu_info.get('model', 'Unknown')}")
        report.append(f"Cores: {cpu_info.get('cores', 'Unknown')}")
        report.append(f"Features: {', '.join(cpu_info.get('features', []))}")
        report.append("")
        
        # Memory info
        mem_info = self.detected_hardware["memory"]
        report.append(f"Memory: {mem_info.get('total_gb', 'Unknown')} GB")
        if "type" in mem_info:
            report.append(f"Type: {mem_info['type']} @ {mem_info.get('speed_mhz', 'Unknown')} MHz")
        report.append("")
        
        # Storage info
        report.append("Storage Devices:")
        for dev in self.detected_hardware["storage"]:
            dev_type = "SSD" if not dev["rotational"] else "HDD"
            report.append(f"  - {dev['name']}: {dev['size']} {dev_type} ({dev['model']})")
        report.append("")
        
        # Network info
        report.append("Network Interfaces:")
        for dev in self.detected_hardware["network"]:
            speed = f"{dev.get('speed_mbps', 'Unknown')} Mbps" if "speed_mbps" in dev else "Unknown"
            report.append(f"  - {dev['name']}: {speed} ({dev['state']})")
        report.append("")
        
        # GPU info
        if self.detected_hardware["gpu"]:
            report.append("GPU Devices:")
            for gpu in self.detected_hardware["gpu"]:
                report.append(f"  - {gpu.get('vendor', 'Unknown')}: {gpu['pci_info']}")
            report.append("")
        
        # Hardware profile match
        profile = self.get_hardware_profile(sys_info)
        if profile:
            report.append(f"Matched Profile: {profile.name}")
            report.append("Known Issues:")
            for issue in profile.known_issues:
                report.append(f"  - {issue}")
            report.append("")
            report.append("Special Features:")
            for feature in profile.special_features:
                report.append(f"  - {feature}")
        else:
            report.append("No specific hardware profile matched.")
            report.append("Using generic optimization settings.")
        
        return "\n".join(report)


def main():
    """CLI for hardware detection"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Z-FORGE Hardware Detection")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--settings", action="store_true", 
                       help="Show optimal settings")
    parser.add_argument("--report", action="store_true",
                       help="Generate full report")
    
    args = parser.parse_args()
    
    hw_db = HardwareDatabase()
    
    if args.json:
        hw_info = hw_db.detect_hardware()
        print(json.dumps(hw_info, indent=2))
    elif args.settings:
        settings = hw_db.get_optimal_settings()
        print(json.dumps(settings, indent=2))
    elif args.report:
        print(hw_db.generate_report())
    else:
        # Default: show summary
        hw_db.detect_hardware()
        sys_info = hw_db.detected_hardware["system"]
        print(f"System: {sys_info.get('vendor', 'Unknown')} {sys_info.get('model', 'Unknown')}")
        
        profile = hw_db.get_hardware_profile(sys_info)
        if profile:
            print(f"Profile: {profile.name}")
            print(f"Tested: {'Yes' if profile.tested else 'No'}")
        else:
            print("Profile: Generic (no specific match)")


if __name__ == "__main__":
    main()
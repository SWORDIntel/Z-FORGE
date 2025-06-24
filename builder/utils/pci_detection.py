#!/usr/bin/env python3
"""
PCI Detection Utilities for Z-FORGE
Automatically detects PCI devices and provides optimal kernel parameters
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

class PCIDetector:
    """Detects PCI devices and provides optimized kernel parameters"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def detect_nvme_pci_paths(self) -> List[Dict[str, str]]:
        """
        Detect all NVMe devices and their PCI paths
        
        Returns:
            List of dicts containing device info and PCI paths
        """
        nvme_devices = []
        
        try:
            # Use lspci to find NVMe controllers
            result = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
            
            for line in result.stdout.splitlines():
                # Look for NVMe controllers (class code [0108])
                if '[0108]' in line or 'Non-Volatile memory controller' in line:
                    # Extract PCI address (e.g., "02:00.0")
                    pci_addr = line.split()[0]
                    
                    # Get detailed info
                    detail_result = subprocess.run(
                        ['lspci', '-vvs', pci_addr], 
                        capture_output=True, 
                        text=True
                    )
                    
                    device_info = {
                        'pci_address': pci_addr,
                        'description': line,
                        'vendor': self._extract_vendor(detail_result.stdout),
                        'model': self._extract_model(line),
                        'numa_node': self._get_numa_node(pci_addr),
                        'driver': self._get_driver(pci_addr)
                    }
                    
                    # Get associated block device if any
                    block_device = self._find_block_device(pci_addr)
                    if block_device:
                        device_info['block_device'] = block_device
                    
                    nvme_devices.append(device_info)
                    
        except Exception as e:
            self.logger.error(f"Failed to detect NVMe devices: {e}")
            
        return nvme_devices
    
    def detect_dell_server_model(self) -> Optional[str]:
        """
        Detect Dell server model from DMI information
        
        Returns:
            Server model string or None
        """
        try:
            if Path("/sys/class/dmi/id/product_name").exists():
                with open("/sys/class/dmi/id/product_name", "r") as f:
                    product_name = f.read().strip()
                    
                # Check for specific Dell models
                if "PowerEdge R730xd" in product_name:
                    return "R730xd"
                elif "PowerEdge R730" in product_name:
                    return "R730"
                elif "PowerEdge R420" in product_name:
                    return "R420"
                elif "PowerEdge" in product_name:
                    # Extract model from string like "PowerEdge R640"
                    match = re.search(r'PowerEdge\s+(\w+)', product_name)
                    if match:
                        return match.group(1)
                        
        except Exception as e:
            self.logger.debug(f"Could not detect server model: {e}")
            
        return None
    
    def get_r730xd_nvme_kernel_params(self) -> List[str]:
        """
        Get optimal kernel parameters for R730xd with NVMe
        
        The R730xd often has issues with PCIe allocation when using
        NVMe cards in certain slots. This provides the necessary
        kernel parameters to fix those issues.
        
        Returns:
            List of kernel parameters
        """
        params = []
        nvme_devices = self.detect_nvme_pci_paths()
        
        if nvme_devices:
            # R730xd specific: Enable PCIe resource reallocation
            # This is often needed when NVMe cards are in slots 6-8
            params.append("pci=realloc=on")
            
            # Check if any NVMe devices are on high bus numbers
            # R730xd slots 6-8 are typically on bus 80+ 
            for device in nvme_devices:
                bus_num = int(device['pci_address'].split(':')[0], 16)
                if bus_num > 0x40:  # Bus number > 64
                    # Need to enable 64-bit BARs for these devices
                    params.append("pci=assign-busses")
                    params.append("pcie_aspm=off")  # Disable ASPM for stability
                    break
            
            # If multiple NVMe devices, ensure proper NUMA allocation
            if len(nvme_devices) > 1:
                params.append("numa_balancing=enable")
                
        return params
    
    def get_optimal_kernel_params(self) -> List[str]:
        """
        Get optimal kernel parameters based on detected hardware
        
        Returns:
            List of kernel parameters
        """
        params = []
        
        # Detect server model
        server_model = self.detect_dell_server_model()
        
        if server_model == "R730xd":
            # R730xd specific optimizations
            params.extend(self.get_r730xd_nvme_kernel_params())
            params.append("intel_iommu=on")  # Enable VT-d
            params.append("iommu=pt")  # Passthrough mode
            
        elif server_model == "R420":
            # R420 specific optimizations
            params.append("intel_iommu=on")
            nvme_devices = self.detect_nvme_pci_paths()
            if nvme_devices:
                params.append("pci=realloc=on")
                
        else:
            # Generic optimizations for NVMe
            nvme_devices = self.detect_nvme_pci_paths()
            if nvme_devices:
                params.append("nvme_core.default_ps_max_latency_us=0")
                
        return params
    
    def get_pci_slot_mapping(self) -> Dict[str, str]:
        """
        Get mapping of PCI addresses to physical slot numbers
        
        This is Dell-specific and based on common configurations
        
        Returns:
            Dict mapping PCI addresses to slot descriptions
        """
        server_model = self.detect_dell_server_model()
        
        if server_model == "R730xd":
            # R730xd typical slot mapping
            return {
                "03:00": "Slot 1 (x16)",
                "02:00": "Slot 2 (x8)", 
                "01:00": "Slot 3 (x16)",
                "82:00": "Slot 6 (x8)",
                "83:00": "Slot 7 (x8)",
                "84:00": "Slot 8 (x8)"
            }
        elif server_model == "R420":
            # R420 typical slot mapping
            return {
                "03:00": "Slot 1 (x16)",
                "04:00": "Slot 2 (x8)"
            }
        else:
            return {}
    
    def _extract_vendor(self, lspci_output: str) -> str:
        """Extract vendor from lspci -v output"""
        for line in lspci_output.splitlines():
            if "Subsystem:" in line:
                return line.split("Subsystem:")[1].strip()
        return "Unknown"
    
    def _extract_model(self, lspci_line: str) -> str:
        """Extract model from lspci line"""
        # Remove PCI address and class code
        parts = lspci_line.split(']')
        if len(parts) > 1:
            return parts[1].strip()
        return "Unknown"
    
    def _get_numa_node(self, pci_addr: str) -> Optional[int]:
        """Get NUMA node for PCI device"""
        try:
            numa_path = f"/sys/bus/pci/devices/0000:{pci_addr}/numa_node"
            if Path(numa_path).exists():
                with open(numa_path, 'r') as f:
                    return int(f.read().strip())
        except:
            pass
        return None
    
    def _get_driver(self, pci_addr: str) -> Optional[str]:
        """Get driver for PCI device"""
        try:
            driver_path = f"/sys/bus/pci/devices/0000:{pci_addr}/driver"
            if Path(driver_path).exists():
                return Path(driver_path).resolve().name
        except:
            pass
        return None
    
    def _find_block_device(self, pci_addr: str) -> Optional[str]:
        """Find block device associated with PCI address"""
        try:
            # Look for NVMe devices under this PCI address
            nvme_path = f"/sys/bus/pci/devices/0000:{pci_addr}/nvme"
            if Path(nvme_path).exists():
                for nvme_dev in Path(nvme_path).iterdir():
                    if nvme_dev.is_dir():
                        return f"/dev/{nvme_dev.name}"
        except:
            pass
        return None
    
    def generate_report(self) -> str:
        """Generate a report of detected PCI devices and recommendations"""
        
        report = ["PCI Device Detection Report", "=" * 50, ""]
        
        # Server model
        server_model = self.detect_dell_server_model()
        if server_model:
            report.append(f"Detected Server: Dell PowerEdge {server_model}")
        else:
            report.append("Server Model: Unknown")
        report.append("")
        
        # NVMe devices
        nvme_devices = self.detect_nvme_pci_paths()
        if nvme_devices:
            report.append("NVMe Devices Detected:")
            report.append("-" * 30)
            
            slot_mapping = self.get_pci_slot_mapping()
            
            for device in nvme_devices:
                report.append(f"  PCI Address: {device['pci_address']}")
                
                # Check if we know the physical slot
                slot_prefix = device['pci_address'].split('.')[0]
                if slot_prefix in slot_mapping:
                    report.append(f"  Physical Location: {slot_mapping[slot_prefix]}")
                
                report.append(f"  Model: {device['model']}")
                if device.get('block_device'):
                    report.append(f"  Block Device: {device['block_device']}")
                if device.get('numa_node') is not None:
                    report.append(f"  NUMA Node: {device['numa_node']}")
                report.append("")
        else:
            report.append("No NVMe devices detected")
            report.append("")
        
        # Recommended kernel parameters
        kernel_params = self.get_optimal_kernel_params()
        if kernel_params:
            report.append("Recommended Kernel Parameters:")
            report.append("-" * 30)
            for param in kernel_params:
                report.append(f"  {param}")
            report.append("")
            report.append("Full kernel command line addition:")
            report.append(f"  {' '.join(kernel_params)}")
        
        return '\n'.join(report)


# CLI interface
if __name__ == "__main__":
    import sys
    
    detector = PCIDetector()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--kernel-params":
        # Just output kernel parameters
        params = detector.get_optimal_kernel_params()
        if params:
            print(' '.join(params))
    else:
        # Output full report
        print(detector.generate_report())
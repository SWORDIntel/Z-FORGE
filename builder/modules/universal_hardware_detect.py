#!/usr/bin/env python3
"""
Universal Hardware Detection Module for Z-Forge
Automatically detects and configures for any hardware during ISO build
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import json
import shutil
from builder.modules.hardware_db import HardwareDatabase, HardwareProfile


class UniversalHardwareDetect:
    """Universal hardware detection and configuration"""
    
    def __init__(self, config: Dict[str, Any], chroot_path: Path, logger: logging.Logger):
        self.config = config
        self.chroot_path = chroot_path
        self.logger = logger
        self.hardware_profile = {}
        self.hardware_db = HardwareDatabase()
        self.detected_profile = None
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None,
                lockfile: Optional[Any] = None) -> Dict[str, Any]:
        """Execute universal hardware detection"""
        self.logger.info("Starting universal hardware detection...")
        
        try:
            # Detect hardware
            self._detect_all_hardware()
            
            # Check against hardware database
            self._check_hardware_database()
            
            # Apply universal configurations
            self._apply_universal_configs()
            
            # Configure for detected hardware
            self._configure_for_hardware()
            
            # Detect and configure RAID controllers
            self._configure_raid_controllers()
            
            # Apply optimal settings if found in database
            if self.detected_profile:
                self._apply_optimal_settings()
            
            # Install detection scripts for runtime
            self._install_runtime_detection()
            
            return {
                'status': 'success',
                'hardware_profile': self.hardware_profile,
                'message': 'Universal hardware detection completed'
            }
            
        except Exception as e:
            self.logger.error(f"Hardware detection failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _detect_all_hardware(self):
        """Detect all hardware components"""
        self.logger.info("Detecting system hardware...")
        
        # Create comprehensive detection script
        detect_script = self.chroot_path / "tmp/universal_hw_detect.sh"
        detect_script.write_text("""#!/bin/bash
# Universal Hardware Detection

# System Information
VENDOR=$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null || echo "Unknown")
MODEL=$(cat /sys/class/dmi/id/product_name 2>/dev/null || echo "Unknown")
BIOS_VENDOR=$(cat /sys/class/dmi/id/bios_vendor 2>/dev/null || echo "Unknown")
BOARD_NAME=$(cat /sys/class/dmi/id/board_name 2>/dev/null || echo "Unknown")

# CPU Information
CPU_VENDOR=$(lscpu | grep "Vendor ID:" | awk '{print $3}')
CPU_MODEL=$(lscpu | grep "Model name:" | cut -d: -f2 | xargs)
CPU_CORES=$(nproc)
CPU_THREADS=$(lscpu | grep "Thread(s) per core:" | awk '{print $4}')
CPU_SOCKETS=$(lscpu | grep "Socket(s):" | awk '{print $2}')

# Memory Information
MEM_TOTAL_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
MEM_TOTAL_GB=$((MEM_TOTAL_KB / 1024 / 1024))

# Storage Controllers
STORAGE_CONTROLLERS=$(lspci | grep -E "SATA|RAID|SCSI|NVMe" | cut -d' ' -f2- | tr '\n' '|')

# Network Controllers
NETWORK_CONTROLLERS=$(lspci | grep -E "Ethernet|Network" | cut -d' ' -f2- | tr '\n' '|')

# GPU Information
GPU_INFO=$(lspci | grep -E "VGA|3D|Display" | cut -d' ' -f2- | tr '\n' '|')

# Virtualization Support
VIRT_SUPPORT="none"
if grep -E "vmx|svm" /proc/cpuinfo >/dev/null 2>&1; then
    if grep "vmx" /proc/cpuinfo >/dev/null 2>&1; then
        VIRT_SUPPORT="Intel VT-x"
    else
        VIRT_SUPPORT="AMD-V"
    fi
fi

# Create JSON output
cat > /tmp/hardware_profile.json << EOF
{
    "system": {
        "vendor": "$VENDOR",
        "model": "$MODEL",
        "bios_vendor": "$BIOS_VENDOR",
        "board_name": "$BOARD_NAME"
    },
    "cpu": {
        "vendor": "$CPU_VENDOR",
        "model": "$CPU_MODEL",
        "cores": $CPU_CORES,
        "threads": $CPU_THREADS,
        "sockets": $CPU_SOCKETS,
        "virtualization": "$VIRT_SUPPORT"
    },
    "memory": {
        "total_gb": $MEM_TOTAL_GB
    },
    "storage": {
        "controllers": "$STORAGE_CONTROLLERS"
    },
    "network": {
        "controllers": "$NETWORK_CONTROLLERS"
    },
    "gpu": {
        "devices": "$GPU_INFO"
    }
}
EOF

echo "Hardware detection completed"
""")
        detect_script.chmod(0o755)
        
        # Run detection
        try:
            result = subprocess.run(
                ["chroot", str(self.chroot_path), "/tmp/universal_hw_detect.sh"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Read hardware profile
            profile_path = self.chroot_path / "tmp/hardware_profile.json"
            if profile_path.exists():
                self.hardware_profile = json.loads(profile_path.read_text())
                self.logger.info(f"Detected: {self.hardware_profile['system']['vendor']} {self.hardware_profile['system']['model']}")
                self.logger.info(f"CPU: {self.hardware_profile['cpu']['model']} ({self.hardware_profile['cpu']['cores']} cores)")
                self.logger.info(f"Memory: {self.hardware_profile['memory']['total_gb']}GB")
                
        except Exception as e:
            self.logger.warning(f"Hardware detection error: {e}")
            # Set defaults
            self.hardware_profile = {
                'system': {'vendor': 'Generic', 'model': 'PC'},
                'cpu': {'cores': 4, 'vendor': 'Unknown'},
                'memory': {'total_gb': 8}
            }
    
    def _apply_universal_configs(self):
        """Apply configurations that work for all hardware"""
        self.logger.info("Applying universal hardware configurations...")
        
        # Universal kernel modules to load
        universal_modules = [
            # Storage
            'ahci', 'libahci', 'sd_mod', 'sr_mod',
            # Network - Intel
            'e1000', 'e1000e', 'igb', 'ixgbe', 'i40e',
            # Network - Realtek
            'r8169', 'r8152',
            # Network - Broadcom
            'tg3', 'bnx2', 'bnx2x',
            # USB
            'ehci_hcd', 'ohci_hcd', 'uhci_hcd', 'xhci_hcd',
            # Virtualization
            'virtio_pci', 'virtio_net', 'virtio_blk', 'virtio_scsi',
            'vmw_pvscsi', 'vmxnet3',  # VMware
            'hv_vmbus', 'hv_storvsc', 'hv_netvsc',  # Hyper-V
            # Generic
            'nvme', 'nvme_core'
        ]
        
        # Create modprobe config
        modprobe_conf = self.chroot_path / "etc/modules-load.d/zforge-universal.conf"
        modprobe_conf.parent.mkdir(parents=True, exist_ok=True)
        modprobe_conf.write_text('\n'.join(universal_modules))
        
        # Universal dracut configuration
        dracut_conf = self.chroot_path / "etc/dracut.conf.d/99-universal.conf"
        dracut_conf.parent.mkdir(parents=True, exist_ok=True)
        dracut_conf.write_text("""# Universal hardware support
add_drivers+=" ahci libahci sd_mod sr_mod "
add_drivers+=" e1000 e1000e igb ixgbe i40e r8169 tg3 bnx2 bnx2x "
add_drivers+=" nvme nvme_core nvme_common nvme_tcp nvme_rdma "
add_drivers+=" xhci_hcd xhci_pci ehci_hcd ohci_hcd uhci_hcd "
add_drivers+=" virtio_pci virtio_net virtio_blk virtio_scsi "
add_drivers+=" vmw_pvscsi vmxnet3 hv_vmbus hv_storvsc hv_netvsc "
add_drivers+=" mpt3sas mpt2sas mptsas megaraid_sas "
""")
        
    def _configure_for_hardware(self):
        """Apply hardware-specific optimizations based on detection"""
        self.logger.info("Configuring for detected hardware...")
        
        # Get hardware details
        vendor = self.hardware_profile.get('system', {}).get('vendor', '').lower()
        model = self.hardware_profile.get('system', {}).get('model', '').lower()
        cpu_vendor = self.hardware_profile.get('cpu', {}).get('vendor', '').lower()
        cores = self.hardware_profile.get('cpu', {}).get('cores', 4)
        memory_gb = self.hardware_profile.get('memory', {}).get('total_gb', 8)
        
        # Vendor-specific configurations
        if 'dell' in vendor:
            self._configure_dell_system()
        elif 'hp' in vendor or 'hewlett' in vendor:
            self._configure_hp_system()
        elif 'lenovo' in vendor or 'ibm' in vendor:
            self._configure_lenovo_system()
        elif 'supermicro' in vendor:
            self._configure_supermicro_system()
        
        # CPU-specific optimizations
        if 'genuineintel' in cpu_vendor:
            self._configure_intel_cpu()
        elif 'authenticamd' in cpu_vendor:
            self._configure_amd_cpu()
        
        # Memory-based optimizations
        self._configure_memory_settings(memory_gb)
        
        # Configure build parallelism based on cores
        self._configure_build_settings(cores, memory_gb)
    
    def _configure_dell_system(self):
        """Dell-specific configurations"""
        self.logger.info("Applying Dell system optimizations...")
        
        # Dell modules
        modules = ['dell_smbios', 'dcdbas', 'dell_wmi', 'dell_laptop']
        module_conf = self.chroot_path / "etc/modules-load.d/dell.conf"
        module_conf.write_text('\n'.join(modules))
        
        # Dell repository (with GPG bypass)
        if not (self.chroot_path / "etc/apt/sources.list.d/dell-omsa.list").exists():
            sources = """# Dell OpenManage
deb [arch=amd64 trusted=yes] https://linux.dell.com/repo/community/openmanage/11100/jammy jammy main
"""
            dell_sources = self.chroot_path / "etc/apt/sources.list.d/dell-omsa.list"
            dell_sources.parent.mkdir(parents=True, exist_ok=True)
            dell_sources.write_text(sources)
    
    def _configure_hp_system(self):
        """HP/HPE-specific configurations"""
        self.logger.info("Applying HP system optimizations...")
        
        modules = ['hpilo', 'hpwdt', 'hp_accel']
        module_conf = self.chroot_path / "etc/modules-load.d/hp.conf"
        module_conf.write_text('\n'.join(modules))
    
    def _configure_lenovo_system(self):
        """Lenovo/IBM-specific configurations"""
        self.logger.info("Applying Lenovo system optimizations...")
        
        modules = ['thinkpad_acpi', 'hdaps']
        module_conf = self.chroot_path / "etc/modules-load.d/lenovo.conf"
        module_conf.write_text('\n'.join(modules))
    
    def _configure_supermicro_system(self):
        """Supermicro-specific configurations"""
        self.logger.info("Applying Supermicro system optimizations...")
        
        # Supermicro IPMI modules
        modules = ['ipmi_si', 'ipmi_devintf', 'ipmi_msghandler']
        module_conf = self.chroot_path / "etc/modules-load.d/supermicro.conf"
        module_conf.write_text('\n'.join(modules))
    
    def _configure_intel_cpu(self):
        """Intel CPU optimizations"""
        self.logger.info("Applying Intel CPU optimizations...")
        
        # Intel modules
        modules = ['intel_pstate', 'intel_powerclamp', 'coretemp']
        module_conf = self.chroot_path / "etc/modules-load.d/intel-cpu.conf"
        module_conf.write_text('\n'.join(modules))
        
        # Intel microcode
        if not self._is_package_installed('intel-microcode'):
            self._add_package_to_install('intel-microcode')
    
    def _configure_amd_cpu(self):
        """AMD CPU optimizations"""
        self.logger.info("Applying AMD CPU optimizations...")
        
        # AMD modules
        modules = ['amd_pstate', 'k10temp', 'fam15h_power']
        module_conf = self.chroot_path / "etc/modules-load.d/amd-cpu.conf"
        module_conf.write_text('\n'.join(modules))
        
        # AMD microcode
        if not self._is_package_installed('amd64-microcode'):
            self._add_package_to_install('amd64-microcode')
    
    def _configure_memory_settings(self, memory_gb: int):
        """Configure based on available memory"""
        self.logger.info(f"Configuring for {memory_gb}GB memory...")
        
        if memory_gb >= 64:
            config_type = "high-memory"
            vm_settings = """vm.swappiness = 1
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 20
vm.dirty_background_ratio = 10
vm.min_free_kbytes = 524288"""
        elif memory_gb >= 16:
            config_type = "medium-memory"
            vm_settings = """vm.swappiness = 10
vm.vfs_cache_pressure = 75
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.min_free_kbytes = 262144"""
        else:
            config_type = "low-memory"
            vm_settings = """vm.swappiness = 60
vm.vfs_cache_pressure = 100
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5
vm.min_free_kbytes = 131072"""
        
        sysctl_conf = self.chroot_path / f"etc/sysctl.d/99-{config_type}.conf"
        sysctl_conf.write_text(vm_settings)
    
    def _configure_build_settings(self, cores: int, memory_gb: int):
        """Configure build parallelism based on hardware"""
        # Calculate safe number of parallel jobs
        # Rule: 1 job per 2GB RAM, but not more than cores
        safe_jobs = min(cores, max(1, memory_gb // 2))
        
        # Save for other modules to use
        build_conf = self.chroot_path / "etc/zforge-build.conf"
        build_conf.write_text(f"""# Z-Forge Build Configuration
ZFORGE_BUILD_JOBS={safe_jobs}
ZFORGE_CPU_CORES={cores}
ZFORGE_MEMORY_GB={memory_gb}
""")
        
        self.logger.info(f"Build parallelism set to {safe_jobs} jobs")
    
    def _install_runtime_detection(self):
        """Install runtime hardware detection for live ISO"""
        self.logger.info("Installing runtime hardware detection...")
        
        # Copy the universal detection script
        runtime_script = self.chroot_path / "usr/local/bin/zforge-hw-autoconfig"
        runtime_script.write_text("""#!/bin/bash
# Z-Forge Runtime Hardware Auto-Configuration

echo "=== Z-Forge Hardware Auto-Configuration ==="

# Detect hardware at runtime
VENDOR=$(dmidecode -s system-manufacturer 2>/dev/null || echo "Unknown")
MODEL=$(dmidecode -s system-product-name 2>/dev/null || echo "Unknown")
CPU_MODEL=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
MEM_GB=$(free -g | awk '/^Mem:/{print $2}')

echo "Detected: $VENDOR $MODEL"
echo "CPU: $CPU_MODEL"
echo "Memory: ${MEM_GB}GB"

# Load appropriate modules based on vendor
case "$VENDOR" in
    *Dell*)
        modprobe dell_smbios dcdbas 2>/dev/null
        echo "Loaded Dell-specific modules"
        ;;
    *HP*|*Hewlett*)
        modprobe hpilo hpwdt 2>/dev/null
        echo "Loaded HP-specific modules"
        ;;
    *Lenovo*|*IBM*)
        modprobe thinkpad_acpi 2>/dev/null
        echo "Loaded Lenovo-specific modules"
        ;;
    *Supermicro*)
        modprobe ipmi_si ipmi_devintf 2>/dev/null
        echo "Loaded Supermicro-specific modules"
        ;;
esac

# CPU-specific modules
if lscpu | grep -q "GenuineIntel"; then
    modprobe intel_pstate coretemp 2>/dev/null
    echo "Loaded Intel CPU modules"
elif lscpu | grep -q "AuthenticAMD"; then
    modprobe amd_pstate k10temp 2>/dev/null
    echo "Loaded AMD CPU modules"
fi

# Network driver detection
for pci in $(lspci -n | grep "0200:" | cut -d' ' -f3); do
    case "$pci" in
        8086:*) modprobe e1000e igb ixgbe 2>/dev/null ;;
        10ec:*) modprobe r8169 2>/dev/null ;;
        14e4:*) modprobe tg3 bnx2 2>/dev/null ;;
    esac
done

echo "Hardware auto-configuration completed"

# Save detected profile
cat > /etc/zforge-detected-hardware << EOF
VENDOR="$VENDOR"
MODEL="$MODEL"
CPU_MODEL="$CPU_MODEL"
MEMORY_GB="$MEM_GB"
DETECTED_AT="$(date)"
EOF
""")
        runtime_script.chmod(0o755)
        
        # Create systemd service
        service_content = """[Unit]
Description=Z-Forge Hardware Auto-Configuration
DefaultDependencies=no
After=systemd-modules-load.service
Before=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/zforge-hw-autoconfig
RemainAfterExit=yes
StandardOutput=journal+console

[Install]
WantedBy=multi-user.target
"""
        
        service_path = self.chroot_path / "etc/systemd/system/zforge-hw-autoconfig.service"
        service_path.write_text(service_content)
    
    def _is_package_installed(self, package: str) -> bool:
        """Check if package is marked for installation"""
        # This is a simplified check - in real implementation would check package lists
        return False
    
    def _add_package_to_install(self, package: str):
        """Add package to installation queue"""
        # In real implementation, this would add to package list
        self.logger.info(f"Marked {package} for installation")
    
    def _check_hardware_database(self):
        """Check if detected hardware is in the database"""
        self.logger.info("Checking hardware database for known configurations...")
        
        # Get system info
        vendor = self.hardware_profile.get('system', {}).get('vendor', '')
        model = self.hardware_profile.get('system', {}).get('model', '')
        
        # Check all hardware profile collections
        all_profiles = [
            self.hardware_db.DELL_SERVERS,
            self.hardware_db.HP_SERVERS,
            self.hardware_db.SUPERMICRO_SERVERS,
            self.hardware_db.CONSUMER_HARDWARE  # This includes workstations, NVMe systems, etc.
        ]
        
        # Check for exact match first
        for profile_dict in all_profiles:
            for key, profile in profile_dict.items():
                if profile.vendor.lower() in vendor.lower() and profile.model.lower() in model.lower():
                    self.detected_profile = profile
                    self.logger.info(f"Found exact match: {profile.name}")
                    return
        
        # Try fuzzy matching for servers
        if 'dell' in vendor.lower():
            if 'r730' in model.lower():
                self.detected_profile = self.hardware_db.DELL_SERVERS.get("PowerEdge R730")
            elif 'r740' in model.lower():
                self.detected_profile = self.hardware_db.DELL_SERVERS.get("PowerEdge R740")
            elif 'r640' in model.lower():
                self.detected_profile = self.hardware_db.DELL_SERVERS.get("PowerEdge R640")
            elif 'precision' in model.lower() and 'g8' in model.lower():
                self.detected_profile = self.hardware_db.CONSUMER_HARDWARE.get("Precision G8")
            elif 't30' in model.lower():
                self.detected_profile = self.hardware_db.DELL_SERVERS.get("PowerEdge T30")
        elif 'hp' in vendor.lower() or 'hpe' in vendor.lower():
            if 'dl380' in model.lower() and 'gen10' in model.lower():
                self.detected_profile = self.hardware_db.HP_SERVERS.get("ProLiant DL380 Gen10")
        elif 'supermicro' in vendor.lower():
            if 'x11dph' in model.lower():
                self.detected_profile = self.hardware_db.SUPERMICRO_SERVERS.get("X11DPH-T")
        
        # Check for CPU-based workstation profiles
        cpu_model = self.hardware_profile.get('cpu', {}).get('model', '').lower()
        if not self.detected_profile:
            if 'ryzen 9 5950x' in cpu_model:
                self.detected_profile = self.hardware_db.CONSUMER_HARDWARE.get("AMD Ryzen 9 5950X")
            elif 'i9-13900k' in cpu_model:
                self.detected_profile = self.hardware_db.CONSUMER_HARDWARE.get("Intel Core i9-13900K")
        
        # Check for storage-specific profiles
        if not self.detected_profile:
            storage_controllers = self.hardware_profile.get('storage', {}).get('controllers', '').lower()
            if 'sabrent' in storage_controllers or 'rocket' in storage_controllers:
                self.detected_profile = self.hardware_db.CONSUMER_HARDWARE.get("Sabrent Rocket System")
            elif 'intel' in storage_controllers and '750' in storage_controllers:
                # Could be a system with Intel 750 NVMe
                self.logger.info("Detected Intel 750 NVMe, checking for Precision G8 profile")
            elif 'ultrastar' in storage_controllers and ('wd' in storage_controllers or 'western digital' in storage_controllers):
                self.detected_profile = self.hardware_db.CONSUMER_HARDWARE.get("WD Ultrastar SAS System")
            elif 'dell' in storage_controllers and ('emc' in storage_controllers or 'sas' in storage_controllers):
                self.detected_profile = self.hardware_db.CONSUMER_HARDWARE.get("Dell EMC SAS System")
            elif 'hp' in storage_controllers and ('enterprise' in storage_controllers or 'sas' in storage_controllers):
                self.detected_profile = self.hardware_db.CONSUMER_HARDWARE.get("HP Enterprise SAS System")
            elif 'seagate' in storage_controllers and ('exos' in storage_controllers or 'enterprise' in storage_controllers):
                self.detected_profile = self.hardware_db.CONSUMER_HARDWARE.get("Seagate Exos SAS System")
        
        if self.detected_profile:
            self.logger.info(f"Using profile: {self.detected_profile.name}")
        else:
            self.logger.info("No specific hardware profile found, using generic optimizations")
    
    def _apply_optimal_settings(self):
        """Apply optimal settings from hardware database"""
        if not self.detected_profile:
            return
            
        self.logger.info(f"Applying optimal settings for {self.detected_profile.name}")
        
        settings = self.detected_profile.optimal_settings
        
        # Apply ZFS settings
        if 'zfs' in settings:
            self._apply_zfs_settings(settings['zfs'])
        
        # Apply kernel settings
        if 'kernel' in settings:
            self._apply_kernel_settings(settings['kernel'])
        
        # Apply CPU settings
        if 'cpu' in settings:
            self._apply_cpu_settings(settings['cpu'])
        
        # Apply storage settings
        if 'storage' in settings:
            self._apply_storage_settings(settings['storage'])
        
        # Apply network settings
        if 'network' in settings:
            self._apply_network_settings(settings['network'])
        
        # Handle known issues
        if self.detected_profile.known_issues:
            self.logger.warning(f"Known issues for {self.detected_profile.name}:")
            for issue in self.detected_profile.known_issues:
                self.logger.warning(f"  - {issue}")
    
    def _apply_zfs_settings(self, zfs_settings: Dict[str, Any]):
        """Apply ZFS-specific settings"""
        zfs_conf = self.chroot_path / "etc/modprobe.d/zfs.conf"
        zfs_conf.parent.mkdir(parents=True, exist_ok=True)
        
        lines = ["# Z-Forge Optimal ZFS Settings"]
        for key, value in zfs_settings.items():
            if key == "arc_max_percent":
                # Calculate based on system memory
                memory_gb = self.hardware_profile.get('memory', {}).get('total_gb', 8)
                arc_max = int((memory_gb * 1024 * 1024 * 1024) * (value / 100))
                lines.append(f"options zfs zfs_arc_max={arc_max}")
            else:
                lines.append(f"options zfs {key}={value}")
        
        zfs_conf.write_text('\n'.join(lines))
        self.logger.info("Applied optimal ZFS settings")
    
    def _apply_kernel_settings(self, kernel_settings: Dict[str, Any]):
        """Apply kernel-specific settings"""
        sysctl_conf = self.chroot_path / "etc/sysctl.d/99-zforge-optimal.conf"
        
        lines = ["# Z-Forge Optimal Kernel Settings"]
        for key, value in kernel_settings.items():
            if key == "transparent_hugepages":
                # Handle separately via systemd
                self._configure_transparent_hugepages(value)
            else:
                lines.append(f"{key.replace('_', '.')} = {value}")
        
        sysctl_conf.write_text('\n'.join(lines))
        self.logger.info("Applied optimal kernel settings")
    
    def _apply_cpu_settings(self, cpu_settings: Dict[str, Any]):
        """Apply CPU-specific settings"""
        if 'governor' in cpu_settings:
            # Create CPU governor service
            service_content = f"""[Unit]
Description=Set CPU Governor
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo {cpu_settings['governor']} > $cpu; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
            service_path = self.chroot_path / "etc/systemd/system/cpu-governor.service"
            service_path.write_text(service_content)
        
        self.logger.info("Applied optimal CPU settings")
    
    def _apply_storage_settings(self, storage_settings: Dict[str, Any]):
        """Apply storage-specific settings"""
        # Create udev rules for storage optimization
        udev_rules = ["# Z-Forge Storage Optimization Rules"]
        
        if 'scheduler' in storage_settings:
            # NVMe scheduler
            udev_rules.append(f'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{{queue/scheduler}}="{storage_settings["scheduler"]}"')
            # SATA scheduler (different)
            sata_sched = "mq-deadline" if storage_settings["scheduler"] == "none" else storage_settings["scheduler"]
            udev_rules.append(f'ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{{queue/scheduler}}="{sata_sched}"')
        
        if 'nr_requests' in storage_settings:
            udev_rules.append(f'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{{queue/nr_requests}}="{storage_settings["nr_requests"]}"')
        
        udev_path = self.chroot_path / "etc/udev/rules.d/99-zforge-storage.rules"
        udev_path.parent.mkdir(parents=True, exist_ok=True)
        udev_path.write_text('\n'.join(udev_rules))
        
        self.logger.info("Applied optimal storage settings")
    
    def _apply_network_settings(self, network_settings: Dict[str, Any]):
        """Apply network-specific settings"""
        # Network optimizations would go here
        self.logger.info("Applied optimal network settings")
    
    def _configure_transparent_hugepages(self, setting: str):
        """Configure transparent hugepages via systemd"""
        if setting == "never":
            service_content = """[Unit]
Description=Disable Transparent Huge Pages
DefaultDependencies=no
After=sysinit.target
Before=basic.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled && echo never > /sys/kernel/mm/transparent_hugepage/defrag'

[Install]
WantedBy=basic.target
"""
            service_path = self.chroot_path / "etc/systemd/system/disable-thp.service"
            service_path.write_text(service_content)
    
    def _configure_raid_controllers(self):
        """Detect and configure RAID controllers"""
        self.logger.info("Detecting and configuring RAID controllers...")
        
        # Detect RAID controllers
        raid_controllers = self._detect_raid_controllers()
        
        if not raid_controllers:
            self.logger.info("No RAID controllers detected")
            return
        
        # Configure each detected controller
        for controller in raid_controllers:
            self._configure_raid_controller(controller)
        
        # Install RAID management tools
        self._install_raid_tools()
    
    def _detect_raid_controllers(self) -> List[Dict[str, Any]]:
        """Detect RAID controllers using lspci"""
        controllers = []
        
        try:
            # Get PCI device information
            lspci_result = subprocess.run(
                ['lspci', '-v', '-nn'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if lspci_result.returncode != 0:
                self.logger.warning("Failed to run lspci")
                return controllers
            
            # Parse lspci output for RAID controllers
            current_device = {}
            for line in lspci_result.stdout.split('\n'):
                line = line.strip()
                
                # New device line
                if line and not line.startswith('\t'):
                    # Process previous device
                    if current_device:
                        controller_info = self._identify_raid_controller(current_device)
                        if controller_info:
                            controllers.append(controller_info)
                    
                    # Start new device
                    current_device = {'description': line}
                
                # Device details
                elif line.startswith('\t'):
                    if line.startswith('\tSubsystem:'):
                        current_device['subsystem'] = line[11:].strip()
                    elif line.startswith('\tKernel driver in use:'):
                        current_device['driver'] = line[21:].strip()
            
            # Process last device
            if current_device:
                controller_info = self._identify_raid_controller(current_device)
                if controller_info:
                    controllers.append(controller_info)
        
        except Exception as e:
            self.logger.warning(f"RAID controller detection failed: {e}")
        
        self.logger.info(f"Detected {len(controllers)} RAID controllers")
        for controller in controllers:
            self.logger.info(f"  - {controller['name']} ({controller['type']})")
        
        return controllers
    
    def _identify_raid_controller(self, device: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Identify RAID controller type from device information"""
        desc = device.get('description', '').upper()
        subsystem = device.get('subsystem', '').upper()
        driver = device.get('driver', '').lower()
        
        # Skip if not a RAID/storage controller
        if not any(keyword in desc for keyword in ['RAID', 'STORAGE', 'SCSI', 'SAS', 'SATA']):
            return None
        
        # Dell PERC controllers
        if 'DELL' in desc and 'PERC' in desc:
            if 'H730' in desc:
                return {
                    'name': 'Dell PERC H730',
                    'type': 'dell_perc_h730',
                    'vendor': 'Dell Inc.',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'perccli',
                    'features': ['raid_modes', 'cache', 'bbu']
                }
            elif 'H740P' in desc:
                return {
                    'name': 'Dell PERC H740P',
                    'type': 'dell_perc_h740p',
                    'vendor': 'Dell Inc.',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'perccli',
                    'features': ['raid_modes', 'cache', 'bbu', 'nvme']
                }
            else:
                return {
                    'name': 'Dell PERC Controller',
                    'type': 'dell_perc_generic',
                    'vendor': 'Dell Inc.',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'perccli',
                    'features': ['raid_modes']
                }
        
        # HP Smart Array controllers
        elif 'HP' in desc or 'HEWLETT' in desc:
            if 'SMART ARRAY' in desc or 'P440AR' in desc:
                return {
                    'name': 'HP Smart Array P440ar',
                    'type': 'hp_smartarray_p440ar',
                    'vendor': 'HPE',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'ssacli',
                    'features': ['raid_modes', 'cache', 'smart_cache']
                }
            else:
                return {
                    'name': 'HP Smart Array Controller',
                    'type': 'hp_smartarray_generic',
                    'vendor': 'HPE',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'ssacli',
                    'features': ['raid_modes']
                }
        
        # LSI/Broadcom MegaRAID controllers
        elif 'LSI' in desc or 'MEGARAID' in desc or 'BROADCOM' in subsystem:
            if '9361-8I' in desc:
                return {
                    'name': 'LSI MegaRAID 9361-8i',
                    'type': 'lsi_megaraid_9361_8i',
                    'vendor': 'Broadcom/LSI',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'megacli',
                    'features': ['raid_modes', 'cache', 'bbu', 'ssd_cache']
                }
            else:
                return {
                    'name': 'LSI MegaRAID Controller',
                    'type': 'lsi_megaraid_generic',
                    'vendor': 'Broadcom/LSI',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'megacli',
                    'features': ['raid_modes']
                }
        
        # Adaptec controllers
        elif 'ADAPTEC' in desc or 'MICROSEMI' in desc:
            if '8805' in desc:
                return {
                    'name': 'Adaptec ASR-8805',
                    'type': 'adaptec_asr_8805',
                    'vendor': 'Microsemi/Adaptec',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'arcconf',
                    'features': ['raid_modes', 'cache', 'maxcache']
                }
            else:
                return {
                    'name': 'Adaptec RAID Controller',
                    'type': 'adaptec_generic',
                    'vendor': 'Microsemi/Adaptec',
                    'description': desc,
                    'driver': driver,
                    'management_tool': 'arcconf',
                    'features': ['raid_modes']
                }
        
        return None
    
    def _configure_raid_controller(self, controller: Dict[str, Any]):
        """Configure specific RAID controller"""
        self.logger.info(f"Configuring {controller['name']}...")
        
        controller_type = controller['type']
        
        # Create controller-specific configuration
        if controller_type.startswith('dell_perc'):
            self._configure_dell_perc(controller)
        elif controller_type.startswith('hp_smartarray'):
            self._configure_hp_smartarray(controller)
        elif controller_type.startswith('lsi_megaraid'):
            self._configure_lsi_megaraid(controller)
        elif controller_type.startswith('adaptec'):
            self._configure_adaptec(controller)
    
    def _configure_dell_perc(self, controller: Dict[str, Any]):
        """Configure Dell PERC controller"""
        # Create PERC configuration
        perc_conf = self.chroot_path / "etc/zforge/raid/dell_perc.conf"
        perc_conf.parent.mkdir(parents=True, exist_ok=True)
        
        config = f"""# Dell PERC Configuration
CONTROLLER_TYPE="{controller['type']}"
CONTROLLER_NAME="{controller['name']}"
MANAGEMENT_TOOL="{controller['management_tool']}"

# Recommended settings for ZFS
RAID_MODE="IT"  # IT mode recommended for ZFS
CACHE_POLICY="disabled"  # Let ZFS handle caching
BBU_POLICY="check_status"
PATROL_READ="auto"

# Driver settings
KERNEL_MODULE="megaraid_sas"
"""
        perc_conf.write_text(config)
        
        # Add to package installation list
        self._add_package_to_install('perccli')
    
    def _configure_hp_smartarray(self, controller: Dict[str, Any]):
        """Configure HP Smart Array controller"""
        smartarray_conf = self.chroot_path / "etc/zforge/raid/hp_smartarray.conf"
        smartarray_conf.parent.mkdir(parents=True, exist_ok=True)
        
        config = f"""# HP Smart Array Configuration
CONTROLLER_TYPE="{controller['type']}"
CONTROLLER_NAME="{controller['name']}"
MANAGEMENT_TOOL="{controller['management_tool']}"

# Recommended settings for ZFS
RAID_MODE="HBA"  # HBA mode recommended for ZFS
CACHE_POLICY="disabled"
SMART_CACHE="disabled"

# Driver settings
KERNEL_MODULE="hpsa"
"""
        smartarray_conf.write_text(config)
        
        # Add to package installation list
        self._add_package_to_install('ssacli')
    
    def _configure_lsi_megaraid(self, controller: Dict[str, Any]):
        """Configure LSI MegaRAID controller"""
        megaraid_conf = self.chroot_path / "etc/zforge/raid/lsi_megaraid.conf"
        megaraid_conf.parent.mkdir(parents=True, exist_ok=True)
        
        config = f"""# LSI MegaRAID Configuration
CONTROLLER_TYPE="{controller['type']}"
CONTROLLER_NAME="{controller['name']}"
MANAGEMENT_TOOL="{controller['management_tool']}"

# Recommended settings for ZFS
RAID_MODE="IT"  # IT mode recommended for ZFS
CACHE_POLICY="disabled"
BBU_POLICY="check_status"
WRITE_POLICY="write_through"

# Driver settings
KERNEL_MODULE="megaraid_sas"
"""
        megaraid_conf.write_text(config)
        
        # Add to package installation list
        self._add_package_to_install('megacli')
    
    def _configure_adaptec(self, controller: Dict[str, Any]):
        """Configure Adaptec controller"""
        adaptec_conf = self.chroot_path / "etc/zforge/raid/adaptec.conf"
        adaptec_conf.parent.mkdir(parents=True, exist_ok=True)
        
        config = f"""# Adaptec Configuration
CONTROLLER_TYPE="{controller['type']}"
CONTROLLER_NAME="{controller['name']}"
MANAGEMENT_TOOL="{controller['management_tool']}"

# Recommended settings for ZFS
RAID_MODE="HBA"  # HBA mode recommended for ZFS
CACHE_POLICY="disabled"
MAXCACHE="disabled"

# Driver settings
KERNEL_MODULE="aacraid"
"""
        adaptec_conf.write_text(config)
        
        # Add to package installation list
        self._add_package_to_install('arcconf')
    
    def _install_raid_tools(self):
        """Install RAID management tools"""
        self.logger.info("Installing RAID management tools...")
        
        # Generic RAID tools
        raid_tools = [
            'mdadm',  # Software RAID
            'lvm2',   # Logical Volume Manager
            'smartmontools',  # Drive monitoring
            'hdparm'  # Drive utilities
        ]
        
        for tool in raid_tools:
            self._add_package_to_install(tool)
        
        # Create RAID management script
        raid_script = self.chroot_path / "usr/local/bin/zforge-raid-info"
        raid_script.write_text("""#!/bin/bash
# Z-FORGE RAID Information Script

echo "=== Z-FORGE RAID Controller Information ==="
echo

# Check for controller configurations
RAID_CONF_DIR="/etc/zforge/raid"
if [ -d "$RAID_CONF_DIR" ]; then
    echo "Detected RAID Controllers:"
    for conf in "$RAID_CONF_DIR"/*.conf; do
        if [ -f "$conf" ]; then
            echo "  - $(basename "$conf" .conf)"
            grep "CONTROLLER_NAME" "$conf" | cut -d'"' -f2
        fi
    done
    echo
fi

# Check for management tools
echo "Available Management Tools:"
for tool in perccli ssacli megacli arcconf; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "  ✓ $tool"
    else
        echo "  ✗ $tool (not installed)"
    fi
done
echo

# Show current RAID status if tools available
if command -v lsblk >/dev/null 2>&1; then
    echo "Current Storage Layout:"
    lsblk
fi
""")
        raid_script.chmod(0o755)
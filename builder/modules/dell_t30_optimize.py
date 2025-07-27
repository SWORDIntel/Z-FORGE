#!/usr/bin/env python3
"""
Dell PowerEdge T30 Optimization Module
Applies T30-specific configurations and optimizations
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import shutil
import os


class DellT30Optimize:
    """Dell PowerEdge T30 specific optimizations"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.chroot_path = workspace / "chroot"
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # T30 specific configuration
        self.t30_config = config.get('dell_t30_config', {})
        self.post_install_scripts = config.get('post_install_scripts', [])
        self.kernel_build_config = config.get('kernel_build_config', {})
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None,
                lockfile: Optional[Any] = None) -> Dict[str, Any]:
        """Execute T30 optimizations"""
        self.logger.info("Starting Dell PowerEdge T30 optimizations...")
        
        try:
            # Copy T30 scripts to chroot
            self._copy_scripts()
            
            # Detect hardware automatically
            self._detect_hardware()
            
            # Apply T30 specific configurations
            self._configure_t30_hardware()
            
            # Configure software RAID support
            self._configure_software_raid()
            
            # Set up Intel-specific optimizations
            self._configure_intel_optimizations()
            
            # Configure tower server thermal profile
            self._configure_thermal_profile()
            
            # Configure memory-conscious kernel builds
            self._configure_kernel_build_limits()
            
            # Run post-install scripts
            self._run_post_install_scripts()
            
            return {
                'status': 'success',
                'message': 'Dell T30 optimizations completed successfully'
            }
            
        except Exception as e:
            self.logger.error(f"T30 optimization failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _copy_scripts(self):
        """Copy T30 scripts to chroot"""
        self.logger.info("Copying T30 scripts to chroot...")
        
        scripts_dir = self.chroot_path / "opt/dell-t30"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy post-install scripts
        for script_path in self.post_install_scripts:
            if script_path.startswith('config/'):
                # Relative to project root
                source = Path(__file__).parent.parent.parent / script_path
            else:
                source = Path(script_path)
                
            if source.exists():
                dest = scripts_dir / source.name
                shutil.copy2(source, dest)
                dest.chmod(0o755)
                self.logger.info(f"Copied {source.name} to chroot")
            else:
                self.logger.warning(f"Script not found: {source}")
    
    def _detect_hardware(self):
        """Automatically detect T30 hardware configuration"""
        self.logger.info("Detecting Dell T30 hardware configuration...")
        
        # Create hardware detection script
        detect_script = self.chroot_path / "tmp/detect_t30_hardware.sh"
        detect_script.parent.mkdir(parents=True, exist_ok=True)
        detect_script.write_text("""#!/bin/bash
# Dell T30 Hardware Detection

echo "=== Dell T30 Hardware Detection ==="

# CPU Detection
echo "CPU Information:"
lscpu | grep -E "Model name|Socket|Core|Thread" || true

# Memory Detection
echo -e "\nMemory Configuration:"
free -h | grep "Mem:" || true
dmidecode -t memory 2>/dev/null | grep -E "Size:|Type:|Speed:" | head -10 || true

# Storage Detection
echo -e "\nStorage Devices:"
lsblk -d -o NAME,SIZE,TYPE,MODEL | grep -v loop || true

# NVMe Detection
echo -e "\nNVMe Devices:"
nvme list 2>/dev/null || echo "No NVMe devices detected"

# Network Detection
echo -e "\nNetwork Interfaces:"
ip link show | grep -E "^[0-9]+: " | grep -v "lo:" || true
lspci | grep -i ethernet || true

# PCIe Devices
echo -e "\nPCIe Devices:"
lspci | grep -E "VGA|Audio|USB|SATA|RAID" || true

# BIOS/UEFI Mode
echo -e "\nBoot Mode:"
if [ -d /sys/firmware/efi ]; then
    echo "UEFI Mode"
else
    echo "BIOS/Legacy Mode"
fi

# Save detection results
cat > /etc/dell-t30-hardware.conf << EOF
# Dell T30 Hardware Configuration (Auto-detected)
DETECTED_DATE="$(date)"
CPU_MODEL="$(lscpu | grep "Model name" | cut -d: -f2 | xargs)"
CPU_CORES="$(nproc)"
MEMORY_GB="$(free -g | awk '/^Mem:/{print $2}')"
BOOT_MODE="$([ -d /sys/firmware/efi ] && echo "UEFI" || echo "BIOS")"
EOF

echo -e "\nHardware detection completed."
""")
        detect_script.chmod(0o755)
        
        # Run detection script
        try:
            result = subprocess.run(
                ["chroot", str(self.chroot_path), "/tmp/detect_t30_hardware.sh"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.stdout:
                self.logger.info("Hardware detection output:")
                for line in result.stdout.splitlines():
                    self.logger.info(f"  {line}")
                    
            # Parse detected hardware
            self._parse_hardware_info()
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Hardware detection timed out")
        except Exception as e:
            self.logger.warning(f"Hardware detection failed: {e}")
    
    def _parse_hardware_info(self):
        """Parse and apply hardware-specific optimizations"""
        hw_conf = self.chroot_path / "etc/dell-t30-hardware.conf"
        
        if hw_conf.exists():
            content = hw_conf.read_text()
            
            # Extract key values
            cpu_cores = 4  # default
            memory_gb = 8  # default
            
            for line in content.splitlines():
                if line.startswith("CPU_CORES="):
                    try:
                        cpu_cores = int(line.split('=')[1].strip('"'))
                    except ValueError:
                        pass
                elif line.startswith("MEMORY_GB="):
                    try:
                        memory_gb = int(line.split('=')[1].strip('"'))
                    except ValueError:
                        pass
            
            self.logger.info(f"Detected: {cpu_cores} CPU cores, {memory_gb}GB RAM")
            
            # Apply dynamic optimizations based on hardware
            if memory_gb >= 32:
                self.logger.info("High memory system detected, applying optimizations")
                self._apply_high_memory_optimizations()
            elif memory_gb <= 8:
                self.logger.info("Low memory system detected, applying conservative settings")
                self._apply_low_memory_optimizations()
    
    def _apply_high_memory_optimizations(self):
        """Apply optimizations for high-memory T30 systems"""
        opt_conf = self.chroot_path / "etc/sysctl.d/99-t30-highmem.conf"
        opt_conf.write_text("""# High memory T30 optimizations
vm.swappiness = 1
vm.vfs_cache_pressure = 50
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
""")
    
    def _apply_low_memory_optimizations(self):
        """Apply optimizations for low-memory T30 systems"""
        opt_conf = self.chroot_path / "etc/sysctl.d/99-t30-lowmem.conf"
        opt_conf.write_text("""# Low memory T30 optimizations
vm.swappiness = 60
vm.vfs_cache_pressure = 100
vm.dirty_ratio = 5
vm.dirty_background_ratio = 2
vm.overcommit_memory = 1
""")
    
    def _configure_t30_hardware(self):
        """Configure T30-specific hardware settings"""
        self.logger.info("Configuring T30 hardware settings...")
        
        # Create T30 hardware configuration
        hw_config = self.chroot_path / "etc/dell-t30.conf"
        hw_config.write_text(f"""
# Dell PowerEdge T30 Configuration
SERVER_TYPE=tower
CPU_FAMILY=xeon_e3_v5
MEMORY_TYPE=ddr4_ecc
MAX_MEMORY_GB=64
PCIE_SLOTS=4
SATA_PORTS=4
USB3_PORTS=4
BMC_TYPE=basic
""")
        
        # Configure modprobe for T30 hardware
        modprobe_conf = self.chroot_path / "etc/modprobe.d/dell-t30.conf"
        modprobe_conf.write_text("""
# Intel E3 v5 CPU frequency driver
options intel_pstate hwp_dynamic_boost=1

# Intel graphics (if using integrated graphics)
options i915 enable_guc=2 enable_fbc=1

# USB 3.0 optimization
options xhci_hcd quirks=0x40

# AHCI for SATA
options ahci mobile_lpm_policy=0
""")
    
    def _configure_software_raid(self):
        """Configure software RAID support"""
        self.logger.info("Configuring software RAID support...")
        
        # Ensure mdadm is configured
        mdadm_conf = self.chroot_path / "etc/mdadm/mdadm.conf"
        if not mdadm_conf.exists():
            mdadm_conf.parent.mkdir(parents=True, exist_ok=True)
            mdadm_conf.write_text("""
# mdadm.conf for Dell T30
DEVICE partitions
HOMEHOST <system>
MAILADDR root
AUTO +all
""")
        
        # Enable mdadm monitoring
        cmd = ["chroot", str(self.chroot_path), "systemctl", "enable", "mdadm-monitoring.service"]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.logger.info("Enabled mdadm monitoring service")
        except subprocess.CalledProcessError:
            self.logger.warning("Could not enable mdadm monitoring (may not be installed yet)")
    
    def _configure_intel_optimizations(self):
        """Configure Intel Xeon E3 v5 specific optimizations"""
        self.logger.info("Applying Intel Xeon E3 v5 optimizations...")
        
        # Create Intel optimization script
        intel_opt = self.chroot_path / "etc/profile.d/intel-opt.sh"
        intel_opt.write_text("""
#!/bin/bash
# Intel Xeon E3 v5 optimizations

# Enable Intel Turbo Boost
if [ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
    echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || true
fi

# Set performance bias
if command -v x86_energy_perf_policy >/dev/null 2>&1; then
    x86_energy_perf_policy performance 2>/dev/null || true
fi

# Export Intel-specific environment variables
export INTEL_BATCH=1
export KMP_AFFINITY=granularity=fine,compact,1,0
""")
        intel_opt.chmod(0o755)
        
        # Configure Intel microcode loading
        microcode_conf = self.chroot_path / "etc/default/intel-microcode"
        microcode_conf.parent.mkdir(parents=True, exist_ok=True)
        microcode_conf.write_text("""
# Intel microcode configuration
IUCODE_TOOL_SCANCPUS=yes
IUCODE_TOOL_INITRAMFS=yes
IUCODE_TOOL_EXTRA_OPTIONS=""
""")
    
    def _configure_thermal_profile(self):
        """Configure thermal profile for tower server"""
        self.logger.info("Configuring tower server thermal profile...")
        
        # Create thermal configuration
        thermal_conf = self.chroot_path / "etc/thermald/thermal-conf.xml"
        thermal_conf.parent.mkdir(parents=True, exist_ok=True)
        thermal_conf.write_text("""<?xml version="1.0"?>
<ThermalConfiguration>
  <Platform>
    <Name>Dell PowerEdge T30</Name>
    <ProductName>PowerEdge T30</ProductName>
    <Preference>PERFORMANCE</Preference>
    <ThermalZones>
      <ThermalZone>
        <Type>cpu</Type>
        <TripPoints>
          <TripPoint>
            <Temperature>85000</Temperature>
            <type>passive</type>
          </TripPoint>
          <TripPoint>
            <Temperature>95000</Temperature>
            <type>critical</type>
          </TripPoint>
        </TripPoints>
      </ThermalZone>
    </ThermalZones>
  </Platform>
</ThermalConfiguration>
""")
        
        # Configure fan control if available
        fancontrol_conf = self.chroot_path / "etc/fancontrol"
        fancontrol_conf.write_text("""
# Dell T30 fan control configuration
# This is a tower server with different cooling than rack servers
INTERVAL=10
DEVPATH=hwmon0=devices/platform/coretemp.0 hwmon1=devices/platform/nct6775.2592
DEVNAME=hwmon0=coretemp hwmon1=nct6779
FCTEMPS=hwmon1/pwm2=hwmon0/temp1_input
FCFANS=hwmon1/pwm2=hwmon1/fan2_input
MINTEMP=hwmon1/pwm2=35
MAXTEMP=hwmon1/pwm2=65
MINSTART=hwmon1/pwm2=100
MINSTOP=hwmon1/pwm2=60
""")
    
    def _run_post_install_scripts(self):
        """Run T30 post-install scripts in chroot"""
        self.logger.info("Running T30 post-install scripts...")
        
        scripts_dir = self.chroot_path / "opt/dell-t30"
        
        for script in ["t30_post_install.sh", "t30_optimization.sh"]:
            script_path = scripts_dir / script
            if script_path.exists():
                self.logger.info(f"Running {script}...")
                
                cmd = ["chroot", str(self.chroot_path), f"/opt/dell-t30/{script}"]
                
                try:
                    result = subprocess.run(
                        cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    self.logger.info(f"{script} completed successfully")
                    if result.stdout:
                        self.logger.debug(f"Output: {result.stdout}")
                        
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"{script} failed: {e.stderr}")
                    # Don't fail the entire module if optimization scripts fail
                    self.logger.warning("Continuing despite script failure...")
                    
                except subprocess.TimeoutExpired:
                    self.logger.error(f"{script} timed out after 5 minutes")
            else:
                self.logger.warning(f"Script not found: {script_path}")
        
        # Create marker file
        marker = self.chroot_path / "var/lib/dell-t30-optimized"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        
        self.logger.info("T30 post-install scripts completed")
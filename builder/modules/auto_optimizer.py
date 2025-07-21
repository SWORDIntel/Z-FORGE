#!/usr/bin/env python3
"""
Auto-Optimizer for Z-FORGE
Combines hardware detection, presets, and testing for optimal configuration
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
import sys

# Add modules to path
sys.path.append(str(Path(__file__).parent))

from hardware_db import HardwareDatabase
from preset_loader import PresetLoader

logger = logging.getLogger(__name__)

class AutoOptimizer:
    """Automatically optimize Z-FORGE installation based on hardware"""
    
    def __init__(self):
        self.hw_db = HardwareDatabase()
        self.preset_loader = PresetLoader()
        self.optimization_report = {}
    
    def analyze_system(self) -> Dict[str, Any]:
        """Perform complete system analysis"""
        logger.info("Starting system analysis...")
        
        # Detect hardware
        hw_info = self.hw_db.detect_hardware()
        
        # Get hardware profile
        sys_info = hw_info["system"]
        hw_profile = self.hw_db.get_hardware_profile(sys_info)
        
        # Determine best preset
        preset_name = self._determine_preset(hw_info, hw_profile)
        
        # Get optimal settings
        optimal_settings = self.hw_db.get_optimal_settings()
        
        analysis = {
            "hardware": hw_info,
            "profile": hw_profile.name if hw_profile else "Generic",
            "recommended_preset": preset_name,
            "optimal_settings": optimal_settings,
            "warnings": self._check_compatibility(hw_info, hw_profile)
        }
        
        self.optimization_report = analysis
        return analysis
    
    def _determine_preset(self, hw_info: Dict[str, Any], 
                         hw_profile: Optional[Any]) -> str:
        """Determine best preset based on hardware"""
        # Check system type
        if hw_profile:
            if hw_profile.type == "server":
                # Check if it's likely a homelab or datacenter
                total_mem = hw_info["memory"].get("total_gb", 0)
                
                if total_mem >= 128:
                    return "datacenter"
                else:
                    return "homelab"
            elif hw_profile.type == "workstation":
                # Check for GPU to determine if gaming or development
                if hw_info["gpu"] and any(g["vendor"] != "Intel" for g in hw_info["gpu"]):
                    return "gaming"
                else:
                    return "development"
        
        # Fallback logic based on detected features
        if hw_info["memory"].get("total_gb", 0) >= 64:
            return "datacenter"
        elif hw_info["gpu"] and len(hw_info["gpu"]) > 1:
            return "gaming"
        else:
            return "homelab"
    
    def _check_compatibility(self, hw_info: Dict[str, Any], 
                           hw_profile: Optional[Any]) -> List[str]:
        """Check for compatibility issues"""
        warnings = []
        
        # Check memory
        total_mem = hw_info["memory"].get("total_gb", 0)
        if total_mem < 8:
            warnings.append("Less than 8GB RAM detected - ZFS performance may suffer")
        
        # Check specific hardware issues
        if hw_profile and hw_profile.known_issues:
            warnings.extend(hw_profile.known_issues)
        
        # Check storage
        has_ssd = any(not dev["rotational"] for dev in hw_info["storage"])
        if not has_ssd:
            warnings.append("No SSD detected - consider SSD for boot/root pool")
        
        # Check for RAID controllers
        sys_model = hw_info["system"].get("model", "")
        if any(raid in sys_model.lower() for raid in ["perc", "smart array"]):
            warnings.append("Hardware RAID detected - configure in IT/HBA mode for ZFS")
        
        return warnings
    
    def generate_config(self, output_dir: Path, 
                       preset_override: Optional[str] = None) -> Dict[str, Path]:
        """Generate optimized configuration files"""
        if not self.optimization_report:
            self.analyze_system()
        
        preset_name = preset_override or self.optimization_report["recommended_preset"]
        
        logger.info(f"Generating configuration with preset: {preset_name}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate module configs from preset
        self.preset_loader.save_to_calamares_config(preset_name, output_dir)
        
        # Apply hardware-specific optimizations
        self._apply_hardware_optimizations(output_dir)
        
        # Generate system optimization scripts
        self._generate_optimization_scripts(output_dir)
        
        # Generate report
        report_path = output_dir / "optimization_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.optimization_report, f, indent=2)
        
        return {
            "configs": output_dir / "*.conf",
            "scripts": output_dir / "scripts",
            "report": report_path
        }
    
    def _apply_hardware_optimizations(self, output_dir: Path):
        """Apply hardware-specific optimizations to configs"""
        optimal_settings = self.optimization_report["optimal_settings"]
        
        # Create hardware-specific overrides
        overrides = {
            "zfs_tuning": optimal_settings.get("zfs", {}),
            "kernel_parameters": optimal_settings.get("kernel", {}),
            "cpu_settings": optimal_settings.get("cpu", {})
        }
        
        override_path = output_dir / "hardware_overrides.yaml"
        import yaml
        with open(override_path, 'w') as f:
            yaml.dump(overrides, f, default_flow_style=False)
    
    def _generate_optimization_scripts(self, output_dir: Path):
        """Generate optimization scripts"""
        scripts_dir = output_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # Generate ZFS tuning script
        self._generate_zfs_tuning_script(scripts_dir)
        
        # Generate kernel tuning script
        self._generate_kernel_tuning_script(scripts_dir)
        
        # Generate post-install optimization script
        self._generate_post_install_script(scripts_dir)
    
    def _generate_zfs_tuning_script(self, scripts_dir: Path):
        """Generate ZFS tuning script"""
        zfs_settings = self.optimization_report["optimal_settings"].get("zfs", {})
        
        script_content = """#!/bin/bash
# Z-FORGE ZFS Optimization Script
# Generated based on hardware detection

echo "Applying ZFS optimizations..."

"""
        
        # ARC settings
        if "arc_max_percent" in zfs_settings:
            arc_percent = zfs_settings["arc_max_percent"]
            script_content += f"""
# Set ARC max to {arc_percent}% of RAM
TOTAL_MEM=$(grep MemTotal /proc/meminfo | awk '{{print $2}}')
ARC_MAX=$((TOTAL_MEM * 1024 * {arc_percent} / 100))
echo $ARC_MAX > /sys/module/zfs/parameters/zfs_arc_max
echo "options zfs zfs_arc_max=$ARC_MAX" > /etc/modprobe.d/zfs.conf
"""
        
        # L2ARC settings
        if "l2arc_write_max" in zfs_settings:
            script_content += f"""
# L2ARC write settings
echo {zfs_settings['l2arc_write_max']} > /sys/module/zfs/parameters/l2arc_write_max
echo "options zfs l2arc_write_max={zfs_settings['l2arc_write_max']}" >> /etc/modprobe.d/zfs.conf
"""
        
        # Additional ZFS settings for NVMe optimization
        for param, value in zfs_settings.items():
            if param not in ["arc_max_percent", "l2arc_write_max"]:
                script_content += f"""
# {param}
echo {value} > /sys/module/zfs/parameters/{param} 2>/dev/null || true
echo "options zfs {param}={value}" >> /etc/modprobe.d/zfs.conf
"""
        
        # Check for Intel 750 Series SSD
        if self.optimization_report.get("hardware", {}).get("storage"):
            for disk in self.optimization_report["hardware"]["storage"]:
                if disk.get("special") == "Intel 750 Series":
                    script_content += """
# Intel 750 Series NVMe optimizations
echo "Detected Intel 750 Series SSD - applying specific optimizations"

# Increase queue depth for Intel 750
for nvme in /sys/block/nvme*/queue; do
    echo 256 > $nvme/nr_requests
    echo 256 > $nvme/queue_depth 2>/dev/null || true
done

# Enable IO polling for lower latency
echo 1 > /sys/module/nvme_core/parameters/io_poll 2>/dev/null || true
echo 0 > /sys/module/nvme_core/parameters/io_poll_delay 2>/dev/null || true

# Set optimal scheduler for NVMe
for nvme in /sys/block/nvme*; do
    echo none > $nvme/queue/scheduler 2>/dev/null || true
done
"""
        
        script_content += """
echo "ZFS optimizations applied!"
"""
        
        script_path = scripts_dir / "optimize_zfs.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)
    
    def _generate_kernel_tuning_script(self, scripts_dir: Path):
        """Generate kernel tuning script"""
        kernel_settings = self.optimization_report["optimal_settings"].get("kernel", {})
        
        script_content = """#!/bin/bash
# Z-FORGE Kernel Optimization Script
# Generated based on hardware detection

echo "Applying kernel optimizations..."

"""
        
        # Sysctl settings
        sysctl_settings = []
        
        if "vm_swappiness" in kernel_settings:
            sysctl_settings.append(f"vm.swappiness={kernel_settings['vm_swappiness']}")
        
        if "transparent_hugepages" in kernel_settings:
            thp = kernel_settings["transparent_hugepages"]
            script_content += f"""
# Transparent hugepages
echo {thp} > /sys/kernel/mm/transparent_hugepage/enabled
echo {thp} > /sys/kernel/mm/transparent_hugepage/defrag
"""
        
        if sysctl_settings:
            script_content += """
# Apply sysctl settings
cat >> /etc/sysctl.d/99-zforge-optimization.conf << EOF
"""
            for setting in sysctl_settings:
                script_content += f"{setting}\n"
            
            script_content += """EOF

sysctl -p /etc/sysctl.d/99-zforge-optimization.conf
"""
        
        script_content += """
echo "Kernel optimizations applied!"
"""
        
        script_path = scripts_dir / "optimize_kernel.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)
    
    def _generate_post_install_script(self, scripts_dir: Path):
        """Generate post-install optimization script"""
        script_content = """#!/bin/bash
# Z-FORGE Post-Install Optimization Script
# Runs all optimization scripts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running Z-FORGE post-install optimizations..."

# Run ZFS optimizations
if [ -f "$SCRIPT_DIR/optimize_zfs.sh" ]; then
    echo "Applying ZFS optimizations..."
    bash "$SCRIPT_DIR/optimize_zfs.sh"
fi

# Run kernel optimizations
if [ -f "$SCRIPT_DIR/optimize_kernel.sh" ]; then
    echo "Applying kernel optimizations..."
    bash "$SCRIPT_DIR/optimize_kernel.sh"
fi

# Run CPU governor settings
if [ -f "$SCRIPT_DIR/optimize_cpu.sh" ]; then
    echo "Applying CPU optimizations..."
    bash "$SCRIPT_DIR/optimize_cpu.sh"
fi

echo "All optimizations applied!"
echo "Please reboot to ensure all settings take effect."
"""
        
        script_path = scripts_dir / "run_all_optimizations.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)
    
    def test_configuration(self, config_dir: Path) -> Dict[str, Any]:
        """Test generated configuration"""
        logger.info("Testing configuration...")
        
        test_results = {
            "syntax": self._test_syntax(config_dir),
            "modules": self._test_modules(config_dir),
            "scripts": self._test_scripts(config_dir)
        }
        
        return test_results
    
    def _test_syntax(self, config_dir: Path) -> Dict[str, bool]:
        """Test configuration file syntax"""
        results = {}
        
        # Test YAML files
        import yaml
        for yaml_file in config_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    yaml.safe_load(f)
                results[yaml_file.name] = True
            except Exception as e:
                results[yaml_file.name] = False
                logger.error(f"YAML syntax error in {yaml_file}: {e}")
        
        # Test shell scripts
        for script in (config_dir / "scripts").glob("*.sh"):
            result = subprocess.run(
                ["bash", "-n", str(script)],
                capture_output=True
            )
            results[script.name] = result.returncode == 0
        
        return results
    
    def _test_modules(self, config_dir: Path) -> Dict[str, bool]:
        """Test module configurations"""
        # This would run the actual test suite
        # For now, just check that configs exist
        results = {}
        
        expected_modules = ["networkconfig", "hardwarehealth", "gpupassthrough", 
                          "storagelayout", "postinstall"]
        
        for module in expected_modules:
            config_file = config_dir / f"{module}.conf"
            results[module] = config_file.exists()
        
        return results
    
    def _test_scripts(self, config_dir: Path) -> Dict[str, bool]:
        """Test optimization scripts"""
        results = {}
        scripts_dir = config_dir / "scripts"
        
        if scripts_dir.exists():
            for script in scripts_dir.glob("*.sh"):
                # Check if executable
                results[script.name] = script.stat().st_mode & 0o111 != 0
        
        return results


def main():
    """CLI for auto-optimizer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Z-FORGE Auto-Optimizer")
    parser.add_argument("-o", "--output", default="./optimized_config",
                       help="Output directory for configuration")
    parser.add_argument("-p", "--preset", help="Override preset selection")
    parser.add_argument("--analyze-only", action="store_true",
                       help="Only analyze, don't generate config")
    parser.add_argument("--test", action="store_true",
                       help="Test generated configuration")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    optimizer = AutoOptimizer()
    
    # Analyze system
    analysis = optimizer.analyze_system()
    
    print("Z-FORGE Auto-Optimization Analysis")
    print("=" * 50)
    print(f"Hardware Profile: {analysis['profile']}")
    print(f"Recommended Preset: {analysis['recommended_preset']}")
    
    if analysis['warnings']:
        print("\nWarnings:")
        for warning in analysis['warnings']:
            print(f"  ⚠ {warning}")
    
    if args.analyze_only:
        print("\nOptimal Settings:")
        print(json.dumps(analysis['optimal_settings'], indent=2))
        return
    
    # Generate configuration
    output_dir = Path(args.output)
    config_files = optimizer.generate_config(output_dir, args.preset)
    
    print(f"\nConfiguration generated in: {output_dir}")
    print("Files created:")
    for category, path in config_files.items():
        print(f"  - {category}: {path}")
    
    # Test if requested
    if args.test:
        print("\nTesting configuration...")
        test_results = optimizer.test_configuration(output_dir)
        
        all_passed = True
        for category, results in test_results.items():
            print(f"\n{category.title()} Tests:")
            for item, passed in results.items():
                status = "✓" if passed else "✗"
                print(f"  {status} {item}")
                if not passed:
                    all_passed = False
        
        if all_passed:
            print("\nAll tests passed!")
        else:
            print("\nSome tests failed. Check logs for details.")
            sys.exit(1)


if __name__ == "__main__":
    main()
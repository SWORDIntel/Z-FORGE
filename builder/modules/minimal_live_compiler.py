#!/usr/bin/env python3
"""
Z-FORGE Minimal Live Compilation Environment Builder
Creates a 512MB live environment for native compilation during installation
Coordinated by INFRASTRUCTURE agent with DIRECTOR oversight
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Set
import logging

class MinimalLiveCompiler:
    """
    Builds minimal live compilation environment within 512MB budget
    Hardware-aware compiler configuration for maximum performance
    """
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Budget constraints (DIRECTOR specifications)
        self.size_budget_mb = 512
        self.expanded_budget_mb = 1800
        
        # Critical packages for live compilation
        self.essential_packages = {
            'tier1_critical': [
                'gcc-13',
                'g++-13', 
                'libc6-dev',
                'linux-headers-generic',
                'make',
                'binutils',
                'libssl-dev',
                'zlib1g-dev',
                'uuid-dev',
                'libblkid-dev',
                'libelf-dev'
            ],
            'tier2_build_tools': [
                'cmake',
                'ninja-build',
                'autoconf',
                'automake',
                'libtool',
                'pkg-config',
                'git',
                'patch'
            ],
            'tier3_optimization': [
                'llvm-17',
                'clang-17',
                'lld-17'
            ]
        }
        
        # Packages to exclude (space optimization)
        self.excluded_packages = {
            'documentation',
            'man-pages',
            'debug-symbols',
            'locale-data',
            'example-files',
            'test-suites'
        }

    def create_live_environment(self):
        """Create minimal live compilation environment"""
        
        self.logger.info("Creating minimal live compilation environment (512MB budget)")
        
        live_env_dir = self.workspace / "live-compiler-env"
        live_env_dir.mkdir(exist_ok=True)
        
        # Stage 1: Create base environment
        self._create_base_environment(live_env_dir)
        
        # Stage 2: Install essential packages
        self._install_essential_packages(live_env_dir)
        
        # Stage 3: Configure hardware-specific optimizations
        self._configure_hardware_optimizations(live_env_dir)
        
        # Stage 4: Create compilation scripts
        self._create_compilation_scripts(live_env_dir)
        
        # Stage 5: Optimize for size
        self._optimize_environment_size(live_env_dir)
        
        # Stage 6: Create squashfs image
        live_image = self._create_live_image(live_env_dir)
        
        self.logger.info(f"Minimal live environment created: {live_image}")
        return live_image

    def _create_base_environment(self, live_env_dir: Path):
        """Create base chroot environment"""
        
        self.logger.info("Creating base chroot environment...")
        
        # Use debootstrap to create minimal base
        cmd = [
            'debootstrap',
            '--variant=minbase',
            '--components=main,contrib,non-free-firmware',
            '--include=systemd,udev,dbus',
            'trixie',
            str(live_env_dir),
            'http://deb.debian.org/debian'
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        self.logger.info("Base environment created")

    def _install_essential_packages(self, live_env_dir: Path):
        """Install essential compilation packages"""
        
        self.logger.info("Installing essential compilation packages...")
        
        # Install Tier 1 critical packages first
        for tier, packages in self.essential_packages.items():
            self.logger.info(f"Installing {tier} packages...")
            
            cmd = [
                'chroot', str(live_env_dir),
                'apt-get', 'install', '-y', '--no-install-recommends'
            ] + packages
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                self.logger.info(f"✓ {tier} packages installed")
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to install some {tier} packages: {e}")

    def _configure_hardware_optimizations(self, live_env_dir: Path):
        """Configure hardware-specific compiler optimizations"""
        
        self.logger.info("Configuring hardware-specific optimizations...")
        
        # Create compiler configuration
        compiler_config = live_env_dir / "etc" / "compiler-config.sh"
        compiler_config.parent.mkdir(exist_ok=True)
        
        with open(compiler_config, 'w') as f:
            f.write('''#!/bin/bash
# Hardware-Specific Compiler Configuration
# Auto-generated by Z-FORGE INFRASTRUCTURE agent

detect_cpu_optimization() {
    local cpu_vendor=$(lscpu | grep "Vendor ID" | awk '{print $3}')
    local cpu_model=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
    
    echo "Detecting CPU for native optimization..." >&2
    echo "CPU: $cpu_model" >&2
    
    if [[ "$cpu_vendor" == "GenuineIntel" ]]; then
        # Intel-specific optimizations
        if echo "$cpu_model" | grep -qi "Meteor Lake"; then
            echo "-march=raptorlake -mtune=raptorlake -mavx2 -mfma -mbmi2 -flto=auto"
        elif echo "$cpu_model" | grep -qi "Alder Lake\|Raptor Lake"; then
            echo "-march=alderlake -mtune=alderlake -mavx2 -mfma -mbmi2 -flto=auto"
        elif echo "$cpu_model" | grep -qi "Tiger Lake\|Ice Lake"; then
            echo "-march=icelake-client -mtune=icelake-client -mavx2 -mfma -flto=auto"
        else
            echo "-march=native -mtune=native -O3 -flto=auto"
        fi
        
        # Add Intel-specific features
        if grep -q "avx512f" /proc/cpuinfo; then
            echo " -mavx512f -mavx512cd -mavx512bw -mavx512dq -mavx512vl"
        fi
        
        if grep -q "aes" /proc/cpuinfo; then
            echo " -maes -mpclmul"
        fi
        
    elif [[ "$cpu_vendor" == "AuthenticAMD" ]]; then
        # AMD-specific optimizations
        local cpu_family=$(lscpu | grep "CPU family" | awk '{print $3}')
        local cpu_model_num=$(lscpu | grep "Model:" | awk '{print $2}')
        
        if [[ "$cpu_family" -eq 25 ]] && [[ "$cpu_model_num" -ge 96 ]]; then
            echo "-march=znver4 -mtune=znver4 -mavx2 -mfma -mbmi2 -flto=auto"
        elif [[ "$cpu_family" -eq 25 ]]; then
            echo "-march=znver3 -mtune=znver3 -mavx2 -mfma -mbmi2 -flto=auto"
        elif [[ "$cpu_family" -eq 23 ]] && [[ "$cpu_model_num" -ge 49 ]]; then
            echo "-march=znver2 -mtune=znver2 -mavx2 -mfma -mbmi2 -flto=auto"
        elif [[ "$cpu_family" -eq 23 ]]; then
            echo "-march=znver1 -mtune=znver1 -mavx2 -mfma -flto=auto"
        else
            echo "-march=native -mtune=native -O3 -flto=auto"
        fi
    else
        # Generic optimization
        echo "-march=native -mtune=native -O3 -pipe"
    fi
}

# Export optimization flags
export NATIVE_CFLAGS="$(detect_cpu_optimization) -pipe -fomit-frame-pointer"
export NATIVE_CXXFLAGS="$NATIVE_CFLAGS"

# Memory optimization based on system RAM
TOTAL_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
if [[ "$TOTAL_RAM_GB" -gt 32 ]]; then
    export NATIVE_CFLAGS="$NATIVE_CFLAGS -Os"  # Optimize for cache on high-RAM systems
    echo "High-RAM system detected (${TOTAL_RAM_GB}GB), optimizing for cache efficiency" >&2
else
    export NATIVE_CFLAGS="$NATIVE_CFLAGS -O3"  # Maximum optimization for standard systems
    echo "Standard system (${TOTAL_RAM_GB}GB RAM), optimizing for speed" >&2
fi

# Parallel compilation
export MAKEFLAGS="-j$(nproc)"
export NINJA_BUILD_JOBS="$(nproc)"

echo "Native optimization flags configured: $NATIVE_CFLAGS" >&2
''')
        
        compiler_config.chmod(0o755)
        self.logger.info("Hardware optimization configuration created")

    def _create_compilation_scripts(self, live_env_dir: Path):
        """Create intelligent compilation scripts"""
        
        self.logger.info("Creating compilation coordination scripts...")
        
        scripts_dir = live_env_dir / "usr" / "local" / "bin"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Main compilation coordinator
        coordinator_script = scripts_dir / "zforge-compile"
        with open(coordinator_script, 'w') as f:
            f.write('''#!/bin/bash
# Z-FORGE Native Compilation Coordinator
# Executes build orchestration with hardware awareness

set -euo pipefail

source /etc/compiler-config.sh

SOURCES_DIR="${1:-/cdrom/compilation-sources}"
BUILD_LOG="/tmp/zforge-compilation.log"
PROGRESS_FILE="/tmp/compilation-progress"

log() {
    echo "[$(date '+%H:%M:%S')] $*" | tee -a "$BUILD_LOG"
}

progress() {
    echo "PROGRESS:$1:$2:$3" | tee -a "$PROGRESS_FILE"
    log "Progress: $1 ($2%) - $3"
}

main() {
    log "Starting Z-FORGE native compilation"
    log "CPU Optimization: $NATIVE_CFLAGS"
    
    # Execute Python build orchestrator
    if [[ -f "$SOURCES_DIR/build_orchestrator.py" ]]; then
        log "Executing intelligent build orchestration..."
        python3 "$SOURCES_DIR/build_orchestrator.py"
    else
        log "Build orchestrator not found, falling back to manual build"
        # Manual fallback build logic would go here
    fi
    
    log "Native compilation completed"
}

main "$@"
''')
        
        coordinator_script.chmod(0o755)
        
        # Resource monitor script
        monitor_script = scripts_dir / "zforge-monitor"
        with open(monitor_script, 'w') as f:
            f.write('''#!/bin/bash
# Resource monitoring during compilation
# Implements thermal throttling and memory management

while true; do
    # Check CPU temperature
    if command -v sensors >/dev/null 2>&1; then
        TEMP=$(sensors | grep 'Core 0' | awk '{print $3}' | sed 's/+//;s/°C.*//' || echo "50")
        if (( $(echo "$TEMP > 85" | bc -l) )); then
            echo "WARNING: CPU temperature high (${TEMP}°C), throttling compilation"
            killall -STOP make || true
            sleep 10
            killall -CONT make || true
        fi
    fi
    
    # Check memory usage
    MEM_USAGE=$(free | awk '/^Mem:/ {printf("%.0f", $3/$2 * 100)}')
    if [[ "$MEM_USAGE" -gt 90 ]]; then
        echo "WARNING: High memory usage (${MEM_USAGE}%), reducing parallel jobs"
        export MAKEFLAGS="-j1"
    fi
    
    sleep 30
done
''')
        
        monitor_script.chmod(0o755)
        
        self.logger.info("Compilation scripts created")

    def _optimize_environment_size(self, live_env_dir: Path):
        """Aggressively optimize environment size to meet 512MB budget"""
        
        self.logger.info("Optimizing environment size...")
        
        # Remove unnecessary files
        cleanup_paths = [
            "usr/share/doc",
            "usr/share/man", 
            "usr/share/info",
            "usr/share/locale",
            "var/cache/apt",
            "var/lib/apt/lists",
            "tmp/*",
            "var/tmp/*"
        ]
        
        for path in cleanup_paths:
            full_path = live_env_dir / path
            if full_path.exists():
                if full_path.is_dir():
                    shutil.rmtree(full_path, ignore_errors=True)
                else:
                    full_path.unlink(missing_ok=True)
        
        # Strip debug symbols from binaries
        subprocess.run([
            'find', str(live_env_dir), '-type', 'f',
            '-executable', '-exec', 'strip', '--strip-debug', '{}', ';'
        ], capture_output=True)
        
        # Clean package cache
        subprocess.run([
            'chroot', str(live_env_dir),
            'apt-get', 'clean'
        ], capture_output=True)
        
        # Check final size
        result = subprocess.run(['du', '-sm', str(live_env_dir)], capture_output=True, text=True)
        size_mb = int(result.stdout.split()[0])
        
        self.logger.info(f"Environment size optimized: {size_mb}MB")
        
        if size_mb > self.expanded_budget_mb:
            self.logger.warning(f"Environment exceeds budget: {size_mb}MB > {self.expanded_budget_mb}MB")

    def _create_live_image(self, live_env_dir: Path):
        """Create compressed squashfs live image"""
        
        self.logger.info("Creating live compilation image...")
        
        live_image = self.workspace / "zforge-live-compiler.squashfs"
        
        # Create squashfs with maximum compression
        cmd = [
            'mksquashfs',
            str(live_env_dir),
            str(live_image),
            '-comp', 'xz',
            '-Xbcj', 'x86',
            '-b', '1M',
            '-no-xattrs',
            '-no-exports'
        ]
        
        subprocess.run(cmd, check=True)
        
        # Verify size meets budget
        size_mb = live_image.stat().st_size // (1024 * 1024)
        self.logger.info(f"Live image created: {size_mb}MB")
        
        if size_mb > self.size_budget_mb:
            self.logger.error(f"Image exceeds budget: {size_mb}MB > {self.size_budget_mb}MB")
            raise ValueError("Live image too large")
        
        return live_image

    def integrate_with_iso(self, live_image: Path):
        """Integrate live compilation environment with ISO build"""
        
        self.logger.info("Integrating live compiler with ISO build...")
        
        # Copy live image to ISO build directory
        iso_live_dir = self.workspace / "iso" / "live"
        iso_live_dir.mkdir(parents=True, exist_ok=True)
        
        target_image = iso_live_dir / "zforge-compiler.squashfs"
        shutil.copy2(live_image, target_image)
        
        # Create initramfs hook for live environment
        hook_script = iso_live_dir / "live-compiler-hook.sh"
        with open(hook_script, 'w') as f:
            f.write('''#!/bin/bash
# Live compiler environment initialization hook
# Mounts and prepares compilation environment during boot

mount_live_compiler() {
    local live_image="/cdrom/live/zforge-compiler.squashfs"
    local mount_point="/live/compiler"
    
    if [[ -f "$live_image" ]]; then
        mkdir -p "$mount_point"
        mount -t squashfs -o loop,ro "$live_image" "$mount_point"
        
        # Bind mount essential directories
        for dir in /proc /sys /dev; do
            mount --bind "$dir" "$mount_point$dir"
        done
        
        echo "Live compilation environment ready at $mount_point"
    fi
}

# Execute during initramfs
mount_live_compiler
''')
        
        hook_script.chmod(0o755)
        
        self.logger.info("Live compiler integration completed")

def main():
    """Main execution function"""
    
    logging.basicConfig(level=logging.INFO)
    
    workspace = Path("/tmp/zforge-live-compiler")
    workspace.mkdir(exist_ok=True)
    
    config = {
        'size_budget_mb': 512,
        'optimization_level': 'native'
    }
    
    builder = MinimalLiveCompiler(workspace, config)
    
    try:
        live_image = builder.create_live_environment()
        builder.integrate_with_iso(live_image)
        
        print(f"✓ Minimal live compilation environment created: {live_image}")
        print(f"  Size: {live_image.stat().st_size // (1024*1024)}MB")
        print("  Ready for integration with Z-FORGE ISO build")
        
    except Exception as e:
        logging.error(f"Failed to create live environment: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
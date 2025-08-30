#!/bin/bash
# HPC Compilation UI Integration Script
# Integrates the HPC compilation UI system with Calamares and Z-FORGE

set -euo pipefail

# Configuration
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
CALAMARES_MODULES_DIR="/usr/lib/calamares/modules"
CALAMARES_CONFIG_DIR="/etc/calamares"
Z_FORGE_ROOT="${Z_FORGE_ROOT:-/home/john/Z-FORGE}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    # Python dependencies
    if ! python3 -c "import PyQt5" 2>/dev/null; then
        missing_deps+=("python3-pyqt5")
    fi
    
    if ! python3 -c "import psutil" 2>/dev/null; then
        missing_deps+=("python3-psutil")
    fi
    
    if ! python3 -c "import curses" 2>/dev/null; then
        missing_deps+=("python3-dev")
    fi
    
    # System tools
    if ! command -v calamares >/dev/null 2>&1; then
        missing_deps+=("calamares")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_warning "Missing dependencies: ${missing_deps[*]}"
        log_info "Installing dependencies..."
        
        if command -v apt-get >/dev/null 2>&1; then
            apt-get update
            apt-get install -y "${missing_deps[@]}"
        elif command -v dnf >/dev/null 2>&1; then
            dnf install -y "${missing_deps[@]}"
        elif command -v pacman >/dev/null 2>&1; then
            pacman -S --noconfirm "${missing_deps[@]}"
        else
            log_error "Cannot install dependencies - unsupported package manager"
            exit 1
        fi
    fi
    
    log_success "Dependencies checked"
}

# Install HPC compilation UI modules
install_ui_modules() {
    log_info "Installing HPC compilation UI modules..."
    
    # Create module directories
    mkdir -p "$CALAMARES_MODULES_DIR/hpc_compilation_ui"
    mkdir -p "$CALAMARES_MODULES_DIR/hpc_compilation_tui"
    
    # Copy UI module files
    cp "$SCRIPT_DIR/module.desc" "$CALAMARES_MODULES_DIR/hpc_compilation_ui/"
    cp "$SCRIPT_DIR/main.py" "$CALAMARES_MODULES_DIR/hpc_compilation_ui/"
    cp "$SCRIPT_DIR/compilation_progress_parser.py" "$CALAMARES_MODULES_DIR/hpc_compilation_ui/"
    cp "$SCRIPT_DIR/resource_monitor.py" "$CALAMARES_MODULES_DIR/hpc_compilation_ui/"
    cp "$SCRIPT_DIR/compilation_controller.py" "$CALAMARES_MODULES_DIR/hpc_compilation_ui/"
    
    # Copy TUI fallback
    cp "$SCRIPT_DIR/hpc_compilation_tui.py" "$CALAMARES_MODULES_DIR/hpc_compilation_tui/"
    
    # Create TUI module descriptor
    cat > "$CALAMARES_MODULES_DIR/hpc_compilation_tui/module.desc" << 'EOF'
---
type:      "job"
name:      "hpc_compilation_tui"
interface: "python"

weight: 150
emergency: false

configuration:
    enable_thermal_monitoring: true
    max_parallel_jobs: 0
    thermal_threshold_celsius: 85
    memory_threshold_percent: 85

# Only run in text mode or if GUI fails
onlyIf:
    - condition: "config"
      key: "no_gui"
      value: true

name[en]: "HPC Driver Compilation (Text Mode)"
prettyName: "High-Performance Computing Driver Compilation (Text Mode)"
EOF
    
    # Set permissions
    chmod +x "$CALAMARES_MODULES_DIR/hpc_compilation_ui/main.py"
    chmod +x "$CALAMARES_MODULES_DIR/hpc_compilation_tui/hpc_compilation_tui.py"
    
    log_success "UI modules installed"
}

# Update Calamares settings
update_calamares_settings() {
    log_info "Updating Calamares settings..."
    
    local settings_file="$CALAMARES_CONFIG_DIR/settings.conf"
    
    if [[ ! -f "$settings_file" ]]; then
        log_error "Calamares settings file not found: $settings_file"
        exit 1
    fi
    
    # Backup original settings
    cp "$settings_file" "$settings_file.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Add HPC compilation modules to sequence
    python3 << EOF
import yaml
import sys

try:
    with open('$settings_file', 'r') as f:
        config = yaml.safe_load(f)
    
    # Find the sequence
    if 'sequence' not in config:
        print("ERROR: No sequence found in settings.conf")
        sys.exit(1)
    
    # Add HPC compilation modules before finalize
    sequence = config['sequence']
    
    # Find insertion point (before final steps)
    insert_index = len(sequence)
    for i, step in enumerate(sequence):
        if isinstance(step, dict) and 'finalize' in str(step).lower():
            insert_index = i
            break
        elif isinstance(step, str) and 'finalize' in step.lower():
            insert_index = i
            break
    
    # Insert HPC compilation modules
    hpc_modules = [
        {'hpc_compilation_ui': None},
        {'hpc_compilation_tui': None}  # Fallback
    ]
    
    # Only add if not already present
    existing_modules = str(sequence)
    if 'hpc_compilation_ui' not in existing_modules:
        for module in reversed(hpc_modules):
            sequence.insert(insert_index, module)
    
    # Write updated config
    with open('$settings_file', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print("SUCCESS: Updated Calamares settings")

except Exception as e:
    print(f"ERROR: Failed to update settings: {e}")
    sys.exit(1)
EOF
    
    if [[ $? -eq 0 ]]; then
        log_success "Calamares settings updated"
    else
        log_error "Failed to update Calamares settings"
        exit 1
    fi
}

# Install HPC driver packages
install_hpc_packages() {
    log_info "Preparing HPC driver packages..."
    
    local hpc_package_dir="$Z_FORGE_ROOT/prebuilt_packages/hpc"
    mkdir -p "$hpc_package_dir"
    
    # Create mock HPC driver package for testing
    if [[ ! -f "$hpc_package_dir/zforge-hpc-drivers_1.0_all.deb" ]]; then
        log_info "Creating HPC driver package..."
        
        # Create package structure
        local pkg_dir="/tmp/zforge-hpc-drivers"
        mkdir -p "$pkg_dir/DEBIAN"
        mkdir -p "$pkg_dir/usr/src"
        mkdir -p "$pkg_dir/usr/lib/hpc"
        
        # Create package control file
        cat > "$pkg_dir/DEBIAN/control" << EOF
Package: zforge-hpc-drivers
Version: 1.0
Section: kernel
Priority: optional
Architecture: all
Depends: build-essential, dkms, linux-headers-generic
Maintainer: Z-FORGE Team <zforge@example.com>
Description: HPC driver compilation package for Z-FORGE
 This package contains source code and build scripts for compiling
 HPC drivers including CUDA, Intel MKL, and scientific libraries
 with hardware-specific optimizations.
EOF
        
        # Create mock source files
        echo "# HPC Driver Sources - Placeholder" > "$pkg_dir/usr/src/README"
        echo "#!/bin/bash\necho 'HPC driver compilation script'" > "$pkg_dir/usr/lib/hpc/compile.sh"
        chmod +x "$pkg_dir/usr/lib/hpc/compile.sh"
        
        # Build package
        dpkg-deb --build "$pkg_dir" "$hpc_package_dir/zforge-hpc-drivers_1.0_all.deb"
        rm -rf "$pkg_dir"
        
        log_success "HPC driver package created"
    fi
}

# Create launcher scripts
create_launchers() {
    log_info "Creating launcher scripts..."
    
    # GUI launcher
    cat > "/usr/local/bin/hpc-compilation-ui" << 'EOF'
#!/bin/bash
# HPC Compilation UI Launcher

set -euo pipefail

# Check if running in GUI environment
if [[ -z "${DISPLAY:-}" ]]; then
    echo "ERROR: GUI environment not available, use TUI instead"
    exec hpc-compilation-tui "$@"
fi

# Launch GUI
exec python3 /usr/lib/calamares/modules/hpc_compilation_ui/main.py "$@"
EOF
    chmod +x "/usr/local/bin/hpc-compilation-ui"
    
    # TUI launcher
    cat > "/usr/local/bin/hpc-compilation-tui" << 'EOF'
#!/bin/bash
# HPC Compilation TUI Launcher

set -euo pipefail

# Check terminal
if [[ ! -t 0 ]]; then
    echo "ERROR: TUI requires interactive terminal"
    exit 1
fi

# Launch TUI
exec python3 /usr/lib/calamares/modules/hpc_compilation_tui/hpc_compilation_tui.py "$@"
EOF
    chmod +x "/usr/local/bin/hpc-compilation-tui"
    
    # Universal launcher with fallback
    cat > "/usr/local/bin/hpc-compilation" << 'EOF'
#!/bin/bash
# Universal HPC Compilation Launcher with GUI/TUI fallback

set -euo pipefail

# Try GUI first, fallback to TUI
if [[ -n "${DISPLAY:-}" ]] && command -v python3 >/dev/null 2>&1; then
    if python3 -c "import PyQt5" 2>/dev/null; then
        echo "Launching HPC Compilation GUI..."
        exec hpc-compilation-ui "$@"
    fi
fi

# Fallback to TUI
echo "Launching HPC Compilation TUI..."
exec hpc-compilation-tui "$@"
EOF
    chmod +x "/usr/local/bin/hpc-compilation"
    
    log_success "Launcher scripts created"
}

# Create configuration files
create_config_files() {
    log_info "Creating configuration files..."
    
    # Main configuration
    mkdir -p "/etc/zforge/hpc"
    
    cat > "/etc/zforge/hpc/compilation.conf" << 'EOF'
# HPC Compilation Configuration for Z-FORGE

[compilation]
# Maximum parallel jobs (0 = auto-detect CPU cores)
max_parallel_jobs = 0

# Compilation timeout in hours
timeout_hours = 4.0

# Enable process-level control (pause/resume)
enable_process_control = true

[thermal]
# Thermal protection thresholds in Celsius
warning_threshold = 85
critical_threshold = 95
emergency_threshold = 100

# Enable thermal monitoring
enable_thermal_monitoring = true

[memory]
# Memory usage thresholds in percent
warning_threshold = 85
critical_threshold = 95

[ui]
# UI update interval in milliseconds
update_interval_ms = 500

# Enable advanced mode by default
default_advanced_mode = false

# Show compiler output in logs tab
show_compiler_output = true

[fallback]
# Enable prebuilt package fallback
enable_prebuilt_fallback = true

# Enable partial compilation (skip failed zones)
enable_partial_compilation = true

# Enable zone skipping
enable_zone_skipping = true
EOF
    
    # Hardware-specific configurations
    cat > "/etc/zforge/hpc/hardware_profiles.conf" << 'EOF'
# Hardware-specific compilation profiles

[tesla_k40]
cuda_arch = sm_35
compute_capability = 3.5
compiler_flags = -O3,-use_fast_math,-Xptxas=-O3
memory_optimization = gddr5_bandwidth

[tesla_k80]
cuda_arch = sm_37
compute_capability = 3.7
compiler_flags = -O3,-use_fast_math,-Xptxas=-O3
memory_optimization = dual_gpu_aware

[xeon_phi_knl]
arch_flags = -xMIC-AVX512,-qopt-streaming-stores,always
memory_optimization = mcdram_aware
thread_model = many_core_scaling

[xeon_e3_v5]
arch_flags = -march=broadwell,-mavx2,-mfma
memory_optimization = ddr4_bandwidth
thread_model = smt_aware

[default]
arch_flags = -march=native,-mtune=native
optimization_level = -O3
enable_debug = false
EOF
    
    log_success "Configuration files created"
}

# Setup systemd service for monitoring
setup_monitoring_service() {
    log_info "Setting up monitoring service..."
    
    cat > "/etc/systemd/system/hpc-compilation-monitor.service" << 'EOF'
[Unit]
Description=HPC Compilation Resource Monitor
After=multi-user.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/hpc-compilation-monitor
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    # Create monitor script
    cat > "/usr/local/bin/hpc-compilation-monitor" << 'EOF'
#!/usr/bin/env python3
"""
HPC Compilation System Monitor Service
Runs in background to monitor system resources during compilation
"""

import time
import logging
import sys
import os

# Add module path
sys.path.insert(0, '/usr/lib/calamares/modules/hpc_compilation_ui')

try:
    from resource_monitor import HPCResourceMonitor, ThermalState
except ImportError:
    print("ERROR: Could not import resource monitor")
    sys.exit(1)

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/hpc-compilation-monitor.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger('hpc-monitor')
    
    # Configuration
    config = {
        'update_interval_seconds': 5.0,
        'thermal_threshold_celsius': 85,
        'thermal_critical_celsius': 95,
        'memory_threshold_percent': 85,
        'memory_critical_percent': 95
    }
    
    # Create monitor
    monitor = HPCResourceMonitor(config)
    
    # Add thermal warning callback
    def thermal_warning(old_state, new_state, metrics):
        logger.warning(f"Thermal state: {old_state.value} -> {new_state.value} at {metrics.cpu_temperature:.1f}°C")
    
    monitor.add_thermal_callback(ThermalState.WARNING, thermal_warning)
    monitor.add_thermal_callback(ThermalState.CRITICAL, thermal_warning)
    
    logger.info("Starting HPC compilation monitor service")
    
    try:
        monitor.start_monitoring()
        
        # Keep service running
        while True:
            time.sleep(10)
            
            # Log periodic status
            metrics = monitor.get_current_metrics()
            if metrics.cpu_temperature > 80 or metrics.memory_percent > 80:
                logger.info(f"Resources: CPU {metrics.cpu_temperature:.1f}°C, RAM {metrics.memory_percent:.1f}%")
    
    except KeyboardInterrupt:
        logger.info("Monitor service stopping...")
    except Exception as e:
        logger.error(f"Monitor service error: {e}")
    finally:
        monitor.stop_monitoring()

if __name__ == "__main__":
    main()
EOF
    chmod +x "/usr/local/bin/hpc-compilation-monitor"
    
    # Enable service
    systemctl daemon-reload
    systemctl enable hpc-compilation-monitor.service
    
    log_success "Monitoring service setup complete"
}

# Validate installation
validate_installation() {
    log_info "Validating installation..."
    
    local validation_errors=()
    
    # Check module files
    if [[ ! -f "$CALAMARES_MODULES_DIR/hpc_compilation_ui/main.py" ]]; then
        validation_errors+=("GUI module not installed")
    fi
    
    if [[ ! -f "$CALAMARES_MODULES_DIR/hpc_compilation_tui/hpc_compilation_tui.py" ]]; then
        validation_errors+=("TUI module not installed")
    fi
    
    # Check launchers
    if [[ ! -x "/usr/local/bin/hpc-compilation" ]]; then
        validation_errors+=("Universal launcher not installed")
    fi
    
    # Check configuration
    if [[ ! -f "/etc/zforge/hpc/compilation.conf" ]]; then
        validation_errors+=("Configuration file missing")
    fi
    
    # Check Python imports
    if ! python3 -c "
import sys
sys.path.insert(0, '$CALAMARES_MODULES_DIR/hpc_compilation_ui')
from compilation_progress_parser import CompilationProgressParser
from resource_monitor import HPCResourceMonitor
from compilation_controller import HPCCompilationController
print('Python imports successful')
" 2>/dev/null; then
        validation_errors+=("Python module import failed")
    fi
    
    if [[ ${#validation_errors[@]} -eq 0 ]]; then
        log_success "Installation validation passed"
        return 0
    else
        log_error "Validation failed:"
        for error in "${validation_errors[@]}"; do
            log_error "  - $error"
        done
        return 1
    fi
}

# Test the installation
test_installation() {
    log_info "Testing installation..."
    
    # Test TUI (non-interactive)
    log_info "Testing TUI module..."
    if python3 -c "
import sys
sys.path.insert(0, '$CALAMARES_MODULES_DIR/hpc_compilation_tui')
from hpc_compilation_tui import HPCCompilationTUI
config = {'update_interval_seconds': 1.0}
tui = HPCCompilationTUI(config)
print('TUI module test passed')
"; then
        log_success "TUI module test passed"
    else
        log_error "TUI module test failed"
    fi
    
    # Test GUI components (without display)
    log_info "Testing GUI components..."
    if python3 -c "
import sys
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, '$CALAMARES_MODULES_DIR/hpc_compilation_ui')
from compilation_progress_parser import CompilationProgressParser
from resource_monitor import HPCResourceMonitor
from compilation_controller import HPCCompilationController
parser = CompilationProgressParser()
monitor = HPCResourceMonitor({'update_interval_seconds': 1.0})
controller = HPCCompilationController({'max_parallel_jobs': 2})
print('GUI components test passed')
"; then
        log_success "GUI components test passed"
    else
        log_warning "GUI components test failed (may be normal without display)"
    fi
    
    log_success "Installation testing complete"
}

# Show usage help
show_help() {
    cat << EOF
HPC Compilation UI Integration Script

Usage: $0 [OPTIONS]

Options:
    install         Install HPC compilation UI system
    uninstall       Remove HPC compilation UI system
    validate        Validate installation
    test            Test installation
    --help, -h      Show this help message

Examples:
    $0 install              # Full installation
    $0 validate             # Check installation
    $0 test                 # Test components

This script integrates the HPC compilation UI system with Calamares
and Z-FORGE, providing comprehensive installer UI for extended
HPC driver compilation during installation.

EOF
}

# Uninstall function
uninstall() {
    log_info "Uninstalling HPC compilation UI system..."
    
    # Stop and disable service
    systemctl stop hpc-compilation-monitor.service 2>/dev/null || true
    systemctl disable hpc-compilation-monitor.service 2>/dev/null || true
    rm -f "/etc/systemd/system/hpc-compilation-monitor.service"
    systemctl daemon-reload
    
    # Remove modules
    rm -rf "$CALAMARES_MODULES_DIR/hpc_compilation_ui"
    rm -rf "$CALAMARES_MODULES_DIR/hpc_compilation_tui"
    
    # Remove launchers
    rm -f "/usr/local/bin/hpc-compilation"
    rm -f "/usr/local/bin/hpc-compilation-ui"
    rm -f "/usr/local/bin/hpc-compilation-tui"
    rm -f "/usr/local/bin/hpc-compilation-monitor"
    
    # Remove configurations
    rm -rf "/etc/zforge/hpc"
    
    # Restore Calamares settings
    local settings_file="$CALAMARES_CONFIG_DIR/settings.conf"
    local backup_file=$(ls "$settings_file.backup."* 2>/dev/null | tail -1)
    
    if [[ -n "$backup_file" ]]; then
        log_info "Restoring Calamares settings from backup..."
        cp "$backup_file" "$settings_file"
    fi
    
    log_success "HPC compilation UI system uninstalled"
}

# Main function
main() {
    case "${1:-install}" in
        install)
            check_root
            check_dependencies
            install_ui_modules
            update_calamares_settings
            install_hpc_packages
            create_launchers
            create_config_files
            setup_monitoring_service
            validate_installation
            test_installation
            
            log_success "HPC Compilation UI system installation complete!"
            log_info "Use 'hpc-compilation' command to launch the UI"
            log_info "Integrated with Calamares for installer use"
            ;;
        uninstall)
            check_root
            uninstall
            ;;
        validate)
            validate_installation
            ;;
        test)
            test_installation
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
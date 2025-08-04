#!/bin/bash
#
# Z-FORGE Live Environment Builder
# Creates a live environment with Calamares GUI integration
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
WORKSPACE="${WORKSPACE:-$HOME/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"
OUTPUT_DIR="$WORKSPACE/output"
LOG_DIR="$WORKSPACE/logs"
DESKTOP_ENV="${DESKTOP_ENVIRONMENT:-minimal}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

# Create directories
setup_directories() {
    log "Setting up directories..."
    mkdir -p "$WORKSPACE"
    mkdir -p "$CHROOT_PATH"
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$LOG_DIR"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    local required_tools=(
        "debootstrap"
        "chroot"
        "mksquashfs"
        "xorriso"
    )
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            error "Required tool not found: $tool"
            error "Please install it first"
            exit 1
        fi
    done
    
    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root or with sudo"
        exit 1
    fi
}

# Run live environment module
run_live_environment_module() {
    log "Running live environment module..."
    
    cd "$PROJECT_ROOT"
    
    # Create a minimal config for live environment
    cat > "$WORKSPACE/live_env_config.yml" << EOF
builder_config:
  workspace_path: $WORKSPACE
  debian_release: trixie
  kernel_version: 6.14.8-1

modules:
- name: live_environment
  enabled: true
  config:
    autologin: true
    user: zforge
    desktop_environment: $DESKTOP_ENV

- name: desktop_environment
  enabled: true
  config:
    desktop_environment: $DESKTOP_ENV
    
- name: calamares_integration
  enabled: true
  config:
    enable_gui: true
EOF
    
    # Run the specific modules
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from builder.modules.live_environment import LiveEnvironment
from builder.modules.desktop_environment import DesktopEnvironment
from builder.modules.calamares_integration import CalamaresIntegration
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

workspace = Path('$WORKSPACE')
config = {
    'autologin': True,
    'user': 'zforge',
    'desktop_environment': '$DESKTOP_ENV'
}

# Run live environment setup
print('Setting up live environment...')
live_env = LiveEnvironment(workspace, config)
result = live_env.execute()
print(f'Live environment result: {result}')

# Run desktop setup
print('Setting up desktop environment...')
desktop = DesktopEnvironment(workspace, config)
result = desktop.execute()
print(f'Desktop environment result: {result}')

# Run Calamares integration
print('Setting up Calamares GUI...')
calamares_config = {'enable_gui': True}
calamares = CalamaresIntegration(workspace, calamares_config)
result = calamares.execute()
print(f'Calamares integration result: {result}')
"
}

# Install Calamares in chroot
install_calamares() {
    log "Installing Calamares..."
    
    # Update package list
    chroot "$CHROOT_PATH" apt-get update
    
    # Install Calamares and dependencies
    chroot "$CHROOT_PATH" apt-get install -y \
        calamares \
        calamares-settings-debian \
        qml-module-qtquick2 \
        qml-module-qtquick-controls \
        qml-module-qtquick-controls2 \
        qml-module-qtquick-layouts \
        qml-module-qtquick-window2
}

# Setup desktop environment
setup_desktop() {
    log "Setting up desktop environment..."
    
    # Run desktop setup script
    if [ -x "$PROJECT_ROOT/scripts/desktop/setup_live_desktop.sh" ]; then
        "$PROJECT_ROOT/scripts/desktop/setup_live_desktop.sh" "$CHROOT_PATH"
    else
        warning "Desktop setup script not found, creating minimal setup..."
        
        # Minimal X setup
        chroot "$CHROOT_PATH" apt-get install -y \
            xorg \
            openbox \
            lightdm \
            xterm
        
        # Enable auto-login
        mkdir -p "$CHROOT_PATH/etc/lightdm/lightdm.conf.d"
        cat > "$CHROOT_PATH/etc/lightdm/lightdm.conf.d/99-autologin.conf" << EOF
[Seat:*]
autologin-user=zforge
autologin-user-timeout=0
EOF
    fi
}

# Create squashfs
create_squashfs() {
    log "Creating squashfs filesystem..."
    
    local squashfs_path="$OUTPUT_DIR/filesystem.squashfs"
    
    # Remove old squashfs if exists
    rm -f "$squashfs_path"
    
    # Create squashfs with best compression
    mksquashfs "$CHROOT_PATH" "$squashfs_path" \
        -comp xz \
        -no-recovery \
        -no-exports \
        -wildcards \
        -e 'proc/*' \
        -e 'sys/*' \
        -e 'dev/*' \
        -e 'run/*' \
        -e 'tmp/*' \
        -e 'var/cache/apt/archives/*.deb'
    
    log "Squashfs created: $squashfs_path"
}

# Create ISO structure
create_iso_structure() {
    log "Creating ISO structure..."
    
    local iso_dir="$WORKSPACE/iso"
    rm -rf "$iso_dir"
    mkdir -p "$iso_dir"/{live,isolinux,boot/grub}
    
    # Copy squashfs
    cp "$OUTPUT_DIR/filesystem.squashfs" "$iso_dir/live/"
    
    # Copy kernel and initrd
    cp "$CHROOT_PATH/boot/vmlinuz-"* "$iso_dir/live/vmlinuz"
    cp "$CHROOT_PATH/boot/initrd.img-"* "$iso_dir/live/initrd.img"
    
    # Create boot configuration
    create_boot_config "$iso_dir"
}

# Create boot configuration
create_boot_config() {
    local iso_dir="$1"
    
    # ISOLINUX config
    cat > "$iso_dir/isolinux/isolinux.cfg" << 'EOF'
UI menu.c32
PROMPT 0
TIMEOUT 50

LABEL live
    MENU LABEL Z-FORGE Live (with Calamares Installer)
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components quiet splash

LABEL install
    MENU LABEL Install Z-FORGE
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components quiet splash install
EOF
    
    # GRUB config
    cat > "$iso_dir/boot/grub/grub.cfg" << 'EOF'
set timeout=5
set default=0

menuentry "Z-FORGE Live (with Calamares Installer)" {
    linux /live/vmlinuz boot=live components quiet splash
    initrd /live/initrd.img
}

menuentry "Install Z-FORGE" {
    linux /live/vmlinuz boot=live components quiet splash install
    initrd /live/initrd.img
}
EOF
}

# Build ISO
build_iso() {
    log "Building ISO..."
    
    local iso_dir="$WORKSPACE/iso"
    local iso_path="$OUTPUT_DIR/zforge-live-${DESKTOP_ENV}.iso"
    
    # Install ISOLINUX files
    if [ -d "/usr/lib/ISOLINUX" ]; then
        cp /usr/lib/ISOLINUX/isolinux.bin "$iso_dir/isolinux/"
        cp /usr/lib/syslinux/modules/bios/menu.c32 "$iso_dir/isolinux/"
        cp /usr/lib/syslinux/modules/bios/libutil.c32 "$iso_dir/isolinux/"
        cp /usr/lib/syslinux/modules/bios/libcom32.c32 "$iso_dir/isolinux/"
    fi
    
    # Create ISO
    xorriso -as mkisofs \
        -r -V "Z-FORGE-LIVE" \
        -cache-inodes \
        -J -l \
        -b isolinux/isolinux.bin \
        -c isolinux/boot.cat \
        -no-emul-boot \
        -boot-load-size 4 \
        -boot-info-table \
        -o "$iso_path" \
        "$iso_dir"
    
    log "ISO created: $iso_path"
}

# Test GUI connectivity
test_gui_connectivity() {
    log "Testing GUI connectivity chain..."
    
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from builder.modules.integrated_build_orchestrator import IntegratedBuildOrchestrator
from pathlib import Path

orchestrator = IntegratedBuildOrchestrator(Path('$WORKSPACE'))
result = orchestrator.test_gui_connectivity()

print('\\nGUI Connectivity Test Results:')
print(f'Complete Chain Connected: {result[\"complete_chain_connected\"]}')
print(f'Connectivity Score: {result[\"connectivity_score\"]:.2f}%')
print('\\nConnection Status:')
for key, value in result['connections'].items():
    status = '✅' if value else '❌'
    print(f'  {status} {key}: {value}')
"
}

# Main execution
main() {
    log "Z-FORGE Live Environment Builder"
    log "================================"
    
    check_prerequisites
    setup_directories
    
    # Check if chroot exists
    if [ ! -d "$CHROOT_PATH/etc" ]; then
        error "Chroot not found at $CHROOT_PATH"
        error "Please run the main build first"
        exit 1
    fi
    
    # Build live environment
    run_live_environment_module
    install_calamares
    setup_desktop
    
    # Create live ISO
    create_squashfs
    create_iso_structure
    build_iso
    
    # Test connectivity
    test_gui_connectivity
    
    log "Live environment build complete!"
    log "ISO available at: $OUTPUT_DIR/zforge-live-${DESKTOP_ENV}.iso"
}

# Run main
main "$@"
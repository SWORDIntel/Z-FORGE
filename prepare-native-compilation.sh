#!/bin/bash
# Z-FORGE Native Compilation Preparation Script
# Downloads and prepares ZFS 2.3.4 and Proxmox v9 sources
# Creates DKMS packages for native compilation at install time

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_section() { echo -e "${BLUE}==== $1 ====${NC}"; }
log_detail() { echo -e "${CYAN}  → ${NC}$1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

main() {
    log_section "Z-FORGE Native Compilation Preparation"
    log_info "Preparing ZFS 2.3.4 and Proxmox v9 for native compilation"
    echo ""
    
    cd "${PROJECT_ROOT}"
    
    # Step 1: Download ZFS 2.3.4 source
    log_info "Step 1: Downloading ZFS 2.3.4 source..."
    if [ -x "./download-zfs-2.3.4.sh" ]; then
        ./download-zfs-2.3.4.sh
    else
        log_warning "ZFS download script not found"
    fi
    
    # Step 2: Download Proxmox v9 sources
    log_info "Step 2: Downloading Proxmox v9 complete sources..."
    if [ -x "./scripts/download/download_proxmox_v9_complete.sh" ]; then
        ./scripts/download/download_proxmox_v9_complete.sh
    else
        log_warning "Proxmox download script not found"
    fi
    
    # Step 3: Build unified DKMS package
    log_info "Step 3: Building unified ZFS + Proxmox DKMS package..."
    if [ -x "./scripts/build/build_zfs_proxmox_dkms_optimized.sh" ]; then
        ./scripts/build/build_zfs_proxmox_dkms_optimized.sh
    else
        log_warning "DKMS build script not found"
    fi
    
    # Step 4: Integrate Proxmox sources
    log_info "Step 4: Integrating Proxmox sources into build system..."
    if [ -x "./proxmox-v9-sources/integrate_into_iso.sh" ]; then
        cd ./proxmox-v9-sources
        ./integrate_into_iso.sh "${PROJECT_ROOT}"
        cd "${PROJECT_ROOT}"
    else
        log_warning "Proxmox integration script not found"
    fi
    
    # Step 5: Verify everything is ready
    log_info "Step 5: Verifying preparation..."
    
    local all_ready=true
    
    # Check ZFS sources
    if [ -d "./zfs-builds" ]; then
        log_detail "✓ ZFS 2.3.4 sources downloaded"
    else
        log_warning "✗ ZFS sources missing"
        all_ready=false
    fi
    
    # Check Proxmox sources  
    if [ -d "./proxmox-v9-sources" ]; then
        log_detail "✓ Proxmox v9 sources downloaded"
    else
        log_warning "✗ Proxmox sources missing"
        all_ready=false
    fi
    
    # Check DKMS package
    if [ -f "./prebuilt_packages/zfs-proxmox-2.3.4-dkms/zforge-zfs-proxmox-dkms_2.3.4-pve9.0_all.deb" ]; then
        local pkg_size=$(du -h "./prebuilt_packages/zfs-proxmox-2.3.4-dkms/zforge-zfs-proxmox-dkms_2.3.4-pve9.0_all.deb" | cut -f1)
        log_detail "✓ Unified DKMS package created (${pkg_size})"
    else
        log_warning "✗ DKMS package missing"
        all_ready=false
    fi
    
    # Check integration
    if [ -f "./BUILD_CONFIG.sh" ]; then
        log_detail "✓ Proxmox integration complete"
    else
        log_warning "✗ Proxmox integration incomplete"
        all_ready=false
    fi
    
    echo ""
    
    if [ "$all_ready" = true ]; then
        log_section "Preparation Complete! ✅"
        echo ""
        log_info "Your Z-FORGE system is now ready for native compilation:"
        echo ""
        log_detail "ZFS 2.3.4: Will compile with CPU-specific optimizations"
        log_detail "Proxmox v9: Will compile with virtualization optimizations"
        log_detail "QEMU: Will build with native CPU targeting"
        log_detail "Kernel: Will use hardware-specific features"
        echo ""
        log_info "Build the ISO with native compilation:"
        echo ""
        echo "  sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml"
        echo ""
        log_info "During installation, the system will:"
        log_detail "1. Detect the target hardware capabilities"
        log_detail "2. Compile ZFS with AVX-512/AVX2/AES-NI support"
        log_detail "3. Build Proxmox with virtualization optimizations"
        log_detail "4. Create kernel modules for exact hardware match"
        log_detail "5. Optimize QEMU for host CPU features"
        echo ""
        log_info "This ensures maximum performance for each installation! 🚀"
        
    else
        log_section "Preparation Incomplete ❌"
        echo ""
        log_warning "Some components are missing. Please run the individual"
        log_warning "download and build scripts manually to complete setup."
        exit 1
    fi
}

# Run main function
main "$@"
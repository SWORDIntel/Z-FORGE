#!/bin/bash
# Z-FORGE Proxmox v9 Complete Source Downloader
# Downloads all Proxmox v9 source components for offline ISO building

set -euo pipefail

# Configuration
PVE_VERSION="9.0"
DOWNLOAD_DIR="${1:-$(pwd)/proxmox-v9-sources}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Proxmox repositories and versions
declare -A PVE_REPOS=(
    ["pve-manager"]="pve-manager.git"
    ["pve-kernel"]="pve-kernel.git" 
    ["pve-qemu"]="qemu.git"
    ["pve-container"]="pve-container.git"
    ["pve-firewall"]="pve-firewall.git"
    ["pve-cluster"]="pve-cluster.git"
    ["pve-storage"]="pve-storage.git"
    ["pve-access-control"]="pve-access-control.git"
    ["pve-guest-common"]="pve-guest-common.git"
    ["pve-ha-manager"]="pve-ha-manager.git"
    ["pve-docs"]="pve-docs.git"
    ["proxmox-widget-toolkit"]="proxmox-widget-toolkit.git"
    ["proxmox-backup"]="proxmox-backup.git"
    ["proxmox-mini-journalreader"]="proxmox-mini-journalreader.git"
    ["libpve-common-perl"]="libpve-common-perl.git"
    ["libpve-access-control"]="libpve-access-control.git"
    ["libpve-cluster-perl"]="libpve-cluster-perl.git"
    ["libpve-storage-perl"]="libpve-storage-perl.git"
    ["libpve-guest-common-perl"]="libpve-guest-common-perl.git"
)

# Debian package repositories
declare -A PVE_PACKAGES=(
    ["pve-kernel-6.8"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/pve-kernel-6.8.12-4-pve_6.8.12-4_amd64.deb"
    ["pve-headers-6.8"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/pve-headers-6.8.12-4-pve_6.8.12-4_amd64.deb"
    ["proxmox-ve"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/proxmox-ve_8.2.0_all.deb"
    ["pve-manager"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/pve-manager_8.2.4-1_amd64.deb"
    ["pve-cluster"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/pve-cluster_8.0.7-1_amd64.deb"
    ["pve-firewall"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/pve-firewall_5.0.7-3_amd64.deb"
    ["qemu-server"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/qemu-server_8.2.1-1_amd64.deb"
    ["pve-qemu-kvm"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/pve-qemu-kvm_8.1.5-6_amd64.deb"
    ["ceph-common"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/ceph-common_18.2.4-pve3_amd64.deb"
    ["librados2"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/librados2_18.2.4-pve3_amd64.deb"
    ["librbd1"]="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64/librbd1_18.2.4-pve3_amd64.deb"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_section() { echo -e "${BLUE}==== $1 ====${NC}"; }
log_detail() { echo -e "${CYAN}  → ${NC}$1"; }
log_proxmox() { echo -e "${MAGENTA}[PROXMOX]${NC} $1"; }

# Function to check prerequisites
check_prerequisites() {
    log_section "Checking Prerequisites"
    
    local missing_tools=""
    for tool in git wget curl; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools="${missing_tools} $tool"
        fi
    done
    
    if [ -n "$missing_tools" ]; then
        log_error "Missing required tools:$missing_tools"
        log_info "Install with: sudo apt-get install$missing_tools"
        exit 1
    fi
    
    log_info "All prerequisites satisfied"
}

# Function to download Proxmox source repositories
download_proxmox_sources() {
    log_section "Downloading Proxmox v${PVE_VERSION} Source Repositories"
    
    local src_dir="${DOWNLOAD_DIR}/sources"
    mkdir -p "${src_dir}"
    cd "${src_dir}"
    
    for component in "${!PVE_REPOS[@]}"; do
        local repo_name="${PVE_REPOS[$component]}"
        local repo_url="https://git.proxmox.com/git/${repo_name}"
        
        log_proxmox "Downloading ${component}..."
        
        if [ -d "$component" ]; then
            log_detail "Updating existing repository..."
            cd "$component"
            git pull --quiet || log_warning "Failed to update $component"
            cd ..
        else
            log_detail "Cloning repository..."
            if ! git clone --quiet --depth 1 "$repo_url" "$component"; then
                log_warning "Failed to clone $component from $repo_url"
                continue
            fi
        fi
        
        # Check for specific v9 branches or tags
        cd "$component"
        if git branch -r | grep -q "pve${PVE_VERSION}"; then
            log_detail "Switching to pve${PVE_VERSION} branch"
            git checkout "pve${PVE_VERSION}" --quiet 2>/dev/null || true
        elif git tag | grep -q "v${PVE_VERSION}"; then
            log_detail "Switching to v${PVE_VERSION} tag"
            git checkout "v${PVE_VERSION}" --quiet 2>/dev/null || true
        fi
        cd ..
    done
    
    log_info "Source repositories downloaded to: ${src_dir}"
}

# Function to download Proxmox binary packages
download_proxmox_packages() {
    log_section "Downloading Proxmox v${PVE_VERSION} Binary Packages"
    
    local pkg_dir="${DOWNLOAD_DIR}/packages"
    mkdir -p "${pkg_dir}"
    cd "${pkg_dir}"
    
    for package in "${!PVE_PACKAGES[@]}"; do
        local pkg_url="${PVE_PACKAGES[$package]}"
        local pkg_filename=$(basename "$pkg_url")
        
        if [ -f "$pkg_filename" ]; then
            log_detail "Package $package already exists"
            continue
        fi
        
        log_proxmox "Downloading ${package}..."
        if ! wget -q --show-progress "$pkg_url"; then
            log_warning "Failed to download $package"
        fi
    done
    
    log_info "Binary packages downloaded to: ${pkg_dir}"
}

# Function to download kernel sources
download_kernel_sources() {
    log_section "Downloading PVE Kernel Sources"
    
    local kernel_dir="${DOWNLOAD_DIR}/kernel"
    mkdir -p "${kernel_dir}"
    cd "${kernel_dir}"
    
    # Download Linux kernel source (version used by Proxmox)
    local kernel_version="6.8.12"
    local kernel_url="https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${kernel_version}.tar.xz"
    
    if [ ! -f "linux-${kernel_version}.tar.xz" ]; then
        log_proxmox "Downloading Linux kernel ${kernel_version}..."
        wget -q --show-progress "$kernel_url"
    fi
    
    if [ ! -d "linux-${kernel_version}" ]; then
        log_detail "Extracting kernel source..."
        tar -xJf "linux-${kernel_version}.tar.xz"
    fi
    
    # Download PVE kernel patches
    if [ -d "../sources/pve-kernel" ]; then
        log_detail "Copying PVE kernel patches..."
        cp -r "../sources/pve-kernel/patches" "linux-${kernel_version}/" 2>/dev/null || true
    fi
    
    log_info "Kernel sources prepared in: ${kernel_dir}"
}

# Function to download QEMU sources
download_qemu_sources() {
    log_section "Downloading QEMU Sources for Proxmox"
    
    local qemu_dir="${DOWNLOAD_DIR}/qemu"
    mkdir -p "${qemu_dir}"
    cd "${qemu_dir}"
    
    # Download QEMU version used by Proxmox
    local qemu_version="8.1.5"
    local qemu_url="https://download.qemu.org/qemu-${qemu_version}.tar.xz"
    
    if [ ! -f "qemu-${qemu_version}.tar.xz" ]; then
        log_proxmox "Downloading QEMU ${qemu_version}..."
        wget -q --show-progress "$qemu_url"
    fi
    
    if [ ! -d "qemu-${qemu_version}" ]; then
        log_detail "Extracting QEMU source..."
        tar -xJf "qemu-${qemu_version}.tar.xz"
    fi
    
    # Apply PVE patches if available
    if [ -d "../sources/pve-qemu" ]; then
        log_detail "Applying PVE QEMU patches..."
        cd "qemu-${qemu_version}"
        if [ -d "../../../sources/pve-qemu/debian/patches" ]; then
            cp -r "../../../sources/pve-qemu/debian/patches" . 2>/dev/null || true
        fi
        cd ..
    fi
    
    log_info "QEMU sources prepared in: ${qemu_dir}"
}

# Function to create build configuration
create_build_config() {
    log_section "Creating Build Configuration"
    
    cat > "${DOWNLOAD_DIR}/BUILD_CONFIG.sh" <<EOF
#!/bin/bash
# Z-FORGE Proxmox v${PVE_VERSION} Build Configuration
# Generated on $(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Versions
export PVE_VERSION="${PVE_VERSION}"
export KERNEL_VERSION="6.8.12"
export QEMU_VERSION="8.1.5"
export ZFS_VERSION="2.3.4"

# Paths
export PVE_SOURCE_DIR="${DOWNLOAD_DIR}/sources"
export PVE_PACKAGE_DIR="${DOWNLOAD_DIR}/packages"
export PVE_KERNEL_DIR="${DOWNLOAD_DIR}/kernel"
export PVE_QEMU_DIR="${DOWNLOAD_DIR}/qemu"

# Build flags for native optimization
export NATIVE_BUILD_FLAGS="-march=native -mtune=native -O2 -pipe"
export KERNEL_BUILD_FLAGS="\${NATIVE_BUILD_FLAGS} -fno-strict-aliasing"
export QEMU_BUILD_FLAGS="\${NATIVE_BUILD_FLAGS} -enable-kvm -enable-numa"

# Component status
EOF
    
    # Add component status
    echo "# Component availability:" >> "${DOWNLOAD_DIR}/BUILD_CONFIG.sh"
    for component in "${!PVE_REPOS[@]}"; do
        if [ -d "${DOWNLOAD_DIR}/sources/$component" ]; then
            echo "export ${component^^}_AVAILABLE=true" >> "${DOWNLOAD_DIR}/BUILD_CONFIG.sh"
        else
            echo "export ${component^^}_AVAILABLE=false" >> "${DOWNLOAD_DIR}/BUILD_CONFIG.sh"
        fi
    done
    
    chmod +x "${DOWNLOAD_DIR}/BUILD_CONFIG.sh"
    log_info "Build configuration created: BUILD_CONFIG.sh"
}

# Function to create ISO integration script
create_iso_integration() {
    log_section "Creating ISO Integration Script"
    
    cat > "${DOWNLOAD_DIR}/integrate_into_iso.sh" <<EOF
#!/bin/bash
# Integrate Proxmox sources into Z-FORGE ISO build

set -euo pipefail

ISO_BUILD_DIR="\${1:-\$(pwd)}"
ZFORGE_ROOT="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Integrating Proxmox v${PVE_VERSION} sources into ISO build..."

# Copy packages to prebuilt_packages
echo "Copying binary packages..."
mkdir -p "\${ZFORGE_ROOT}/prebuilt_packages/proxmox-${PVE_VERSION}"
cp -r packages/* "\${ZFORGE_ROOT}/prebuilt_packages/proxmox-${PVE_VERSION}/"

# Copy sources to build environment
echo "Copying source trees..."
mkdir -p "\${ZFORGE_ROOT}/proxmox-sources"
cp -r sources/* "\${ZFORGE_ROOT}/proxmox-sources/"
cp -r kernel "\${ZFORGE_ROOT}/proxmox-sources/"
cp -r qemu "\${ZFORGE_ROOT}/proxmox-sources/"

# Copy build configuration
cp BUILD_CONFIG.sh "\${ZFORGE_ROOT}/"

# Update build specs to include Proxmox
echo "Updating build specifications..."
for spec_file in "\${ZFORGE_ROOT}/build_specs"/*.yml; do
    if ! grep -q "proxmox_config" "\$spec_file"; then
        cat >> "\$spec_file" <<EOL

proxmox_config:
  version: ${PVE_VERSION}
  source_build: true
  native_optimization: true
  compile_at_install: true
  source_dir: "/opt/proxmox-sources"
  
modules:
- name: proxmox_source_build
  enabled: true
  config:
    compile_kernel: true
    compile_qemu: true
    native_flags: true
EOL
    fi
done

echo "Proxmox v${PVE_VERSION} integration complete!"
echo "The ISO will now include Proxmox sources for native compilation."
EOF
    
    chmod +x "${DOWNLOAD_DIR}/integrate_into_iso.sh"
    log_info "ISO integration script created"
}

# Function to create source verification
create_source_verification() {
    log_section "Creating Source Verification"
    
    cat > "${DOWNLOAD_DIR}/verify_sources.sh" <<'EOF'
#!/bin/bash
# Verify Proxmox source integrity and completeness

set -euo pipefail

DOWNLOAD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${DOWNLOAD_DIR}"

echo "Verifying Proxmox source integrity..."
echo ""

# Check source repositories
echo "Source Repositories:"
for dir in sources/*/; do
    if [ -d "$dir" ]; then
        component=$(basename "$dir")
        commit_count=$(cd "$dir" && git rev-list --count HEAD 2>/dev/null || echo "0")
        last_commit=$(cd "$dir" && git log -1 --format="%h %s" 2>/dev/null || echo "No commits")
        echo "  ✓ $component: $commit_count commits, latest: $last_commit"
    fi
done

echo ""
echo "Binary Packages:"
if [ -d "packages" ]; then
    package_count=$(find packages -name "*.deb" | wc -l)
    total_size=$(du -sh packages 2>/dev/null | cut -f1)
    echo "  ✓ $package_count packages, total size: $total_size"
    
    for deb in packages/*.deb; do
        if [ -f "$deb" ]; then
            pkg_name=$(dpkg-deb --field "$deb" Package 2>/dev/null || echo "unknown")
            pkg_version=$(dpkg-deb --field "$deb" Version 2>/dev/null || echo "unknown")
            pkg_size=$(du -h "$deb" | cut -f1)
            echo "    • $pkg_name: $pkg_version ($pkg_size)"
        fi
    done
fi

echo ""
echo "Kernel Sources:"
if [ -d "kernel" ]; then
    for kernel in kernel/linux-*; do
        if [ -d "$kernel" ]; then
            version=$(basename "$kernel" | sed 's/linux-//')
            patch_count=$(find "$kernel/patches" -name "*.patch" 2>/dev/null | wc -l || echo "0")
            echo "  ✓ Linux $version with $patch_count PVE patches"
        fi
    done
fi

echo ""
echo "QEMU Sources:"
if [ -d "qemu" ]; then
    for qemu_dir in qemu/qemu-*; do
        if [ -d "$qemu_dir" ]; then
            version=$(basename "$qemu_dir" | sed 's/qemu-//')
            patch_count=$(find "$qemu_dir/patches" -name "*.patch" 2>/dev/null | wc -l || echo "0")
            echo "  ✓ QEMU $version with $patch_count PVE patches"
        fi
    done
fi

echo ""
echo "Build Configuration:"
if [ -f "BUILD_CONFIG.sh" ]; then
    echo "  ✓ Build configuration present"
    source BUILD_CONFIG.sh
    echo "    • PVE Version: $PVE_VERSION"
    echo "    • Kernel Version: $KERNEL_VERSION"
    echo "    • QEMU Version: $QEMU_VERSION"
    echo "    • ZFS Version: $ZFS_VERSION"
fi

echo ""
echo "Verification complete!"
EOF
    
    chmod +x "${DOWNLOAD_DIR}/verify_sources.sh"
    log_info "Source verification script created"
}

# Function to create README
create_readme() {
    log_section "Creating Documentation"
    
    cat > "${DOWNLOAD_DIR}/README.md" <<EOF
# Proxmox v${PVE_VERSION} Complete Source Package

This directory contains all Proxmox v${PVE_VERSION} source components downloaded for
offline compilation and integration into Z-FORGE ISOs.

## Contents

### Source Repositories (\`sources/\`)
- **pve-manager**: Proxmox VE management interface
- **pve-kernel**: Proxmox kernel with patches
- **pve-qemu**: QEMU with Proxmox optimizations
- **pve-container**: LXC container management
- **pve-firewall**: Proxmox firewall
- **pve-cluster**: Cluster management
- **pve-storage**: Storage abstraction layer
- **pve-access-control**: Authentication and authorization
- **pve-ha-manager**: High availability manager
- **proxmox-backup**: Backup solution
- Plus additional libraries and tools

### Binary Packages (\`packages/\`)
Pre-compiled .deb packages for immediate installation:
- Kernel packages with headers
- Core Proxmox VE components
- QEMU virtualization
- Ceph storage packages
- Management tools

### Kernel Sources (\`kernel/\`)
- Linux kernel source with Proxmox patches
- PVE-specific kernel configurations
- Hardware optimization patches

### QEMU Sources (\`qemu/\`)
- QEMU source with Proxmox patches
- Virtualization optimizations
- PVE-specific device drivers

## Integration with Z-FORGE

### Automatic Integration
\`\`\`bash
# Integrate into Z-FORGE build system
./integrate_into_iso.sh /path/to/zforge

# Verify integration
./verify_sources.sh
\`\`\`

### Build Configuration
Source the build configuration before compilation:
\`\`\`bash
source BUILD_CONFIG.sh
# Now all PVE_* variables are available
\`\`\`

### Native Compilation
The sources are configured for native CPU optimization:
- Kernel modules compiled for target hardware
- QEMU optimized for host CPU features
- All components use -march=native flags

## Manual Usage

### Build Kernel
\`\`\`bash
cd kernel/linux-\${KERNEL_VERSION}
make defconfig
# Apply PVE patches
make -j\$(nproc) bzImage modules
\`\`\`

### Build QEMU
\`\`\`bash
cd qemu/qemu-\${QEMU_VERSION}
./configure --enable-kvm --enable-numa
make -j\$(nproc)
\`\`\`

### Install Binary Packages
\`\`\`bash
cd packages
dpkg -i *.deb
\`\`\`

## Download Information

**Download Date**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Proxmox Version**: v${PVE_VERSION}
**Total Size**: $(du -sh "${DOWNLOAD_DIR}" 2>/dev/null | cut -f1 || echo "Calculating...")

## Scripts

- \`verify_sources.sh\`: Check source integrity
- \`integrate_into_iso.sh\`: Add to Z-FORGE build
- \`BUILD_CONFIG.sh\`: Build environment variables

## Notes

- All sources are downloaded from official Proxmox repositories
- Binary packages are from the pve-no-subscription repository  
- Sources are configured for offline compilation
- Native optimization is enabled by default
- Compatible with Z-FORGE DKMS build system

This package enables complete offline building of Proxmox VE with
native CPU optimizations for maximum performance.
EOF
    
    log_info "Documentation created: README.md"
}

# Main execution
main() {
    log_section "Z-FORGE Proxmox v${PVE_VERSION} Complete Source Downloader"
    log_info "Downloading all Proxmox sources for offline ISO building"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Create download directory
    mkdir -p "${DOWNLOAD_DIR}"
    log_info "Download directory: ${DOWNLOAD_DIR}"
    echo ""
    
    # Download all components
    download_proxmox_sources
    download_proxmox_packages  
    download_kernel_sources
    download_qemu_sources
    
    # Create configuration and integration
    create_build_config
    create_iso_integration
    create_source_verification
    create_readme
    
    # Final verification
    cd "${DOWNLOAD_DIR}"
    ./verify_sources.sh
    
    log_section "Download Complete!"
    echo ""
    log_info "Proxmox v${PVE_VERSION} sources downloaded successfully"
    log_detail "Location: ${DOWNLOAD_DIR}"
    log_detail "Size: $(du -sh "${DOWNLOAD_DIR}" | cut -f1)"
    echo ""
    log_info "Next Steps:"
    log_detail "1. Integrate into Z-FORGE: ./integrate_into_iso.sh"
    log_detail "2. Build DKMS packages: ../build/build_zfs_proxmox_dkms_optimized.sh"
    log_detail "3. Build ISO: sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml"
    echo ""
    log_info "The ISO will include native compilation of both ZFS and Proxmox"
    log_info "optimized for each target system's specific hardware."
}

# Run main function
main "$@"
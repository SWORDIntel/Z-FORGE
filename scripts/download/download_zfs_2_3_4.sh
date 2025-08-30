#!/bin/bash
# Z-FORGE ZFS 2.3.4 Download Script
# Downloads and prepares ZFS 2.3.4 source for building
# Note: This downloads ZFS for building into Debian-based Z-FORGE ISOs
#       The host system (Ubuntu) kernel is different from target (Debian)

set -euo pipefail

# Configuration
ZFS_VERSION="2.3.4"
ZFS_URL="https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
DOWNLOAD_DIR="${1:-$(pwd)/zfs-builds}"  # Default to current directory/zfs-builds
ZFS_SOURCE_DIR="${DOWNLOAD_DIR}/zfs-${ZFS_VERSION}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Main script
main() {
    log_info "Z-FORGE ZFS ${ZFS_VERSION} Download Script"
    log_info "========================================="
    
    # Create download directory
    log_info "Creating download directory: ${DOWNLOAD_DIR}"
    mkdir -p "${DOWNLOAD_DIR}"
    cd "${DOWNLOAD_DIR}"
    
    # Check if already downloaded
    if [[ -f "zfs-${ZFS_VERSION}.tar.gz" ]]; then
        log_warning "ZFS ${ZFS_VERSION} tarball already exists. Checking integrity..."
        if tar -tzf "zfs-${ZFS_VERSION}.tar.gz" >/dev/null 2>&1; then
            log_info "Existing tarball is valid"
        else
            log_warning "Existing tarball is corrupted. Re-downloading..."
            rm -f "zfs-${ZFS_VERSION}.tar.gz"
        fi
    fi
    
    # Download ZFS source if needed
    if [[ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]]; then
        log_info "Downloading ZFS ${ZFS_VERSION} from GitHub..."
        if command -v wget >/dev/null 2>&1; then
            wget -O "zfs-${ZFS_VERSION}.tar.gz" "${ZFS_URL}" || {
                log_error "Failed to download ZFS ${ZFS_VERSION}"
                exit 1
            }
        elif command -v curl >/dev/null 2>&1; then
            curl -L -o "zfs-${ZFS_VERSION}.tar.gz" "${ZFS_URL}" || {
                log_error "Failed to download ZFS ${ZFS_VERSION}"
                exit 1
            }
        else
            log_error "Neither wget nor curl is available. Please install one of them."
            exit 1
        fi
        log_info "Download complete!"
    fi
    
    # Extract source
    if [[ -d "${ZFS_SOURCE_DIR}" ]]; then
        log_warning "ZFS ${ZFS_VERSION} source directory already exists. Removing..."
        rm -rf "${ZFS_SOURCE_DIR}"
    fi
    
    log_info "Extracting ZFS ${ZFS_VERSION} source..."
    tar -xzf "zfs-${ZFS_VERSION}.tar.gz" || {
        log_error "Failed to extract ZFS ${ZFS_VERSION}"
        exit 1
    }
    
    # Verify extraction
    if [[ ! -d "${ZFS_SOURCE_DIR}" ]]; then
        log_error "Source directory not found after extraction"
        exit 1
    fi
    
    # Check for configure script
    if [[ ! -f "${ZFS_SOURCE_DIR}/configure" ]]; then
        log_info "Configure script not found. Running autogen.sh..."
        cd "${ZFS_SOURCE_DIR}"
        if [[ -f "autogen.sh" ]]; then
            ./autogen.sh || {
                log_error "Failed to run autogen.sh"
                exit 1
            }
        else
            log_error "No autogen.sh or configure script found"
            exit 1
        fi
        cd "${DOWNLOAD_DIR}"
    fi
    
    # Create version info file
    cat > "${DOWNLOAD_DIR}/zfs-${ZFS_VERSION}.info" <<EOF
ZFS_VERSION=${ZFS_VERSION}
DOWNLOAD_DATE=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
SOURCE_URL=${ZFS_URL}
SOURCE_DIR=${ZFS_SOURCE_DIR}
TARBALL=${DOWNLOAD_DIR}/zfs-${ZFS_VERSION}.tar.gz
EOF
    
    log_info "ZFS ${ZFS_VERSION} source prepared successfully!"
    log_info "Source location: ${ZFS_SOURCE_DIR}"
    log_info ""
    log_warning "IMPORTANT: This ZFS build is for Debian-based Z-FORGE target systems"
    log_warning "Host system is Ubuntu, target system uses Debian kernel (6.14.0-15-generic)"
    log_info ""
    log_info "Next steps for building ZFS packages:"
    log_info "1. Configure ZFS build: cd ${ZFS_SOURCE_DIR} && ./configure --with-linux=/path/to/debian/kernel/headers"
    log_info "2. Build ZFS: make -j$(nproc)"
    log_info "3. Create Debian packages: make deb-utils deb-kmod"
    log_info ""
    log_info "For Z-FORGE integration (builds for Debian target):"
    log_info "  sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml"
    log_info ""
    log_info "Note: The packages built will be for the Debian kernel in the Z-FORGE ISO,"
    log_info "      not for the current Ubuntu host system."
}

# Run main function
main "$@"
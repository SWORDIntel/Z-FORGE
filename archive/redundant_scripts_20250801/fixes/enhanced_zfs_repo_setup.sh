#!/bin/bash
# Enhanced ZFS Repository Setup for Z-FORGE
# Handles Debian Trixie ZFS package installation with multiple fallbacks

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"
ZFS_VERSION="${2:-2.3.3}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

setup_zfs_repositories() {
    log "Setting up ZFS repositories for Debian Trixie..."
    
    # Method 1: Enable contrib in existing sources
    if [ -f "$CHROOT_PATH/etc/apt/sources.list" ]; then
        log "Enabling contrib and non-free-firmware in existing sources..."
        chroot "$CHROOT_PATH" /bin/bash -c '
            sed -i "s/main$/main contrib non-free-firmware/g" /etc/apt/sources.list
            apt-get update
        '
    fi
    
    # Method 2: Add Bookworm backports as fallback
    log "Adding Bookworm repositories as fallback..."
    cat > "$CHROOT_PATH/etc/apt/sources.list.d/zfs-fallback.list" << EOF
# Fallback repositories for ZFS packages
deb http://deb.debian.org/debian bookworm main contrib non-free-firmware
deb http://deb.debian.org/debian bookworm-backports main contrib non-free-firmware
EOF

    # Set up apt preferences
    cat > "$CHROOT_PATH/etc/apt/preferences.d/zfs-packages" << EOF
# Prefer ZFS packages from bookworm when not available in trixie
Package: zfsutils-linux zfs-dkms zfs-zed libzfs4* libzpool5* libnvpair3* libuutil3*
Pin: release n=bookworm-backports
Pin-Priority: 990

Package: zfsutils-linux zfs-dkms zfs-zed libzfs4* libzpool5* libnvpair3* libuutil3*
Pin: release n=bookworm
Pin-Priority: 980

# Prevent other packages from bookworm
Package: *
Pin: release n=bookworm*
Pin-Priority: 100
EOF
}

install_zfs_packages() {
    log "Installing ZFS packages with fallback strategy..."
    
    chroot "$CHROOT_PATH" /bin/bash -c 'apt-get update'
    
    # Try multiple installation strategies
    local packages=("zfsutils-linux" "zfs-dkms")
    local strategies=(
        "apt-get install -y --no-install-recommends"
        "apt-get install -y --no-install-recommends -t trixie"
        "apt-get install -y --no-install-recommends -t bookworm-backports"
        "apt-get install -y --no-install-recommends -t bookworm"
        "apt-get install -y --fix-missing --no-install-recommends"
    )
    
    for strategy in "${strategies[@]}"; do
        log "Trying: $strategy ${packages[*]}"
        if chroot "$CHROOT_PATH" /bin/bash -c "$strategy ${packages[*]}"; then
            log "✅ ZFS packages installed successfully with: $strategy"
            return 0
        else
            log "❌ Failed with: $strategy"
        fi
    done
    
    # Fallback: Install only userspace tools
    log "Final fallback: Installing only ZFS userspace tools..."
    if chroot "$CHROOT_PATH" /bin/bash -c "apt-get install -y --no-install-recommends zfsutils-linux"; then
        log "⚠️  ZFS userspace tools installed (DKMS modules may be missing)"
        return 0
    fi
    
    log "🚨 All ZFS installation strategies failed"
    return 1
}

download_github_release() {
    log "Downloading ZFS $ZFS_VERSION from GitHub releases..."
    
    local release_url="https://github.com/openzfs/zfs/releases/download/zfs-$ZFS_VERSION"
    local temp_dir="/tmp/zfs_github_install"
    
    mkdir -p "$temp_dir"
    cd "$temp_dir"
    
    # Download pre-built Debian packages if available
    if wget -q "$release_url/zfsutils-linux_${ZFS_VERSION}_amd64.deb" 2>/dev/null; then
        log "Found pre-built ZFS packages, installing..."
        chroot "$CHROOT_PATH" /bin/bash -c "dpkg -i /tmp/zfs_github_install/*.deb || apt-get install -f -y"
        return 0
    fi
    
    # Download source tarball for manual build
    if wget -q "$release_url/zfs-$ZFS_VERSION.tar.gz"; then
        log "Downloaded ZFS source, will need to build from source..."
        # This would need additional build logic
        return 1
    fi
    
    log "Could not download ZFS from GitHub releases"
    return 1
}

main() {
    log "Starting enhanced ZFS setup for version $ZFS_VERSION"
    
    setup_zfs_repositories
    
    if install_zfs_packages; then
        log "✅ ZFS installation completed successfully"
        exit 0
    fi
    
    log "Repository installation failed, trying GitHub releases..."
    if download_github_release; then
        log "✅ ZFS installation from GitHub completed"
        exit 0
    fi
    
    log "🚨 All ZFS installation methods failed"
    exit 1
}

main "$@"
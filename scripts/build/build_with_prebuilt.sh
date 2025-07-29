#!/bin/bash
# Build Z-FORGE ISO using pre-built ZFS packages

set -e

SUDO_PASS="1786"

# Cleanup trap
trap 'rm -f "$CONFIG_FILE" 2>/dev/null || true' EXIT

echo "════════════════════════════════════════════════════════════════════"
echo "    Z-FORGE Build with Pre-built ZFS Packages"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Check for pre-built packages
PREBUILT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
if [ -f "$PREBUILT_DIR/zfs-userspace-2.3.3.tar.gz" ]; then
    echo "✅ Found ZFS userspace package: zfs-userspace-2.3.3.tar.gz"
elif [ -n "$(ls -A $PREBUILT_DIR/*.deb 2>/dev/null)" ]; then
    echo "✅ Found ZFS .deb packages"
else
    echo "❌ No pre-built packages found!"
    echo "   Please run one of the following:"
    echo "   - ./build_zfs_userspace_only.sh"
    echo "   - ./download_zfs_debs.sh"
    exit 1
fi

# Create config to use pre-built packages
CONFIG_FILE="$(mktemp /tmp/zforge_prebuilt_config_XXXXXX.yaml)"
cat > "$CONFIG_FILE" << 'EOF'
# Z-FORGE configuration with pre-built ZFS packages
hostname: zforge-build
timezone: UTC
locale: en_US.UTF-8

packages:
  base:
    - vim
    - htop
    - tree
    - curl
    - wget
    - net-tools
    - openssh-server
    
  firmware:
    - firmware-linux
    - firmware-linux-nonfree
    - firmware-misc-nonfree

zfs_config:
  build_from_source: false  # Use pre-built packages
  default_compression: lz4
  arc_max_percent: 50

services:
  enable:
    - ssh
    - zfs-import-cache
    - zfs-mount
    - zfs-share
    - zfs-zed
  disable:
    - bluetooth
    
network:
  primary_interface: auto
  dhcp: true
EOF

echo ""
echo "📋 Configuration:"
echo "   - Using pre-built ZFS packages"
echo "   - Config: $CONFIG_FILE"
echo ""
echo "Starting build..."

# Run the build
cd /opt/github/Z-FORGE
echo "$SUDO_PASS" | sudo -S ./build.sh --build-spec "$CONFIG_FILE"

echo ""
echo "✅ Build complete!"
echo "📀 ISO location: /opt/github/Z-FORGE/output/*.iso"
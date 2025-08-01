#!/bin/bash
# Prepare ZFS 2.3.3 for Z-FORGE Makefile Build System
# This script checks if ZFS 2.3.3 packages are available and builds them if needed

set -e

PREBUILT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
ZFS_VERSION="2.3.3"
ZFS_PACKAGE="${PREBUILT_DIR}/zfs-${ZFS_VERSION}-complete.tar.gz"
ZFS_INSTALLER="${PREBUILT_DIR}/install_zfs_2_3_3.sh"

echo "══════════════════════════════════════════════════════════════════"
echo "              Preparing ZFS 2.3.3 for Z-FORGE Build"
echo "══════════════════════════════════════════════════════════════════"

# Check if packages already exist
if [ -f "$ZFS_PACKAGE" ] && [ -f "$ZFS_INSTALLER" ]; then
    echo "✅ ZFS 2.3.3 packages already available:"
    echo "   📦 $(basename "$ZFS_PACKAGE") ($(du -h "$ZFS_PACKAGE" | cut -f1))"
    echo "   🔧 $(basename "$ZFS_INSTALLER")"
    echo ""
    echo "Ready for Makefile build! Run: make build"
    exit 0
fi

echo "⚠️  ZFS 2.3.3 packages not found. Building them now..."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: Building ZFS requires root privileges"
    echo ""
    echo "Please run: sudo $0"
    exit 1
fi

# Run the smart ZFS build script (handles CONFIG_MODULES automatically)
echo "🔨 Starting smart ZFS 2.3.3 build process..."
echo "   (Will detect kernel capabilities and build appropriately)"
./build_zfs_233_smart.sh

echo ""
echo "✅ ZFS 2.3.3 preparation complete!"
echo ""
echo "Next steps:"
echo "  1. Check build environment: make check"
echo "  2. Install dependencies: make deps"  
echo "  3. Run the build: make build"
echo ""
echo "The build system will automatically use ZFS 2.3.3 packages."
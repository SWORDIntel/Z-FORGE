#!/bin/bash
# Simple build runner with sudo password

SUDO_PASS="1786"

echo "════════════════════════════════════════════════════════════════════"
echo "    Z-FORGE Build (Using existing build_spec.yml)"  
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Check for pre-built packages
PREBUILT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
if [ -f "$PREBUILT_DIR/zfs-userspace-2.3.3.tar.gz" ]; then
    echo "✅ Found ZFS userspace package: zfs-userspace-2.3.3.tar.gz"
elif [ -n "$(ls -A $PREBUILT_DIR/*.deb 2>/dev/null)" ]; then
    echo "✅ Found ZFS .deb packages"
else
    echo "⚠️  No pre-built packages found, build will try to download"
fi

echo ""
echo "📋 Using configuration: build_spec.yml"
echo "   - ZFS build_from_source: false"
echo "   - ZFS version: 2.3.3"
echo ""

cd /opt/github/Z-FORGE
echo "$SUDO_PASS" | sudo -S ./build.sh

echo ""
echo "✅ Build complete!"
echo "📀 ISO location: /opt/github/Z-FORGE/output/*.iso"
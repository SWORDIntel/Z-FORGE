#!/bin/bash
# Z-FORGE ZFS Pre-builder Wrapper

echo "🔨 Z-FORGE ZFS Pre-builder"
echo "=========================="
echo "Building ZFS 2.3.3 from source for faster installation"
echo ""

# Check if already built
if [ -d "/opt/github/Z-FORGE/prebuilt_packages" ] && [ -f "/opt/github/Z-FORGE/prebuilt_packages/install_zfs_prebuilt.sh" ]; then
    echo "✅ Pre-built ZFS packages already exist"
    echo "   Location: /opt/github/Z-FORGE/prebuilt_packages"
    echo ""
    echo "To rebuild, delete the directory and run this script again:"
    echo "   sudo rm -rf /opt/github/Z-FORGE/prebuilt_packages"
    echo "   sudo ./prebuild_zfs.sh"
    exit 0
fi

# Check for root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (for package installation)"
   echo "   Please run: sudo ./prebuild_zfs.sh"
   exit 1
fi

echo "This will:"
echo "1. Download ZFS 2.3.3 source code"
echo "2. Install build dependencies" 
echo "3. Build ZFS .deb packages"
echo "4. Create installation script for Z-FORGE"
echo "5. Integrate with Z-FORGE build system"
echo ""

read -p "Continue? [Y/n] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Run the pre-builder
python3 ultrathink_zfs_prebuilder.py

echo ""
echo "✅ ZFS pre-build complete!"
echo "   Z-FORGE will now use these pre-built packages for faster installation"
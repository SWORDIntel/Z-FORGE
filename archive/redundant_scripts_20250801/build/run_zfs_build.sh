#!/bin/bash
# Simple wrapper to run ZFS build with proper instructions

echo "═══════════════════════════════════════════════════════════════════"
echo "                   ZFS Build Options"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "You have several ZFS build scripts available:"
echo ""
echo "1. Smart Build (recommended):"
echo "   sudo ./scripts/build/build_zfs_233_smart.sh"
echo "   - Auto-detects kernel capabilities"
echo "   - Builds with or without kernel modules"
echo ""
echo "2. Userspace Only:"
echo "   sudo ./scripts/build/build_zfs_233_userspace_only.sh"
echo "   - Builds ZFS tools without kernel modules"
echo "   - Safe for any kernel"
echo ""
echo "3. Chroot Build:"
echo "   sudo ./scripts/build/build_zfs_233_chroot_modules.sh"
echo "   - Builds inside chroot environment"
echo "   - For ISO development"
echo ""

# Check current system
echo "Current system info:"
echo "  Kernel: $(uname -r)"
echo "  Headers: $(ls /lib/modules/$(uname -r)/build 2>/dev/null && echo "Available" || echo "Not available")"

if grep -q "CONFIG_MODULES=y" /boot/config-$(uname -r) 2>/dev/null; then
    echo "  Modules: Supported ✅"
    echo ""
    echo "Recommended: Run the smart build script"
    echo "  sudo ./scripts/build/build_zfs_233_smart.sh"
else
    echo "  Modules: Not supported ❌"
    echo ""
    echo "Recommended: Run userspace-only build"
    echo "  sudo ./scripts/build/build_zfs_233_userspace_only.sh"
fi

echo ""
echo "Which script would you like to run?"
echo "Enter the number [1-3] or 'q' to quit:"
read -p "> " choice

case "$choice" in
    1)
        echo ""
        echo "Running smart build script..."
        echo "Command: sudo ./scripts/build/build_zfs_233_smart.sh"
        echo ""
        echo "You'll need to run this manually with sudo access."
        ;;
    2)
        echo ""
        echo "Running userspace-only build..."
        echo "Command: sudo ./scripts/build/build_zfs_233_userspace_only.sh"
        echo ""
        echo "You'll need to run this manually with sudo access."
        ;;
    3)
        echo ""
        echo "Running chroot build..."
        echo "Command: sudo ./scripts/build/build_zfs_233_chroot_modules.sh"
        echo ""
        echo "You'll need to run this manually with sudo access."
        ;;
    q|Q)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac
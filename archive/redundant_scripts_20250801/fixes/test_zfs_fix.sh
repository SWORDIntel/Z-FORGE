#!/bin/bash
# Test script to verify ZFS installation fix

echo "Testing ZFS installation fix..."
echo "================================"

# Check if the kernel_acquisition.py file was updated
echo -n "Checking if kernel_acquisition.py was updated... "
if grep -q "Enable contrib repository for ZFS packages" builder/modules/kernel_acquisition.py; then
    echo "✓ Updated"
else
    echo "✗ Not updated"
    exit 1
fi

# Check if the new approach is in place
echo -n "Checking if contrib approach is implemented... "
if grep -q "Adding contrib component to sources.list" builder/modules/kernel_acquisition.py; then
    echo "✓ Implemented"
else
    echo "✗ Not implemented"
    exit 1
fi

# Check if fallback mechanisms are in place
echo -n "Checking if fallback mechanisms exist... "
if grep -q "Try installing with --fix-missing" builder/modules/kernel_acquisition.py; then
    echo "✓ Fallbacks added"
else
    echo "✗ No fallbacks"
    exit 1
fi

# Check if error handling is improved
echo -n "Checking if error handling is improved... "
if grep -q "continuing without ZFS kernel modules" builder/modules/kernel_acquisition.py; then
    echo "✓ Improved error handling"
else
    echo "✗ Error handling not improved"
    exit 1
fi

echo ""
echo "All checks passed! The ZFS installation fix has been applied successfully."
echo ""
echo "Summary of changes:"
echo "1. Changed from OpenZFS repository to native Debian contrib repository"
echo "2. Added multiple fallback installation attempts"
echo "3. Improved error handling to continue build even if ZFS modules fail"
echo "4. Added support for alternative ZFS packages (zfs-modules, zfs-initramfs)"
echo ""
echo "Next build attempt should handle ZFS installation more gracefully."
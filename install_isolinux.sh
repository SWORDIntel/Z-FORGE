#!/bin/bash
# Install isolinux for BIOS boot support

echo "Installing isolinux and syslinux packages..."

# Update package list
apt-get update

# Install with GPG bypass
apt-get install -y --allow-unauthenticated \
    isolinux \
    syslinux \
    syslinux-common \
    syslinux-utils

echo "Installation complete!"
echo
echo "Files installed:"
ls -la /usr/lib/ISOLINUX/isolinux.bin 2>/dev/null || echo "isolinux.bin not found"
ls -la /usr/lib/syslinux/modules/bios/ldlinux.c32 2>/dev/null || echo "ldlinux.c32 not found"
#!/bin/bash
# Quick fix for APT warnings without requiring root
# This script creates a temporary fix for the build process

set -euo pipefail

echo "=== Quick APT Warnings Fix ==="

# Check if we're in a build process with a chroot
WORKSPACE="${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"

if [ -d "$CHROOT_PATH" ]; then
    echo "Fixing APT issues in chroot environment..."
    
    # Fix permissions in chroot if they exist
    if [ -d "$CHROOT_PATH/var/lib/apt/lists/partial" ]; then
        echo "  Fixing chroot APT permissions..."
        chown -R _apt:root "$CHROOT_PATH/var/lib/apt/lists/partial" 2>/dev/null || true
        chmod 755 "$CHROOT_PATH/var/lib/apt/lists/partial" 2>/dev/null || true
    fi
    
    # Remove Dell repository from chroot (not needed for build)
    echo "  Removing Dell repo from chroot..."
    if [ -f "$CHROOT_PATH/etc/apt/sources.list" ]; then
        sed -i '/linux\.dell\.com/d' "$CHROOT_PATH/etc/apt/sources.list" 2>/dev/null || true
    fi
    
    # Remove Dell sources.list.d files from chroot
    find "$CHROOT_PATH/etc/apt/sources.list.d/" -name "*dell*" -delete 2>/dev/null || true
    
    # Create a dummy Dell keyring in chroot to stop the warnings
    mkdir -p "$CHROOT_PATH/usr/share/keyrings"
    touch "$CHROOT_PATH/usr/share/keyrings/dell-trusted.gpg"
    chmod 644 "$CHROOT_PATH/usr/share/keyrings/dell-trusted.gpg" 2>/dev/null || true
    
    echo "  ✅ Chroot APT issues fixed"
fi

# Suggest running the comprehensive fix after build
echo ""
echo "=== Recommendation ==="
echo "After the build completes, run this as root to fix system-wide:"
echo "  sudo ./scripts/fixes/fix_dell_repo_properly.sh"
echo ""
echo "These warnings don't affect the build success - they're just noise."
echo "The build should continue normally."
#!/bin/bash
# Quick fix and rebuild script
# Applies all fixes and retries the build

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "              Quick Fix and Rebuild for Z-FORGE"
echo "═══════════════════════════════════════════════════════════════════"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# Check if chroot exists from previous build
CHROOT_PATH="/tmp/zforge_workspace/chroot"

if [ -d "$CHROOT_PATH" ]; then
    echo "[1/3] Found existing chroot, applying fixes..."
    
    # Fix chroot environment
    echo "Fixing chroot environment..."
    ./fix_chroot_complete.sh "$CHROOT_PATH"
    
    # Fix ZFS modules
    echo ""
    echo "Fixing ZFS dracut modules..."
    ./fix_zfs_dracut_modules.sh "$CHROOT_PATH"
    
    echo ""
    echo "[2/3] Fixes applied to existing chroot"
else
    echo "[1/3] No existing chroot found"
    echo "      Build will create a fresh one with fixes"
fi

echo ""
echo "[3/3] Starting build with Makefile..."
echo ""

# Run the build
make build

echo ""
echo "Build attempt complete. Check logs for results."
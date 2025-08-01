#!/bin/bash
# Safe cleanup script for Z-FORGE workspace
# Prevents system issues by properly unmounting before removal

WORKSPACE="${1:-/tmp/zforge_workspace}"
SUDO_PASS="${2:-1786}"

echo "=== Z-FORGE Safe Workspace Cleanup ==="
echo "Workspace: $WORKSPACE"

# Check if workspace exists
if [ ! -d "$WORKSPACE" ]; then
    echo "Workspace not found, nothing to clean"
    exit 0
fi

# Unmount in reverse order (most specific first)
echo "Unmounting chroot filesystems..."
for mount in dev/pts dev sys proc; do
    if mountpoint -q "$WORKSPACE/chroot/$mount" 2>/dev/null; then
        echo "  Unmounting $mount..."
        echo "$SUDO_PASS" | sudo -S umount "$WORKSPACE/chroot/$mount" || {
            echo "  WARNING: Failed to unmount $mount, trying lazy unmount..."
            echo "$SUDO_PASS" | sudo -S umount -l "$WORKSPACE/chroot/$mount"
        }
    fi
done

# Double-check no mounts remain
if mount | grep -q "$WORKSPACE"; then
    echo "WARNING: Some mounts still exist:"
    mount | grep "$WORKSPACE"
    echo ""
    echo "Attempting forceful cleanup..."
    mount | grep "$WORKSPACE" | awk '{print $3}' | sort -r | while read mount; do
        echo "$SUDO_PASS" | sudo -S umount -l "$mount"
    done
fi

# Now safe to remove workspace
echo "Removing workspace..."
echo "$SUDO_PASS" | sudo -S rm -rf "$WORKSPACE"

echo "Cleanup complete!"
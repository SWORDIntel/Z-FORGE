#!/bin/bash
# Script to safely unmount chroot environments

echo "Unmounting chroot filesystems..."

# Function to unmount a chroot
unmount_chroot() {
    local CHROOT_PATH="$1"
    echo "Processing: $CHROOT_PATH"
    
    # Unmount in reverse order
    for mount_point in dev/pts dev/shm dev sys proc; do
        if mountpoint -q "$CHROOT_PATH/$mount_point" 2>/dev/null; then
            echo "  Unmounting: $CHROOT_PATH/$mount_point"
            sudo umount -l "$CHROOT_PATH/$mount_point" 2>/dev/null || true
        fi
    done
    
    # Also try to unmount dev if it's still mounted
    if mountpoint -q "$CHROOT_PATH/dev" 2>/dev/null; then
        echo "  Unmounting: $CHROOT_PATH/dev"
        sudo umount -l "$CHROOT_PATH/dev" 2>/dev/null || true
    fi
}

# Unmount both chroot environments
unmount_chroot "/home/john/zforge_workspace/chroot"
unmount_chroot "/home/john/zforge_trixie_test/chroot"

# Check if anything is still mounted
echo -e "\nChecking remaining mounts..."
REMAINING=$(mount | grep -E "(zforge_workspace|zforge_trixie_test)" | grep -v grep)

if [ -z "$REMAINING" ]; then
    echo "✅ All chroot filesystems unmounted successfully!"
else
    echo "⚠️  Some mounts remain:"
    echo "$REMAINING"
    echo -e "\nYou may need to manually unmount these or reboot."
fi

echo -e "\nYou can now safely:"
echo "- Exit any chroot shells"
echo "- Remove the workspace directories if needed"
echo "- Start a fresh build"
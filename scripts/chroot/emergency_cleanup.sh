#!/bin/bash
# Emergency cleanup script for stuck chroot mounts
# Run this if use_arch_chroot.sh locks up

echo "═══════════════════════════════════════════════════════════════════"
echo "           Z-FORGE Emergency Cleanup"
echo "═══════════════════════════════════════════════════════════════════"

# Configuration - Use original user's HOME, not root's
ORIGINAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}
ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER" 2>/dev/null || echo "$HOME")
CHROOT_PATH="$ORIGINAL_HOME/zforge_workspace/chroot"

echo "Cleaning up mounts for: $CHROOT_PATH"
echo "Original user: $ORIGINAL_USER"
echo ""

# Kill any processes using the chroot
echo "Killing processes using chroot..."
sudo fuser -k "$CHROOT_PATH" 2>/dev/null || true
sleep 2

# Force unmount everything
echo "Force unmounting filesystems..."
for fs in dev/pts dev proc sys; do
    mount_point="$CHROOT_PATH/$fs"
    if mountpoint -q "$mount_point" 2>/dev/null; then
        echo "  Unmounting $mount_point"
        
        # Try lazy unmount first
        sudo umount -l "$mount_point" 2>/dev/null || true
        
        # Try force unmount
        sudo umount -f "$mount_point" 2>/dev/null || true
        
        # Try normal unmount
        sudo umount "$mount_point" 2>/dev/null || true
        
        # Check if still mounted
        if mountpoint -q "$mount_point" 2>/dev/null; then
            echo "    ⚠️  Still mounted: $mount_point"
        else
            echo "    ✅  Unmounted: $mount_point"
        fi
    else
        echo "  ✅  Not mounted: $mount_point"
    fi
done

echo ""
echo "Checking final mount status..."
remaining_mounts=$(mount | grep "$CHROOT_PATH" || true)
if [ -n "$remaining_mounts" ]; then
    echo "⚠️  Remaining mounts:"
    echo "$remaining_mounts"
else
    echo "✅  All mounts cleaned up successfully"
fi

echo ""
echo "Emergency cleanup complete"
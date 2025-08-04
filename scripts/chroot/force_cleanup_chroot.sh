#!/bin/bash
# Force cleanup of chroot environments with PTY errors

echo "🔧 Force cleaning chroot environments..."

# Kill any processes that might be using the chroot
echo "1. Killing processes using chroot..."
sudo fuser -k /home/john/zforge_workspace/chroot 2>/dev/null || true
sudo fuser -k /home/john/zforge_trixie_test/chroot 2>/dev/null || true

# Wait a moment
sleep 2

# Force unmount everything with lazy unmount
echo "2. Force unmounting filesystems..."

CHROOT_PATHS=(
    "/home/john/zforge_workspace/chroot"
    "/home/john/zforge_trixie_test/chroot"
)

for CHROOT in "${CHROOT_PATHS[@]}"; do
    echo "Processing: $CHROOT"
    
    # Get all mount points for this chroot (in reverse order)
    MOUNTS=$(mount | grep "$CHROOT" | awk '{print $3}' | sort -r)
    
    for MOUNT in $MOUNTS; do
        echo "  Force unmounting: $MOUNT"
        sudo umount -f -l "$MOUNT" 2>/dev/null || true
    done
done

# Additional cleanup for stubborn mounts
echo "3. Additional cleanup..."
sudo umount -f -l /home/john/*/chroot/dev/pts 2>/dev/null || true
sudo umount -f -l /home/john/*/chroot/dev 2>/dev/null || true
sudo umount -f -l /home/john/*/chroot/sys 2>/dev/null || true
sudo umount -f -l /home/john/*/chroot/proc 2>/dev/null || true

# Check what's left
echo "4. Checking remaining mounts..."
REMAINING=$(mount | grep -E "(zforge_workspace|zforge_trixie_test)" || true)

if [ -z "$REMAINING" ]; then
    echo "✅ All mounts cleaned up!"
else
    echo "⚠️  Still mounted:"
    echo "$REMAINING"
    echo ""
    echo "If PTY errors persist, try:"
    echo "sudo reboot"
fi

echo ""
echo "5. Safe to remove directories now:"
echo "sudo rm -rf ~/zforge_workspace"
echo "sudo rm -rf ~/zforge_trixie_test"
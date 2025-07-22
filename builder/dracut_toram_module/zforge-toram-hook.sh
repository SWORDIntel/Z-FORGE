#!/bin/bash
# zforge-toram-hook.sh - Copy live ISO to RAM

# Check if toram boot parameter is set
if ! getarg toram >/dev/null; then
    return 0
fi

echo "Z-FORGE: toram boot parameter detected, copying ISO to RAM..."

# Find the live media device
LIVE_DEV=""
for dev in /dev/sr* /dev/sd*; do
    if [ -b "$dev" ]; then
        # Check if this device contains our squashfs
        if mount -o ro "$dev" /mnt 2>/dev/null; then
            if [ -f /mnt/LiveOS/squashfs.img ] || [ -f /mnt/live/filesystem.squashfs ]; then
                LIVE_DEV="$dev"
                umount /mnt
                break
            fi
            umount /mnt
        fi
    fi
done

if [ -z "$LIVE_DEV" ]; then
    echo "Z-FORGE: ERROR - Could not find live media device"
    return 1
fi

# Check available RAM
AVAIL_RAM=$(free -m | awk '/^Mem:/ {print $7}')
echo "Z-FORGE: Available RAM: ${AVAIL_RAM}MB"

# Mount the live device
mkdir -p /run/initramfs/live
if ! mount -o ro "$LIVE_DEV" /run/initramfs/live; then
    echo "Z-FORGE: ERROR - Failed to mount live device"
    return 1
fi

# Calculate size needed
LIVE_SIZE=0
if [ -f /run/initramfs/live/LiveOS/squashfs.img ]; then
    LIVE_SIZE=$(du -m /run/initramfs/live/LiveOS/squashfs.img | cut -f1)
elif [ -f /run/initramfs/live/live/filesystem.squashfs ]; then
    LIVE_SIZE=$(du -m /run/initramfs/live/live/filesystem.squashfs | cut -f1)
else
    echo "Z-FORGE: ERROR - Could not find squashfs image"
    umount /run/initramfs/live
    return 1
fi

# Add 10% buffer
NEEDED_RAM=$((LIVE_SIZE * 110 / 100))
echo "Z-FORGE: Live image size: ${LIVE_SIZE}MB, needed RAM: ${NEEDED_RAM}MB"

if [ "$AVAIL_RAM" -lt "$NEEDED_RAM" ]; then
    echo "Z-FORGE: ERROR - Not enough RAM (available: ${AVAIL_RAM}MB, needed: ${NEEDED_RAM}MB)"
    umount /run/initramfs/live
    return 1
fi

# Create tmpfs for toram
echo "Z-FORGE: Creating tmpfs for toram..."
mkdir -p /run/initramfs/toram
mount -t tmpfs -o size=${NEEDED_RAM}m tmpfs /run/initramfs/toram

# Copy live image to RAM
echo "Z-FORGE: Copying live image to RAM (this may take a few minutes)..."
cp -a /run/initramfs/live/* /run/initramfs/toram/

# Unmount original device
umount /run/initramfs/live

# Bind mount toram over live
mount --bind /run/initramfs/toram /run/initramfs/live

echo "Z-FORGE: Successfully loaded live image to RAM"
echo "Z-FORGE: You can now safely remove the boot media"

return 0
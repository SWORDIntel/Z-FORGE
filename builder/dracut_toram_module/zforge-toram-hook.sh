#!/bin/sh
# Dracut hook to copy live image to RAM if 'zforge.toram=yes' is on kernel cmdline

type getarg >/dev/null 2>&1 || . /lib/dracut-lib.sh

# Check for the toram parameter
if ! getargbool 0 zforge.toram=yes && ! getargbool 0 toram; then
    # No toram parameter, or it's explicitly 'no'. Exit normally.
    return 0
fi

info "Z-Forge: 'toram' parameter detected. Attempting to copy live image to RAM."

LIVE_IMAGE_DEVICE="${DRACUT_LIVE_ROOT:-/dev/root}"
if [ ! -b "$LIVE_IMAGE_DEVICE" ] && [ "$LIVE_IMAGE_DEVICE" != "/dev/root" ]; then # /dev/root might be a symlink not yet created
    warn "Z-Forge: Could not determine live image device ($LIVE_IMAGE_DEVICE is not a block device)."
    return 1
fi

# If LIVE_IMAGE_DEVICE is /dev/root, it might be a placeholder.
# Try to find the actual device where the ISO is.
# This heuristic looks for a device mounted at /run/initramfs/live (common for live media)
# or /run/initramfs/squashfs_source (common for dmsquash)
REAL_ISO_DEVICE=""
if findmnt -S "$LIVE_IMAGE_DEVICE" /run/initramfs/live >/dev/null 2>&1; then
    REAL_ISO_DEVICE=$(findmnt -S "$LIVE_IMAGE_DEVICE" -n -o SOURCE /run/initramfs/live)
elif findmnt -S "$LIVE_IMAGE_DEVICE" /run/initramfs/squashfs_source >/dev/null 2>&1; then
    REAL_ISO_DEVICE=$(findmnt -S "$LIVE_IMAGE_DEVICE" -n -o SOURCE /run/initramfs/squashfs_source)
elif [ -b "$LIVE_IMAGE_DEVICE" ]; then # If it was a valid block device directly
    REAL_ISO_DEVICE="$LIVE_IMAGE_DEVICE"
else # Fallback: scan common CD/USB devices if label matches or contains known live media files
    # This is more complex and error-prone; relying on dmsquash setup is better.
    # For now, if above fails, we assume dmsquash will handle finding the source.
    info "Z-Forge: REAL_ISO_DEVICE not immediately found, relying on dmsquash to provide source."
fi

if [ -n "$REAL_ISO_DEVICE" ]; then
    info "Z-Forge: Identified real ISO device as $REAL_ISO_DEVICE"
    LIVE_IMAGE_DEVICE="$REAL_ISO_DEVICE"
fi


SQFS_PATH_ON_ISO=$(getarg findiso)
if [ -z "$SQFS_PATH_ON_ISO" ]; then
    SQFS_PATH_ON_ISO="/live/filesystem.squashfs"
    info "Z-Forge: 'findiso' parameter not found, defaulting to $SQFS_PATH_ON_ISO"
fi
# remove leading / if present, as it's relative to ISO root
SQFS_PATH_ON_ISO=${SQFS_PATH_ON_ISO#/}


ISO_CONTENT_MNT="/run/initramfs/iso_source_for_toram"
mkdir -p "$ISO_CONTENT_MNT"

# Check if dmsquash already mounted the source of the squashfs
# This is typically /run/initramfs/squashfs_source
LIVE_SQUASHFS_SOURCE_MNT="/run/initramfs/squashfs_source"

SOURCE_SQFS_FILE=""
NEEDS_UNMOUNT_ISO_CONTENT_MNT=false

if findmnt -R "$LIVE_SQUASHFS_SOURCE_MNT" >/dev/null; then
    info "Z-Forge: Using existing dmsquash mount at $LIVE_SQUASHFS_SOURCE_MNT."
    SOURCE_SQFS_FILE="$LIVE_SQUASHFS_SOURCE_MNT/$SQFS_PATH_ON_ISO"
elif [ -b "$LIVE_IMAGE_DEVICE" ]; then
    info "Z-Forge: Mounting $LIVE_IMAGE_DEVICE to $ISO_CONTENT_MNT to find SquashFS."
    mount -t iso9660 -o ro "$LIVE_IMAGE_DEVICE" "$ISO_CONTENT_MNT"
    if [ $? -ne 0 ]; then
        warn "Z-Forge: Failed to mount $LIVE_IMAGE_DEVICE."
        return 1 # Cannot proceed if mount fails
    fi
    NEEDS_UNMOUNT_ISO_CONTENT_MNT=true
    SOURCE_SQFS_FILE="$ISO_CONTENT_MNT/$SQFS_PATH_ON_ISO"
else
    warn "Z-Forge: Cannot determine source for SquashFS. LIVE_IMAGE_DEVICE ($LIVE_IMAGE_DEVICE) is not a block device and no existing mount found."
    return 1
fi

if [ ! -f "$SOURCE_SQFS_FILE" ]; then
    warn "Z-Forge: SquashFS image not found at $SOURCE_SQFS_FILE."
    if $NEEDS_UNMOUNT_ISO_CONTENT_MNT; then umount "$ISO_CONTENT_MNT"; fi
    return 1
fi

info "Z-Forge: Found SquashFS image at $SOURCE_SQFS_FILE."

TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
SQFS_SIZE_BYTES=$(stat -c%s "$SOURCE_SQFS_FILE")
SQFS_SIZE_KB=$((SQFS_SIZE_BYTES / 1024))

# Required RAM: SquashFS size + size of SquashFS when uncompressed (estimate 2x-3x) + buffer
# For simplicity, let's use a generous buffer for now.
# A more accurate calculation would involve knowing the uncompressed size.
# Let's ask for SQFS size + 256MB free at least.
REQUIRED_RAM_KB=$((SQFS_SIZE_KB + 256000))
# And ensure we don't use more than, say, 75% of total RAM for the tmpfs itself.
MAX_TMPFS_SIZE_KB=$((TOTAL_RAM_KB * 3 / 4))

if [ "$SQFS_SIZE_KB" -gt "$MAX_TMPFS_SIZE_KB" ]; then
    warn "Z-Forge: SquashFS size (${SQFS_SIZE_KB}KB) is too large for tmpfs (max ${MAX_TMPFS_SIZE_KB}KB)."
    if $NEEDS_UNMOUNT_ISO_CONTENT_MNT; then umount "$ISO_CONTENT_MNT"; fi
    return 0 # Continue normal boot
fi

# Check if enough RAM is free (more complex, as current usage varies)
# For now, just check if total RAM is sufficient for SQFS + buffer
if [ "$TOTAL_RAM_KB" -lt "$REQUIRED_RAM_KB" ]; then
    warn "Z-Forge: Not enough total RAM to safely copy SquashFS. Available: ${TOTAL_RAM_KB}KB, Estimated Needed: ${REQUIRED_RAM_KB}KB."
    if $NEEDS_UNMOUNT_ISO_CONTENT_MNT; then umount "$ISO_CONTENT_MNT"; fi
    return 0
fi

RAM_SQFS_MNT="/run/initramfs/ramdisk_rootfs" # Changed name for clarity
mkdir -p "$RAM_SQFS_MNT"
# Mount tmpfs with size of the squashfs file itself.
mount -t tmpfs -o "size=${SQFS_SIZE_KB}k,nr_inodes=0" tmpfs "$RAM_SQFS_MNT"
if [ $? -ne 0 ]; then
    warn "Z-Forge: Failed to mount tmpfs for SquashFS copy."
    if $NEEDS_UNMOUNT_ISO_CONTENT_MNT; then umount "$ISO_CONTENT_MNT"; fi
    return 1
fi
info "Z-Forge: Mounted tmpfs at $RAM_SQFS_MNT."

RAM_SQFS_FILE="$RAM_SQFS_MNT/filesystem.squashfs"

info "Z-Forge: Copying SquashFS to RAM (this may take a while)..."
cp "$SOURCE_SQFS_FILE" "$RAM_SQFS_FILE"
if [ $? -ne 0 ]; then
    warn "Z-Forge: Failed to copy SquashFS to RAM."
    umount "$RAM_SQFS_MNT"
    if $NEEDS_UNMOUNT_ISO_CONTENT_MNT; then umount "$ISO_CONTENT_MNT"; fi
    return 1
fi
info "Z-Forge: SquashFS copied to RAM successfully."

if $NEEDS_UNMOUNT_ISO_CONTENT_MNT; then
    umount "$ISO_CONTENT_MNT"
    info "Z-Forge: Unmounted temporary ISO source $ISO_CONTENT_MNT."
fi

NEW_LOOP_DEV=$(losetup -f --show "$RAM_SQFS_FILE")
if [ -z "$NEW_LOOP_DEV" ]; then
    warn "Z-Forge: Failed to setup loop device for RAM SquashFS."
    umount "$RAM_SQFS_MNT"
    return 1
fi
info "Z-Forge: RAM SquashFS available at $NEW_LOOP_DEV."

# This is where we tell dracut's live/squash module to use our new loop device.
# For dmsquash, it looks for 'root=live:<device>' or similar.
# We need to make $NEW_LOOP_DEV the device that dmsquash uses.
# One way is to update the 'root' kernel argument in the initramfs environment if possible,
# or set a variable that dmsquash checks.
# Dracut's dmsquash module sets $DM_SQUASH_SOURCE to the device.
# Let's try to override the 'root' info for dmsquash.
# The dmsquash module uses `parse_devname` on $dev (from root=live:$dev).
# We can try setting $root and $dev before dmsquash's own cmdline hook runs,
# or hope it picks up $NEWROOT.

# A common pattern is for the hook that prepares the root to set NEWROOT.
# Then, the main dracut script does `switch_root $NEWROOT`.
# We need to mount the new squashfs and set NEWROOT to that mount point.

SQUASHFS_MOUNT_ON_RAM="/run/initramfs/squashfs_on_ram"
mkdir -p "$SQUASHFS_MOUNT_ON_RAM"
mount -t squashfs -o ro "$NEW_LOOP_DEV" "$SQUASHFS_MOUNT_ON_RAM"
if [ $? -ne 0 ]; then
    warn "Z-Forge: Failed to mount RAM SquashFS from $NEW_LOOP_DEV to $SQUASHFS_MOUNT_ON_RAM."
    losetup -d "$NEW_LOOP_DEV"
    umount "$RAM_SQFS_MNT" # umount tmpfs holding the .squashfs file
    return 1
fi
info "Z-Forge: Mounted RAM SquashFS at $SQUASHFS_MOUNT_ON_RAM."

export NEWROOT="$SQUASHFS_MOUNT_ON_RAM"
# Dracut's dmsquash usually creates /dev/root. We are bypassing that by setting NEWROOT directly.
# Ensure subsequent dracut scripts don't try to unmount our tmpfs too early.
# The tmpfs at $RAM_SQFS_MNT needs to persist as it holds the .squashfs file backing $NEW_LOOP_DEV.
# And $SQUASHFS_MOUNT_ON_RAM is the actual rootfs.

# To prevent the original squash device from being used, we might need to
# clear some variables that dmsquash uses, e.g. by modifying /etc/conf.d/dmsquash.conf if it exists
# or unsetting environment variables if they are already set.
# For now, setting NEWROOT is the most standard way to redirect switch_root.

info "Z-Forge: NEWROOT set to $NEWROOT. System should pivot to RAM disk."
return 0

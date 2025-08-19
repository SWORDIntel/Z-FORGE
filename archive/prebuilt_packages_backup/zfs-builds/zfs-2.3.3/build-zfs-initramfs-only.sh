#!/bin/bash
# Build ZFS-only initramfs without ZFSBootMenu (16GB optimized)

set -e

BUILD_ID="$(date +%s)"
OUTPUT_DIR="/tmp/zfs-initramfs-${BUILD_ID}"
KERNEL="/boot/vmlinuz-$(uname -r)"

echo "=== ZFS Initramfs Build (16GB RAM Optimized) ==="
echo "Build ID: ${BUILD_ID}"
echo "Output: ${OUTPUT_DIR}"
echo ""

# System checks
echo "=== Step 1: System Checks ==="
echo -n "ZFS userspace: "
zfs --version | head -1 || { echo "FAILED"; exit 1; }

echo -n "ZFS kernel module: "
modinfo zfs | grep "^version:" | awk '{print $2}' || { echo "FAILED"; exit 1; }

echo -n "Kernel: "
ls -la "$KERNEL" || { echo "FAILED"; exit 1; }

echo "✓ All checks passed"
echo ""

# Create build directory
echo "=== Step 2: Setting up build environment ==="
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# Create ZFS-only dracut config
echo "=== Step 3: Creating ZFS dracut configuration ==="
cat > dracut-zfs.conf << 'EOF'
# ZFS-only initramfs configuration (16GB optimized)
dracutmodules=" bash zfs base kernel-modules udev-rules "
omit_dracutmodules=" systemd systemd-initrd network network-legacy plymouth "
omit_dracutmodules+=" btrfs crypt dmraid dmsquash-live mdraid lvm nfs iscsi nbd "
omit_dracutmodules+=" zfsbootmenu nvmf cifs rngd systemd-battery-check "
add_drivers+=" zfs "
filesystems=" zfs vfat ext4 "
compress="zstd"
compresslevel="3"
hostonly="no"
early_microcode="no"
parallel="yes"
EOF

echo "✓ ZFS-only dracut config created"

# Build with 16-core optimization  
echo ""
echo "=== Step 4: Building ZFS initramfs (16 cores) ==="
echo "Building ZFS-capable initramfs with MAKEFLAGS=-j16..."

MAKEFLAGS="-j16" \
dracut --force \
    --conf dracut-zfs.conf \
    --kver $(uname -r) \
    --no-hostonly \
    --no-early-microcode \
    --verbose \
    initramfs-zfs.img

if [ ! -f "initramfs-zfs.img" ]; then
    echo "✗ ZFS initramfs build failed"
    exit 1
fi

echo "✓ ZFS initramfs created: $(du -h initramfs-zfs.img | cut -f1)"

# Verify contents
echo ""
echo "=== Step 5: Verifying ZFS initramfs contents ==="
echo "ZFS tools in initramfs:"
lsinitrd initramfs-zfs.img | grep -E "(zfs|zpool)" | head -10

echo ""
echo "✓ ZFS initramfs build completed successfully!"
echo ""
echo "Files created:"
echo "  ZFS Initramfs: $OUTPUT_DIR/initramfs-zfs.img ($(du -h initramfs-zfs.img | cut -f1))"
echo ""
echo "Usage:"
echo "1. Copy to boot: sudo cp $OUTPUT_DIR/initramfs-zfs.img /boot/"
echo "2. Use with bootloader - supports ZFS root filesystems"
echo "3. Kernel cmdline example: root=ZFS=rpool/ROOT/LONENOMAD ro quiet"
echo ""
echo "Build directory: $OUTPUT_DIR"
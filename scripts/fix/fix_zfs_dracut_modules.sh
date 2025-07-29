#!/bin/bash
# Fix ZFS kernel modules for dracut
# Ensures ZFS modules are properly installed in chroot

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

echo "═══════════════════════════════════════════════════════════════════"
echo "              Fixing ZFS Kernel Modules for Dracut"
echo "═══════════════════════════════════════════════════════════════════"

if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

echo "[1/5] Checking current ZFS installation..."
if chroot "$CHROOT_PATH" which zfs >/dev/null 2>&1; then
    echo "✅ ZFS userspace tools found"
    chroot "$CHROOT_PATH" zfs version || true
else
    echo "❌ ZFS userspace tools not found!"
fi

echo ""
echo "[2/5] Checking for ZFS kernel modules..."
KERNEL_VERSION=$(chroot "$CHROOT_PATH" ls /lib/modules | head -1)
echo "Kernel version: $KERNEL_VERSION"

ZFS_MODULE_PATH="$CHROOT_PATH/lib/modules/$KERNEL_VERSION/extra/zfs/zfs.ko"
if [ -f "$ZFS_MODULE_PATH" ]; then
    echo "✅ ZFS kernel module found at expected location"
else
    echo "❌ ZFS kernel module NOT found at: $ZFS_MODULE_PATH"
    echo "   Attempting to build ZFS modules in chroot..."
    
    # Run the chroot module builder
    if [ -x "/opt/github/Z-FORGE/build_zfs_233_chroot_modules.sh" ]; then
        echo "   Running ZFS chroot module builder..."
        /opt/github/Z-FORGE/build_zfs_233_chroot_modules.sh "$CHROOT_PATH"
    else
        echo "   ERROR: Chroot module builder not found!"
    fi
fi

echo ""
echo "[3/5] Updating module dependencies..."
chroot "$CHROOT_PATH" depmod -a "$KERNEL_VERSION" || true

echo ""
echo "[4/5] Configuring dracut for ZFS..."
# Ensure dracut ZFS module directory exists
mkdir -p "$CHROOT_PATH/usr/lib/dracut/modules.d/90zfs"

# Create a basic ZFS dracut module if missing
if [ ! -f "$CHROOT_PATH/usr/lib/dracut/modules.d/90zfs/module-setup.sh" ]; then
    echo "Creating basic ZFS dracut module..."
    cat > "$CHROOT_PATH/usr/lib/dracut/modules.d/90zfs/module-setup.sh" << 'EOF'
#!/bin/bash
# ZFS dracut module

check() {
    # Only include if ZFS is available
    which zfs >/dev/null 2>&1 || return 1
    return 0
}

depends() {
    echo udev-rules
    return 0
}

installkernel() {
    # Install ZFS kernel modules
    instmods zfs
    instmods zavl
    instmods znvpair
    instmods zunicode
    instmods zcommon
    instmods icp
    instmods spl
    instmods zlua
}

install() {
    # Install ZFS binaries
    inst_multiple zfs zpool zdb mount.zfs
    
    # Install ZFS udev rules
    inst_rules 60-zvol.rules 69-vdev.rules 90-zfs.rules
    
    # Install ZFS systemd services
    inst_simple /lib/systemd/system/zfs-import-cache.service
    inst_simple /lib/systemd/system/zfs-import-scan.service
    inst_simple /lib/systemd/system/zfs-mount.service
    inst_simple /lib/systemd/system/zfs-share.service
    inst_simple /lib/systemd/system/zfs-zed.service
    inst_simple /lib/systemd/system/zfs-import.target
    inst_simple /lib/systemd/system/zfs-volumes.target
    inst_simple /lib/systemd/system/zfs.target
    
    # Install configuration files
    inst_simple /etc/zfs/zpool.cache
    inst_simple /etc/hostid
    
    # Create necessary directories
    mkdir -p "${initdir}/etc/zfs"
    
    # Install hook scripts
    inst_hook cmdline 95 "$moddir/parse-zfs.sh"
    inst_hook mount 98 "$moddir/mount-zfs.sh"
    
    # Ensure ZFS modules are loaded
    echo "zfs" >> "${initdir}/etc/modules-load.d/zfs.conf"
}
EOF
    chmod +x "$CHROOT_PATH/usr/lib/dracut/modules.d/90zfs/module-setup.sh"
fi

echo ""
echo "[5/5] Testing dracut ZFS module..."
if chroot "$CHROOT_PATH" dracut --list-modules 2>/dev/null | grep -q zfs; then
    echo "✅ ZFS dracut module is available"
else
    echo "⚠️  ZFS dracut module may not be properly configured"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    ZFS Module Fix Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Retry the build: make build"
echo "2. The dracut/initramfs generation should now find ZFS modules"
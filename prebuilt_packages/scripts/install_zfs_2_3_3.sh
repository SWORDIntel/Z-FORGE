#!/bin/bash
# ZFS 2.3.3 Userspace installer for Z-FORGE

CHROOT_PATH="$1"
if [ -z "$CHROOT_PATH" ]; then
    echo "Usage: $0 <chroot_path>"
    exit 1
fi

echo "Installing ZFS 2.3.3 userspace tools to chroot: $CHROOT_PATH"

# Extract package to chroot
cd "$CHROOT_PATH"
tar -xzf /opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3-userspace.tar.gz

# Install Python modules in chroot
chroot "$CHROOT_PATH" python3 -m pip install pyzfs || true

# Note: No kernel modules - will use host ZFS modules or install separately
echo "✅ ZFS 2.3.3 userspace tools installation complete"
echo "⚠️  Note: This is userspace only - kernel modules handled separately"

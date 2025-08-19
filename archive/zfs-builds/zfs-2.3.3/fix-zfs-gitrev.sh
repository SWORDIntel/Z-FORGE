#!/bin/bash
# Fix missing zfs_gitrev.h file

set -e

cd /usr/src/zfs-build-minimal/zfs-2.3.3

# Create the missing zfs_gitrev.h file
echo "Creating missing zfs_gitrev.h..."
cat > include/zfs_gitrev.h << 'EOF'
#ifndef _ZFS_GITREV_H
#define _ZFS_GITREV_H

#define ZFS_META_GITREV "zfs-2.3.3-1"

#endif /* _ZFS_GITREV_H */
EOF

# Also create it in the build directory structure
mkdir -p module/include
cp include/zfs_gitrev.h module/include/

# Continue the kernel module build
echo "Continuing kernel module build..."
cd module
taskset -c 0-7 make -j8

# Install kernel modules
echo "Installing kernel modules..."
make install

# Load modules
echo "Loading ZFS modules..."
depmod -a
modprobe zfs || echo "Module load failed - may need reboot"

echo ""
echo "Build complete!"
zfs --version || echo "zfs command issue"
modinfo zfs | grep version || echo "module not loaded"
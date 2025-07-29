#!/bin/bash
# Build ZFS 2.3.3 using native debian directory

set -e

cd /usr/src/zfs-2.3.3

# Copy the contrib debian files to main directory
echo "Using native ZFS debian packaging..."
cp -r contrib/debian/* debian/

# Update optimization flags in rules
sed -i 's/^export DEB_CFLAGS_MAINT_APPEND.*/export DEB_CFLAGS_MAINT_APPEND = -O2 -march=native -mtune=native/' debian/rules
sed -i 's/^export DEB_CXXFLAGS_MAINT_APPEND.*/export DEB_CXXFLAGS_MAINT_APPEND = -O2 -march=native -mtune=native/' debian/rules

# Remove compat file if exists
rm -f debian/compat

# Build on P-cores
echo "Building Debian packages on P-cores (0-7)..."
taskset -c 0-7 dpkg-buildpackage -us -uc -b -j8

echo ""
echo "Build complete! Packages are in /usr/src/"
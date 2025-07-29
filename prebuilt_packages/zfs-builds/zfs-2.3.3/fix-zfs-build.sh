#!/bin/bash
# Quick fix for the current ZFS build

cd /usr/src/zfs-2.3.3

# Remove the duplicate compat file
rm -f debian/compat

# Continue the build
echo "Continuing build on P-cores..."
taskset -c 0-7 dpkg-buildpackage -us -uc -b -j8
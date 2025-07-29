#!/bin/bash
# Fix missing changelog in ZFS build

cd /usr/src/zfs-2.3.3

# Create the changelog
cat > debian/changelog << 'EOF'
zfs-linux (2.3.3-1) unstable; urgency=medium

  * Local build of ZFS 2.3.3
  * Optimized for Meteor Lake with P-core AVX-512

 -- Local Build <root@localhost>  Sat, 26 Jul 2025 20:00:00 +0000
EOF

# Remove compat file if it exists
rm -f debian/compat

# Continue the build
echo "Continuing build on P-cores..."
taskset -c 0-7 dpkg-buildpackage -us -uc -b -j8
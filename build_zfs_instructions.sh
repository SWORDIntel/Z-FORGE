#!/bin/bash
# ZFS 2.3.3 build instructions - shows commands to run

echo "═══════════════════════════════════════════════════════════════════"
echo "        ZFS 2.3.3 Build Instructions"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Run these commands to build ZFS 2.3.3 on your system:"
echo ""

echo "1. Install build dependencies:"
echo "   sudo apt-get update"
echo "   sudo apt-get install -y build-essential autoconf automake libtool gawk alien fakeroot dkms libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev libaio-dev libattr1-dev libelf-dev linux-headers-\$(uname -r) python3 python3-dev python3-setuptools python3-cffi libffi-dev python3-packaging python3-distutils"
echo ""

echo "2. Create build directory and download ZFS:"
echo "   mkdir -p /tmp/zfs_build && cd /tmp/zfs_build"
echo "   wget https://github.com/openzfs/zfs/releases/download/zfs-2.3.3/zfs-2.3.3.tar.gz"
echo "   tar xzf zfs-2.3.3.tar.gz && cd zfs-2.3.3"
echo ""

echo "3. Configure ZFS build:"
if grep -q "CONFIG_MODULES=y" /boot/config-$(uname -r) 2>/dev/null; then
    echo "   # Your kernel supports modules - building with kernel support:"
    echo "   ./configure --prefix=/usr --sysconfdir=/etc --sbindir=/sbin --libdir=/usr/lib --enable-systemd --enable-pyzfs --with-config=all"
else
    echo "   # Your kernel doesn't support modules - building userspace only:"
    echo "   ./configure --prefix=/usr --sysconfdir=/etc --sbindir=/sbin --libdir=/usr/lib --enable-systemd --enable-pyzfs --with-config=user"
fi
echo ""

echo "4. Build ZFS:"
echo "   make -j\$(nproc)"
echo ""

echo "5. Install ZFS:"
echo "   sudo make install"
echo "   sudo ldconfig"
echo ""

echo "6. Load module and enable services (if kernel modules built):"
echo "   sudo modprobe zfs"
echo "   sudo systemctl enable zfs.target"
echo ""

echo "7. Test installation:"
echo "   zfs version"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Alternative: Use existing build scripts:"
echo ""
echo "For kernel modules + userspace:"
echo "  ./scripts/build/build_zfs_233_smart.sh"
echo ""
echo "For userspace tools only:"
echo "  ./scripts/build/build_zfs_233_userspace_only.sh"
echo ""
echo "Or check what scripts are available:"
echo "  ls -la scripts/build/build_zfs_*"
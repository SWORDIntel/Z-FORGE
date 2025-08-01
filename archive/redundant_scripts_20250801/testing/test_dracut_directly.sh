#!/bin/bash
# Test dracut directly in the chroot to see the actual error

CHROOT="${CHROOT_PATH:-/home/john/zforge_workspace/chroot}"
KVER="6.12.35+deb13-amd64"

echo "Testing dracut directly in chroot..."
echo "================================"

# Test 1: Try dracut with verbose output
echo "Test 1: Running dracut with full verbosity"
sudo chroot "$CHROOT" dracut --force --verbose --debug --kver "$KVER" "/boot/initrd.img-$KVER" 2>&1 | tail -50

echo ""
echo "Test 2: Check if ZFS modules are loaded"
sudo chroot "$CHROOT" find /lib/modules/"$KVER" -name "*.ko" | grep -i zfs

echo ""
echo "Test 3: Check dracut configuration"
sudo chroot "$CHROOT" cat /etc/dracut.conf.d/zfs.conf 2>/dev/null || echo "No ZFS dracut config found"

echo ""
echo "Test 4: Try dracut without kernel version"
sudo chroot "$CHROOT" dracut --force --list-modules 2>&1 | grep -E "zfs|90zfs"

echo ""
echo "Test 5: Check for missing dependencies"
sudo chroot "$CHROOT" ldd /usr/bin/dracut 2>&1 || echo "dracut is a script"

echo ""
echo "Test 6: Try minimal dracut command"
sudo chroot "$CHROOT" dracut --force --no-hostonly --no-hostonly-cmdline "/tmp/test-initrd.img" 2>&1

echo ""
echo "Test 7: Check kernel module dependencies"
sudo chroot "$CHROOT" modinfo zfs 2>&1 | head -10 || echo "Can't load modinfo for zfs"
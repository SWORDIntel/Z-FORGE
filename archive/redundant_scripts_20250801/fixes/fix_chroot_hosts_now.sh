#!/bin/bash
# Fix chroot hosts file immediately

echo "1786" | sudo -S tee -a ${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/etc/hosts > /dev/null << 'EOF'

# Z-FORGE DNS workaround for Debian repositories
151.101.2.132 deb.debian.org
151.101.66.132 security.debian.org
151.101.130.132 ftp.debian.org
151.101.194.132 debian.map.fastlydns.net
EOF

echo "Fixed chroot hosts file with Debian repository IPs"
echo "Current chroot hosts file:"
echo "1786" | sudo -S cat ${CHROOT_PATH:-/home/john/zforge_workspace/chroot}/etc/hosts
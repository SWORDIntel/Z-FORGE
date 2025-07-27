#!/bin/bash
# Quick DNS fix for chroot

echo "Adding Debian repository IPs to chroot hosts file..."

# Add the entries directly
sudo bash -c 'cat >> /tmp/zforge_workspace/chroot/etc/hosts << EOF

# Z-FORGE DNS workaround for Debian repositories
151.101.2.132 deb.debian.org
151.101.66.132 security.debian.org  
151.101.130.132 ftp.debian.org
151.101.194.132 debian.map.fastlydns.net
EOF'

echo "DNS fix applied. Testing connectivity..."

# Test chroot DNS resolution
sudo chroot /tmp/zforge_workspace/chroot /bin/bash -c 'ping -c 1 deb.debian.org' && echo "✓ DNS working" || echo "✗ DNS still not working"

echo "Resume build with:"
echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume"
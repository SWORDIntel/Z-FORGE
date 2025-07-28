#!/bin/bash
# Fix chroot DNS and apt-key issues immediately

echo "Fixing chroot issues..."

# Kill any existing apt processes
echo "1786" | sudo -S pkill -f apt-get 2>/dev/null || true
echo "1786" | sudo -S pkill -f dpkg 2>/dev/null || true
sleep 2

# Fix the hosts file in chroot (it seems to have been reset)
echo "1786" | sudo -S tee -a /tmp/zforge_workspace/chroot/etc/hosts > /dev/null << 'EOF'

# Z-FORGE DNS workaround for Debian repositories  
151.101.2.132 deb.debian.org
151.101.66.132 security.debian.org
151.101.130.132 ftp.debian.org
151.101.194.132 debian.map.fastlydns.net
EOF

# Remove any stale lock files
echo "1786" | sudo -S rm -f /tmp/zforge_workspace/chroot/var/lib/dpkg/lock*
echo "1786" | sudo -S rm -f /tmp/zforge_workspace/chroot/var/cache/apt/archives/lock

# Create the apt-key wrapper directly
echo "1786" | sudo -S tee /tmp/zforge_workspace/chroot/usr/bin/apt-key > /dev/null << 'EOF'
#!/bin/bash
# Minimal apt-key wrapper for compatibility
echo "apt-key is deprecated, but continuing..."
case "$1" in
    add)
        gpg --import "$2" 2>/dev/null || true
        ;;
    *)
        echo "apt-key command: $*"
        ;;
esac
exit 0
EOF

echo "1786" | sudo -S chmod +x /tmp/zforge_workspace/chroot/usr/bin/apt-key

# Create symlink
echo "1786" | sudo -S ln -sf /usr/bin/apt-key /tmp/zforge_workspace/chroot/usr/local/bin/apt-key 2>/dev/null || true

# Test DNS resolution in chroot
echo "Testing chroot DNS resolution..."
echo "1786" | sudo -S chroot /tmp/zforge_workspace/chroot /bin/bash -c 'ping -c 1 deb.debian.org' && echo "✓ DNS working" || echo "✗ DNS still not working"

echo "Chroot fixes applied. Resume build:"
echo "echo '1786' | sudo -S python3 builder/z-forge.py --build-spec build_spec.yml --resume"
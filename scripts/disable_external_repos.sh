#!/bin/bash
# Disable external repositories that interfere with builds

echo "=== Disabling external repositories ==="

# Backup current sources
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup_$(date +%Y%m%d_%H%M%S)

# Remove Dell repository from host system
if [ -f "/etc/apt/sources.list.d/dell-system-update.list" ]; then
    sudo mv /etc/apt/sources.list.d/dell-system-update.list /etc/apt/sources.list.d/dell-system-update.list.disabled
    echo "✓ Disabled Dell repository on host"
fi

# Remove any Dell keyrings
if [ -f "/usr/share/keyrings/dell-trusted.gpg" ]; then
    sudo mv /usr/share/keyrings/dell-trusted.gpg /usr/share/keyrings/dell-trusted.gpg.disabled
    echo "✓ Disabled Dell keyring"
fi

# If chroot exists, clean it too
if [ -d "/root/zforge_workspace/chroot" ]; then
    echo "Cleaning chroot repositories..."
    
    # Remove Dell repo from chroot
    sudo rm -f /root/zforge_workspace/chroot/etc/apt/sources.list.d/dell-*
    
    # Keep only essential Trixie repos
    cat << 'EOF' | sudo tee /root/zforge_workspace/chroot/etc/apt/sources.list
# Debian Trixie - Essential only
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
EOF

    # Add local snapshot repository
    echo "deb [trusted=yes] file:///root/zforge_cache/trixie_snapshot/repository ./" | sudo tee /root/zforge_workspace/chroot/etc/apt/sources.list.d/zforge-snapshot.list
    
    echo "✓ Chroot sources cleaned"
fi

echo "External repositories disabled!"
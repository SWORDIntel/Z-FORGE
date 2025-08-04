#!/bin/bash
# Fix APT issues in chroot before building

set -e

echo "🔧 Fixing APT permissions and configuration..."

# Fix APT sandbox permissions
if [ -d /var/lib/apt/lists/partial ]; then
    echo "Fixing APT partial directory permissions..."
    chown -R _apt:root /var/lib/apt/lists/partial 2>/dev/null || true
    chmod 755 /var/lib/apt/lists/partial
fi

# Remove problematic Dell repository if present
if [ -f /etc/apt/sources.list.d/dell.list ]; then
    echo "Removing Dell repository (not needed for build)..."
    rm -f /etc/apt/sources.list.d/dell.list
fi

# Remove any Dell keyrings
rm -f /usr/share/keyrings/dell*.gpg 2>/dev/null || true
rm -f /etc/apt/trusted.gpg.d/dell*.gpg 2>/dev/null || true

# Clean APT cache
echo "Cleaning APT cache..."
apt-get clean
rm -rf /var/lib/apt/lists/*

# Recreate APT directories with correct permissions
mkdir -p /var/lib/apt/lists/partial
chown -R _apt:root /var/lib/apt/lists/partial || true

# Update sources.list to use only Debian repos for build
echo "Configuring clean Debian sources..."
cat > /etc/apt/sources.list << 'EOF'
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
EOF

# Remove all third-party sources temporarily
mkdir -p /etc/apt/sources.list.d.backup
mv /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d.backup/ 2>/dev/null || true

# Update package lists
echo "Updating package lists..."
apt-get update

echo "✅ APT configuration fixed!"
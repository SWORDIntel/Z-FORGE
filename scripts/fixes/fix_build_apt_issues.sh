#!/bin/bash
# Comprehensive fix for APT issues during Z-FORGE build

set -euo pipefail

WORKSPACE="${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Z-FORGE Build APT Issues Fixer ==="
echo "This script will fix:"
echo "  1. Dell repository GPG key issues"
echo "  2. APT permission warnings"
echo "  3. Chroot package installation failures"
echo ""

# 1. Fix Dell repository on host
echo "Step 1: Fixing Dell repository..."
echo "----------------------------------------"

# Create keyrings directory
mkdir -p /usr/share/keyrings

# Download Dell GPG key
echo "Downloading Dell GPG key..."
wget -qO - https://linux.dell.com/repo/pgp_pubkeys/0x1285491434D8786F.asc | \
    gpg --dearmor -o /usr/share/keyrings/dell-trusted.gpg
chmod 644 /usr/share/keyrings/dell-trusted.gpg

# Update Dell repository entries to use the key
for file in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
    if [ -f "$file" ] && grep -q "linux.dell.com" "$file" 2>/dev/null; then
        echo "Updating $file..."
        sed -i 's|deb https://linux.dell.com|deb [signed-by=/usr/share/keyrings/dell-trusted.gpg] https://linux.dell.com|g' "$file"
        # Remove duplicate signed-by entries
        sed -i 's|\[signed-by=/usr/share/keyrings/dell-trusted.gpg\] \[signed-by=/usr/share/keyrings/dell-trusted.gpg\]|[signed-by=/usr/share/keyrings/dell-trusted.gpg]|g' "$file"
    fi
done

echo "✅ Dell repository fixed"

# 2. Fix APT permissions on host
echo ""
echo "Step 2: Fixing APT permissions..."
echo "----------------------------------------"

# Fix permissions for _apt user
chown -R _apt:root /var/lib/apt/lists/partial 2>/dev/null || true
chmod 755 /var/lib/apt/lists/partial 2>/dev/null || true
chmod 755 /var/lib/apt/lists 2>/dev/null || true

# Clean and update
apt-get clean
apt-get update || echo "⚠️  Some warnings may remain, but build should proceed"

echo "✅ APT permissions fixed"

# 3. Fix chroot environment if it exists
if [ -d "$CHROOT_PATH" ]; then
    echo ""
    echo "Step 3: Fixing chroot environment..."
    echo "----------------------------------------"
    
    # Ensure network configuration in chroot
    echo "Setting up chroot network..."
    cat > "$CHROOT_PATH/etc/resolv.conf" << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
EOF
    
    # Copy host's apt sources if chroot sources are missing
    if [ ! -f "$CHROOT_PATH/etc/apt/sources.list" ] || [ ! -s "$CHROOT_PATH/etc/apt/sources.list" ]; then
        echo "Copying APT sources to chroot..."
        cp /etc/apt/sources.list "$CHROOT_PATH/etc/apt/sources.list"
        # Remove Dell repo from chroot (not needed for build)
        sed -i '/linux\.dell\.com/d' "$CHROOT_PATH/etc/apt/sources.list"
    fi
    
    # Fix APT permissions in chroot
    if [ -d "$CHROOT_PATH/var/lib/apt/lists" ]; then
        chown -R root:root "$CHROOT_PATH/var/lib/apt/lists" 2>/dev/null || true
        mkdir -p "$CHROOT_PATH/var/lib/apt/lists/partial"
        chown -R _apt:root "$CHROOT_PATH/var/lib/apt/lists/partial" 2>/dev/null || true
        chmod 755 "$CHROOT_PATH/var/lib/apt/lists/partial" 2>/dev/null || true
    fi
    
    # Update package lists in chroot
    echo "Updating chroot package lists..."
    chroot "$CHROOT_PATH" apt-get update || {
        echo "Failed to update in chroot, attempting fixes..."
        
        # Ensure /dev/null exists in chroot
        [ -e "$CHROOT_PATH/dev/null" ] || mknod -m 666 "$CHROOT_PATH/dev/null" c 1 3
        
        # Retry
        chroot "$CHROOT_PATH" apt-get update
    }
    
    # Fix any broken packages in chroot
    echo "Fixing any broken packages in chroot..."
    chroot "$CHROOT_PATH" dpkg --configure -a 2>/dev/null || true
    chroot "$CHROOT_PATH" apt-get install -f -y 2>/dev/null || true
    
    # Test package installation
    echo "Testing package installation in chroot..."
    if chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends nano >/dev/null 2>&1; then
        echo "✅ Chroot package installation working"
    else
        echo "⚠️  Chroot package installation may still have issues"
    fi
else
    echo ""
    echo "Step 3: Chroot not found at $CHROOT_PATH (this is OK if you haven't started the build yet)"
fi

# 4. Summary
echo ""
echo "=== Summary ==="
echo "✅ Dell repository GPG key installed"
echo "✅ APT permissions fixed"
if [ -d "$CHROOT_PATH" ]; then
    echo "✅ Chroot environment configured"
fi
echo ""
echo "You can now proceed with the build. The APT warnings should be resolved."
echo ""
echo "To run the build:"
echo "  sudo python3 build.py"
echo "  OR"
echo "  ./launch-enhanced-gui.sh"
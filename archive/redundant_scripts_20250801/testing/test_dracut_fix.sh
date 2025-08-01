#!/bin/bash
# Test the dracut fix for kernel version with + character

CHROOT="${CHROOT_PATH:-/home/john/zforge_workspace/chroot}"
KVER="6.12.35+deb13-amd64"

echo "Testing dracut fix for kernel version: $KVER"
echo "=========================================="

# First verify the kernel modules directory exists
echo "1. Checking kernel modules directory..."
if [ -d "$CHROOT/lib/modules/$KVER" ]; then
    echo "✓ Kernel modules directory exists: /lib/modules/$KVER"
else
    echo "✗ Kernel modules directory NOT FOUND!"
    echo "Available kernel versions:"
    ls -la "$CHROOT/lib/modules/"
    exit 1
fi

# Check if dracut is installed
echo -e "\n2. Checking dracut installation..."
if sudo chroot "$CHROOT" which dracut >/dev/null 2>&1; then
    echo "✓ dracut is installed"
    sudo chroot "$CHROOT" dracut --version
else
    echo "✗ dracut is NOT installed!"
    exit 1
fi

# Check for ZFS dracut module
echo -e "\n3. Checking for ZFS dracut module..."
if [ -d "$CHROOT/usr/lib/dracut/modules.d/90zfs" ]; then
    echo "✓ ZFS dracut module exists"
    ls -la "$CHROOT/usr/lib/dracut/modules.d/90zfs/"
else
    echo "✗ ZFS dracut module NOT FOUND!"
    echo "Available dracut modules:"
    ls -la "$CHROOT/usr/lib/dracut/modules.d/" | grep -i zfs || echo "No ZFS modules found"
fi

# Test the wrapper script approach
echo -e "\n4. Testing dracut with wrapper script..."
cat > "$CHROOT/tmp/test_dracut_wrapper.sh" << 'EOF'
#!/bin/bash
# Test wrapper for dracut with special characters
set -e

KVER="6.12.35+deb13-amd64"
OUTPUT="/tmp/test-initrd.img"

echo "Testing dracut with kernel version: $KVER"

# Create a temporary symlink without special characters
SAFE_KVER=$(echo "$KVER" | tr '+' '_')
echo "Creating safe symlink: /lib/modules/$SAFE_KVER -> /lib/modules/$KVER"

if [ ! -e "/lib/modules/$SAFE_KVER" ]; then
    ln -sf "/lib/modules/$KVER" "/lib/modules/$SAFE_KVER"
fi

# Try with safe version
echo "Attempting dracut with safe kernel version..."
if dracut --force --verbose --kver "$SAFE_KVER" "$OUTPUT" 2>&1; then
    echo "✓ SUCCESS with safe version!"
    ls -la "$OUTPUT"
    rm -f "$OUTPUT"
    rm -f "/lib/modules/$SAFE_KVER"
    exit 0
fi

# Clean up symlink and try original
rm -f "/lib/modules/$SAFE_KVER"

echo "Attempting dracut with original kernel version..."
if dracut --force --verbose --kver "$KVER" "$OUTPUT" 2>&1; then
    echo "✓ SUCCESS with original version!"
    ls -la "$OUTPUT"
    rm -f "$OUTPUT"
    exit 0
fi

echo "Attempting dracut without kernel version..."
if dracut --force --verbose "$OUTPUT" 2>&1; then
    echo "✓ SUCCESS without version!"
    ls -la "$OUTPUT"
    rm -f "$OUTPUT"
    exit 0
fi

echo "✗ All dracut attempts failed"
exit 1
EOF

chmod +x "$CHROOT/tmp/test_dracut_wrapper.sh"
sudo chroot "$CHROOT" /tmp/test_dracut_wrapper.sh

echo -e "\n5. Test complete!"
echo "If the wrapper script succeeded, the fix should work during the build."
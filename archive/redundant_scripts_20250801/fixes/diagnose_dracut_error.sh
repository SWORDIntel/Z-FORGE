#!/bin/bash
# Diagnose dracut initramfs generation error

CHROOT_PATH="${CHROOT_PATH:-/home/john/zforge_workspace/chroot}"

echo "=== Diagnosing Dracut Error ==="
echo

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "[!] Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

# Check dracut installation
echo "1. Checking dracut installation:"
if sudo chroot "$CHROOT_PATH" which dracut >/dev/null 2>&1; then
    echo "   ✓ dracut is installed"
    sudo chroot "$CHROOT_PATH" dracut --version 2>&1 | head -1
else
    echo "   ✗ dracut is NOT installed"
fi
echo

# Check kernel modules
echo "2. Checking kernel modules directory:"
if [ -d "$CHROOT_PATH/lib/modules" ]; then
    echo "   Available kernel versions:"
    sudo ls -la "$CHROOT_PATH/lib/modules/" | grep ^d | awk '{print "   - " $NF}'
else
    echo "   ✗ No /lib/modules directory found"
fi
echo

# Check for kernel with special characters
echo "3. Checking for kernels with special characters:"
for kver in $(sudo ls "$CHROOT_PATH/lib/modules/" 2>/dev/null); do
    if [[ "$kver" == *"+"* ]]; then
        echo "   Found kernel with '+': $kver"
        # Check if kernel modules exist
        if [ -f "$CHROOT_PATH/lib/modules/$kver/modules.dep" ]; then
            echo "   ✓ modules.dep exists"
        else
            echo "   ✗ modules.dep missing - running depmod"
            sudo chroot "$CHROOT_PATH" depmod "$kver"
        fi
    fi
done
echo

# Check dracut configuration
echo "4. Checking dracut configuration:"
if [ -d "$CHROOT_PATH/etc/dracut.conf.d" ]; then
    echo "   Configuration files:"
    sudo ls -la "$CHROOT_PATH/etc/dracut.conf.d/"
    if [ -f "$CHROOT_PATH/etc/dracut.conf.d/zforge.conf" ]; then
        echo "   ZForge config content:"
        sudo cat "$CHROOT_PATH/etc/dracut.conf.d/zforge.conf" | sed 's/^/   /'
    fi
else
    echo "   ✗ No dracut config directory"
fi
echo

# Test dracut directly
echo "5. Testing dracut command directly:"
KERNEL_VERSION=$(sudo ls "$CHROOT_PATH/lib/modules/" | head -1)
if [ -n "$KERNEL_VERSION" ]; then
    echo "   Testing with kernel: $KERNEL_VERSION"
    
    # Create test wrapper script
    cat > /tmp/test_dracut.sh << 'EOF'
#!/bin/bash
set -x
KVER="$1"
OUTPUT="/tmp/test-initrd.img"

echo "Testing dracut with kernel: $KVER"

# Try different dracut invocations
echo "Method 1: Standard dracut"
dracut --force --verbose --kver "$KVER" "$OUTPUT" 2>&1

if [ ! -f "$OUTPUT" ]; then
    echo "Method 2: Dracut without kver"
    dracut --force --verbose "$OUTPUT" 2>&1
fi

if [ -f "$OUTPUT" ]; then
    echo "Success! Initrd created: $(ls -lh $OUTPUT)"
    rm -f "$OUTPUT"
    exit 0
else
    echo "Failed to create initrd"
    exit 1
fi
EOF
    
    chmod +x /tmp/test_dracut.sh
    sudo cp /tmp/test_dracut.sh "$CHROOT_PATH/tmp/"
    
    echo "   Running test..."
    if sudo chroot "$CHROOT_PATH" /tmp/test_dracut.sh "$KERNEL_VERSION"; then
        echo "   ✓ Dracut test successful"
    else
        echo "   ✗ Dracut test failed"
    fi
    
    rm -f /tmp/test_dracut.sh
else
    echo "   ✗ No kernel version found"
fi

echo
echo "6. Checking for missing dependencies:"
# Check for common dracut dependencies
DEPS="kmod binutils cpio gzip bzip2 xz-utils"
for dep in $DEPS; do
    if sudo chroot "$CHROOT_PATH" which $dep >/dev/null 2>&1; then
        echo "   ✓ $dep is installed"
    else
        echo "   ✗ $dep is MISSING"
    fi
done

echo
echo "=== Diagnosis Complete ==="
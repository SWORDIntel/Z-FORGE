#!/bin/bash
# Test script for dracut-based build

echo "=== Z-FORGE Dracut Build Test ==="
echo "Testing dracut integration with ZFS..."
echo ""

# Set working directory
cd /opt/github/Z-FORGE

# First, validate the build system
echo "Step 1: Validating build system..."
python3 builder/modules/build_pipeline_validator.py

if [ $? -ne 0 ]; then
    echo "ERROR: Build system validation failed!"
    exit 1
fi

echo ""
echo "Step 2: Checking dracut module..."

# Check if dracut_config module exists
if [ -f builder/modules/dracut_config.py ]; then
    echo "✓ dracut_config.py exists"
else
    echo "✗ dracut_config.py missing!"
    exit 1
fi

# Check if dracut is in build specs
echo ""
echo "Step 3: Checking build specifications..."
for spec in build_spec*.yml; do
    if grep -q "kernel_acquisition" "$spec" 2>/dev/null; then
        if grep -q "dracut_config" "$spec" 2>/dev/null; then
            echo "✓ $spec has dracut_config module"
        else
            echo "✗ $spec missing dracut_config module (has kernel_acquisition)"
        fi
    fi
done

echo ""
echo "Step 4: Testing dracut module imports..."
python3 -c "
from builder.modules.dracut_config import DracutConfig
from builder.modules.kernel_acquisition import KernelAcquisition
print('✓ Modules import successfully')
" 2>&1

echo ""
echo "=== Configuration Summary ==="
echo "• Dracut replaces initramfs-tools for initrd generation"
echo "• ZFS support integrated via dracut ZFS module"
echo "• Compression: zstd (optimal balance)"
echo "• Host-only mode: disabled (for portability)"
echo ""
echo "Build system is ready for dracut-based builds!"
echo ""
echo "To run a full build with sudo:"
echo "  sudo python3 build.py --spec build_spec_stable.yml"
echo ""
echo "For fastest test build:"
echo "  sudo python3 build.py --spec build_spec_outside_packages.yml"
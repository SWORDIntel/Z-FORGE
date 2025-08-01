#!/bin/bash
# Verify Z-FORGE build readiness

echo "=== Z-FORGE Build Readiness Check ==="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: This script must be run as root (sudo)"
    exit 1
else
    echo "✅ Running as root"
fi

# Check Python version
echo -n "Python version: "
python3 --version
if [ $? -eq 0 ]; then
    echo "✅ Python3 available"
else
    echo "❌ Python3 not found"
    exit 1
fi

# Check required system tools
echo
echo "Checking required tools:"
for tool in debootstrap xorriso mksquashfs grub-mkimage curl wget; do
    if command -v $tool &> /dev/null; then
        echo "✅ $tool found"
    else
        echo "❌ $tool missing - please install"
    fi
done

# Check build configurations
echo
echo "Available build configurations:"
echo "1. T30-specific build:"
if [ -f "config/t30/t30_build_spec.yml" ]; then
    echo "   ✅ config/t30/t30_build_spec.yml exists"
else
    echo "   ❌ config/t30/t30_build_spec.yml missing"
fi

echo
echo "2. Universal auto-detect build:"
if [ -f "config/universal/universal_build_spec.yml" ]; then
    echo "   ✅ config/universal/universal_build_spec.yml exists"
else
    echo "   ❌ config/universal/universal_build_spec.yml missing"
fi

# Check main build script
echo
echo "Build system:"
if [ -f "builder/z-forge.py" ]; then
    echo "✅ builder/z-forge.py exists"
else
    echo "❌ builder/z-forge.py missing"
fi

# Check GPG bypass
echo
echo "GPG bypass module:"
if [ -f "builder/modules/gpg_bypass.py" ]; then
    echo "✅ GPG bypass module available"
else
    echo "❌ GPG bypass module missing"
fi

# Check isolinux
echo
echo "BIOS boot support:"
if [ -f "/usr/lib/ISOLINUX/isolinux.bin" ]; then
    echo "✅ isolinux installed on host"
else
    echo "⚠️  isolinux not installed on host (will be installed in chroot)"
fi

# Show available modules
echo
echo "Available build modules:"
ls builder/modules/*.py 2>/dev/null | wc -l | xargs -I {} echo "Found {} Python modules"

# Check disk space
echo
echo "Disk space check:"
df -h /tmp | grep -v Filesystem

# Summary
echo
echo "=== Build Commands ==="
echo
echo "Default Universal auto-detect build:"
echo "  sudo python3 builder/z-forge.py"
echo "  (or: sudo python3 builder/z-forge.py --build-spec build_spec.yml)"
echo
echo "Hardware-specific builds:"
echo "  sudo python3 builder/z-forge.py --build-spec config/t30/t30_build_spec.yml"
echo "  sudo python3 builder/z-forge.py --build-spec build_spec_r730xd.yml"
echo
echo "To resume a build:"
echo "  sudo python3 builder/z-forge.py --resume"
echo
echo "=== Ready to Build ==="
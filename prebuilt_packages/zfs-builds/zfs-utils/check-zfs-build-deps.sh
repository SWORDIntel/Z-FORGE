#!/bin/bash
# Check ZFS build dependencies and common issues

echo "=== Checking ZFS Build Dependencies ==="

# Check kernel headers
echo -n "Kernel headers: "
if [ -d "/lib/modules/$(uname -r)/build" ]; then
    echo "✓ Found"
else
    echo "✗ Missing - install linux-headers-$(uname -r)"
fi

# Check Python version
echo -n "Python version: "
python3 --version

# Check Python modules
echo "Python modules:"
for module in setuptools cffi packaging distlib; do
    echo -n "  $module: "
    python3 -c "import $module; print('✓ Found')" 2>/dev/null || echo "✗ Missing"
done

# Check build tools
echo "Build tools:"
for tool in gcc make autoconf automake libtool pkg-config; do
    echo -n "  $tool: "
    which $tool >/dev/null && echo "✓ Found" || echo "✗ Missing"
done

# Check libraries
echo "Required libraries:"
for lib in blkid uuid udev ssl z aio attr elf ffi; do
    echo -n "  lib$lib: "
    pkg-config --exists lib$lib 2>/dev/null && echo "✓ Found" || \
        (ldconfig -p | grep -q "lib$lib" && echo "✓ Found" || echo "✗ Missing")
done

# Check for existing ZFS
echo ""
echo "Current ZFS status:"
if command -v zfs >/dev/null; then
    echo "ZFS command: $(which zfs)"
    echo "Version: $(zfs --version 2>/dev/null || echo 'error getting version')"
else
    echo "ZFS not currently installed"
fi

# Suggest fix
echo ""
echo "=== Suggested Installation Command ==="
echo "sudo apt install -y \\"
echo "  build-essential autoconf automake libtool gawk alien fakeroot dkms \\"
echo "  libblkid-dev uuid-dev libudev-dev libssl-dev zlib1g-dev libaio-dev \\"
echo "  libattr1-dev libelf-dev linux-headers-$(uname -r) python3-all-dev \\"
echo "  python3-cffi libffi-dev python3-setuptools python3-packaging \\"
echo "  python3-distlib debhelper pkg-config libcurl4-openssl-dev"
#!/bin/bash
# Diagnose why packages are failing to install in chroot

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

echo "═══════════════════════════════════════════════════════════════════"
echo "              Diagnosing Package Installation Failures"
echo "═══════════════════════════════════════════════════════════════════"

if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

echo "[1/6] Checking chroot environment..."
echo "Chroot path: $CHROOT_PATH"
echo "Contents of /etc/:"
ls -la "$CHROOT_PATH/etc/" | head -10

echo ""
echo "[2/6] Checking APT sources..."
echo "=== /etc/apt/sources.list ==="
if [ -f "$CHROOT_PATH/etc/apt/sources.list" ]; then
    cat "$CHROOT_PATH/etc/apt/sources.list"
else
    echo "ERROR: sources.list not found!"
fi

echo ""
echo "=== /etc/apt/sources.list.d/ ==="
ls -la "$CHROOT_PATH/etc/apt/sources.list.d/" 2>/dev/null || echo "No sources.list.d directory"

echo ""
echo "[3/6] Testing APT update..."
if chroot "$CHROOT_PATH" apt-get update; then
    echo "✅ APT update successful"
else
    echo "❌ APT update failed!"
fi

echo ""
echo "[4/6] Checking package availability..."
TEST_PACKAGES=(
    "systemd"
    "bash" 
    "coreutils"
    "util-linux"
    "live-boot"
)

for pkg in "${TEST_PACKAGES[@]}"; do
    echo -n "Checking $pkg... "
    if chroot "$CHROOT_PATH" apt-cache show "$pkg" >/dev/null 2>&1; then
        VERSION=$(chroot "$CHROOT_PATH" apt-cache show "$pkg" | grep "^Version:" | head -1)
        echo "✅ Available - $VERSION"
    else
        echo "❌ NOT FOUND"
    fi
done

echo ""
echo "[5/6] Testing actual package installation..."
echo "Trying to install bash (should already be installed)..."
if chroot "$CHROOT_PATH" apt-get install -y bash; then
    echo "✅ Package installation works"
else
    echo "❌ Package installation fails"
    echo "Error output:"
    chroot "$CHROOT_PATH" apt-get install -y bash 2>&1 || true
fi

echo ""
echo "[6/6] Checking for common issues..."

# Check if dpkg is in a bad state
if [ -f "$CHROOT_PATH/var/lib/dpkg/status" ]; then
    echo "✅ dpkg status file exists"
else
    echo "❌ dpkg status file missing!"
fi

# Check if essential packages are broken
echo ""
echo "Checking essential packages status:"
chroot "$CHROOT_PATH" dpkg -l | grep -E "^[^i].*essential" || echo "No broken essential packages"

# Check disk space
echo ""
echo "Disk space in chroot:"
df -h "$CHROOT_PATH"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Diagnosis Complete"
echo "═══════════════════════════════════════════════════════════════════"
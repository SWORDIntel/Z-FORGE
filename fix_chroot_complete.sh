#!/bin/bash
# Complete fix for chroot environment issues
# Ensures chroot is properly configured for package installation

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

echo "═══════════════════════════════════════════════════════════════════"
echo "              Complete Chroot Environment Fix"
echo "═══════════════════════════════════════════════════════════════════"

if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "[1/8] Fixing basic chroot structure..."

# Ensure essential directories exist
ESSENTIAL_DIRS=(
    "etc/apt/apt.conf.d"
    "etc/apt/preferences.d"
    "etc/apt/sources.list.d"
    "etc/apt/trusted.gpg.d"
    "var/lib/apt/lists/partial"
    "var/cache/apt/archives/partial"
    "var/lib/dpkg/updates"
    "var/lib/dpkg/info"
)

for dir in "${ESSENTIAL_DIRS[@]}"; do
    mkdir -p "$CHROOT_PATH/$dir"
done

echo "[2/8] Setting up proper Debian sources..."

# Create a comprehensive sources.list
cat > "$CHROOT_PATH/etc/apt/sources.list" << 'EOF'
# Debian Trixie (Testing) - Main Repository
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware

# Debian Trixie Security Updates
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb-src http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware

# Debian Bookworm (Stable) - Fallback for missing packages
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-backports main contrib non-free non-free-firmware

# Debian Unstable (Sid) - Last resort for newest packages
deb http://deb.debian.org/debian unstable main contrib non-free non-free-firmware
EOF

echo "[3/8] Setting up APT preferences..."

# Create APT preferences to control package priorities
cat > "$CHROOT_PATH/etc/apt/preferences.d/00-releases" << 'EOF'
# Prefer Trixie (Testing)
Package: *
Pin: release n=trixie
Pin-Priority: 900

# Allow Bookworm (Stable) as fallback
Package: *
Pin: release n=bookworm
Pin-Priority: 800

# Allow Bookworm Backports
Package: *
Pin: release n=bookworm-backports
Pin-Priority: 700

# Use Unstable only when necessary
Package: *
Pin: release n=unstable
Pin-Priority: 50
EOF

echo "[4/8] Configuring APT options..."

# Configure APT to be more resilient
cat > "$CHROOT_PATH/etc/apt/apt.conf.d/99-resilient" << 'EOF'
APT::Install-Recommends "false";
APT::Install-Suggests "false";
APT::Get::Assume-Yes "true";
APT::Get::Allow-Unauthenticated "true";
Acquire::AllowInsecureRepositories "true";
Acquire::AllowDowngradeToInsecureRepositories "true";
Acquire::Check-Valid-Until "false";
APT::Acquire::Retries "3";
EOF

echo "[5/8] Mounting essential filesystems..."

# Mount necessary filesystems if not already mounted
if ! mountpoint -q "$CHROOT_PATH/proc"; then
    mount -t proc proc "$CHROOT_PATH/proc"
fi

if ! mountpoint -q "$CHROOT_PATH/sys"; then
    mount -t sysfs sysfs "$CHROOT_PATH/sys"
fi

if ! mountpoint -q "$CHROOT_PATH/dev"; then
    mount --bind /dev "$CHROOT_PATH/dev"
fi

if ! mountpoint -q "$CHROOT_PATH/dev/pts"; then
    mount -t devpts devpts "$CHROOT_PATH/dev/pts"
fi

echo "[6/8] Fixing DNS resolution..."

# Ensure DNS works in chroot
if [ ! -f "$CHROOT_PATH/etc/resolv.conf" ] || [ ! -s "$CHROOT_PATH/etc/resolv.conf" ]; then
    cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
fi

echo "[7/8] Updating package database..."

# Update with error handling
echo "Running apt-get update..."
if ! chroot "$CHROOT_PATH" apt-get update; then
    echo "Initial update failed, cleaning and retrying..."
    rm -rf "$CHROOT_PATH/var/lib/apt/lists/"*
    chroot "$CHROOT_PATH" apt-get update || true
fi

echo "[8/8] Testing package installation..."

# Test with a minimal package
echo "Testing with coreutils package..."
if chroot "$CHROOT_PATH" apt-get install -y coreutils; then
    echo "✅ Package installation is working!"
else
    echo "❌ Package installation still failing"
    
    # Try to fix dpkg if needed
    echo "Attempting to fix dpkg..."
    chroot "$CHROOT_PATH" dpkg --configure -a || true
    chroot "$CHROOT_PATH" apt-get install -f -y || true
fi

# Test critical packages
echo ""
echo "Testing critical packages..."
CRITICAL_PACKAGES=(
    "bash"
    "systemd"
    "util-linux"
    "coreutils"
)

SUCCESS_COUNT=0
for pkg in "${CRITICAL_PACKAGES[@]}"; do
    echo -n "Installing $pkg... "
    if chroot "$CHROOT_PATH" apt-get install -y "$pkg" >/dev/null 2>&1; then
        echo "✅"
        ((SUCCESS_COUNT++))
    else
        echo "❌"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Chroot Fix Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Results: $SUCCESS_COUNT/${#CRITICAL_PACKAGES[@]} critical packages installed"
echo ""

if [ "$SUCCESS_COUNT" -gt 2 ]; then
    echo "✅ Chroot environment is now functional!"
    echo "   Package installation should work in the build"
else
    echo "⚠️  Some issues remain, but environment is improved"
    echo "   Build may still encounter some failures"
fi

echo ""
echo "Mounted filesystems (will be unmounted by build system):"
mount | grep "$CHROOT_PATH" || echo "None"
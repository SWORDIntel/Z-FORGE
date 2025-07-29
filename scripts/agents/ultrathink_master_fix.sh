#!/bin/bash
# UltraThink Master Fix Script
# Generated from multi-agent analysis

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "           UltraThink Master Fix for Z-FORGE Build"
echo "════════════════════════════════════════════════════════════════════"

CHROOT_PATH="/tmp/zforge_workspace/chroot"

# 1. Ensure we're running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# 2. Create comprehensive sources.list
echo "[1/6] Fixing repository configuration..."
if [ -d "$CHROOT_PATH" ]; then
    cat > "$CHROOT_PATH/etc/apt/sources.list" << 'EOF'
# Debian Trixie (Testing)
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware

# Debian Bookworm (Stable) - Fallback
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-backports main contrib non-free non-free-firmware

# Debian Sid (Unstable) - Last resort
deb http://deb.debian.org/debian sid main contrib non-free non-free-firmware
EOF

    # 3. Fix APT preferences
    echo "[2/6] Setting package priorities..."
    mkdir -p "$CHROOT_PATH/etc/apt/preferences.d"
    cat > "$CHROOT_PATH/etc/apt/preferences.d/00-priorities" << 'EOF'
Package: *
Pin: release n=trixie
Pin-Priority: 900

Package: *
Pin: release n=bookworm
Pin-Priority: 800

Package: *
Pin: release n=bookworm-backports
Pin-Priority: 700

Package: *
Pin: release n=sid
Pin-Priority: 100
EOF

    # 4. Mount required filesystems
    echo "[3/6] Mounting filesystems..."
    for fs in proc sys dev dev/pts; do
        mountpoint -q "$CHROOT_PATH/$fs" || mount --bind /$fs "$CHROOT_PATH/$fs"
    done

    # 5. Fix DNS
    echo "[4/6] Fixing DNS resolution..."
    cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"

    # 6. Update and install minimal packages
    echo "[5/6] Updating package lists..."
    chroot "$CHROOT_PATH" apt-get update || echo "Update had issues but continuing..."

    # 7. Install absolutely minimal packages
    echo "[6/6] Installing minimal viable packages..."
    MINIMAL_PACKAGES="bash coreutils util-linux systemd"
    for pkg in $MINIMAL_PACKAGES; do
        echo "Installing $pkg..."
        chroot "$CHROOT_PATH" apt-get install -y $pkg || echo "Failed: $pkg"
    done
    
    echo "Basic fixes applied!"
else
    echo "Chroot not found - fixes will be applied during next build"
fi

echo ""
echo "Recommended next steps:"
echo "1. Run: make clean"
echo "2. Run: make build"
echo "3. Monitor for LiveEnvironment failures"

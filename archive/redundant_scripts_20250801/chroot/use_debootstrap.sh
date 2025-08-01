#!/bin/bash
# Use debootstrap to create minimal chroot with essential packages
# This is the most reliable method

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "           Creating chroot using debootstrap"
echo "═══════════════════════════════════════════════════════════════════"

CHROOT_PATH="${CHROOT_PATH:-/home/john/zforge_workspace/chroot}"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

echo "[1/4] Preparing workspace..."
mkdir -p "$(dirname "$CHROOT_PATH")"

# Backup existing chroot if it exists
if [ -d "$CHROOT_PATH" ]; then
    echo "Backing up existing chroot..."
    mv "$CHROOT_PATH" "${CHROOT_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
fi

echo ""
echo "[2/4] Running debootstrap (this may take a few minutes)..."
echo "Target: Debian Trixie (testing)"
echo "Variant: minbase (minimal installation)"
echo ""

# Run debootstrap with minimal variant
debootstrap \
    --variant=minbase \
    --include=systemd,systemd-sysv,udev,kmod,live-boot,live-config,squashfs-tools,e2fsprogs \
    trixie \
    "$CHROOT_PATH" \
    http://deb.debian.org/debian

echo ""
echo "[3/4] Configuring chroot environment..."

# Mount necessary filesystems
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
    fi
done

# Configure apt sources
cat > "$CHROOT_PATH/etc/apt/sources.list" << EOF
deb http://deb.debian.org/debian trixie main contrib non-free-firmware
deb http://deb.debian.org/debian trixie-updates main contrib non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free-firmware

# Backports for additional packages if needed
deb http://deb.debian.org/debian trixie-backports main contrib non-free-firmware
EOF

# Update package cache in chroot
chroot "$CHROOT_PATH" apt-get update

echo ""
echo "[4/4] Installing additional essential packages..."

# Install additional packages for live system
chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    util-linux \
    procps \
    mount \
    grub-common \
    grub-pc-bin \
    grub-efi-amd64-bin \
    dosfstools \
    xorriso \
    isolinux \
    syslinux-common \
    live-boot-initramfs-tools \
    live-config-systemd \
    linux-image-amd64 \
    firmware-linux-free \
    || true

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                  Debootstrap Complete!"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Chroot created at: $CHROOT_PATH"
echo ""
echo "The chroot now contains:"
echo "- Minimal Debian Trixie system"
echo "- systemd and essential tools"
echo "- live-boot and live-config"
echo "- Package management tools"
echo ""
echo "Next steps:"
echo "1. Continue with 'make build' to complete the ISO"
echo "2. The build system can now install additional packages"
echo ""
echo "To enter the chroot manually:"
echo "  sudo chroot $CHROOT_PATH /bin/bash"
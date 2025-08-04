#!/bin/bash
# Fix live environment package installation issues

CHROOT_PATH="$HOME/zforge_workspace/chroot"

echo "Fixing live environment setup..."

# 1. Fix APT sources
echo "Updating APT sources..."
cat > "$CHROOT_PATH/etc/apt/sources.list" << EOF
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
EOF

# 2. Create GPG bypass config
echo "Creating GPG bypass config..."
cat > "$CHROOT_PATH/etc/apt/apt.conf.d/99-no-check-gpg" << EOF
APT::Get::AllowUnauthenticated "true";
Acquire::AllowInsecureRepositories "true";
Acquire::AllowDowngradeToInsecureRepositories "true";
Acquire::Check-Valid-Until "false";
APT::Acquire::Retries "3";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
EOF

# 3. Fix DNS resolution
echo "Setting up DNS..."
cat > "$CHROOT_PATH/etc/resolv.conf" << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
EOF

# 4. Mount necessary filesystems
echo "Mounting filesystems..."
mount -t proc proc "$CHROOT_PATH/proc" 2>/dev/null || true
mount -t sysfs sys "$CHROOT_PATH/sys" 2>/dev/null || true
mount -t devtmpfs udev "$CHROOT_PATH/dev" 2>/dev/null || true
mount -t devpts devpts "$CHROOT_PATH/dev/pts" 2>/dev/null || true

# 5. Update package lists
echo "Updating package lists..."
chroot "$CHROOT_PATH" apt-get update

# 6. Install critical packages first
echo "Installing critical packages..."
chroot "$CHROOT_PATH" apt-get install -y --no-install-recommends \
    systemd \
    systemd-sysv \
    live-boot \
    live-config \
    live-config-systemd

echo "Fix applied. You can now re-run the build."
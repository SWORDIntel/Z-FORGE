#!/bin/bash
# Bootstrap a clean Trixie workspace for Z-FORGE

set -e  # Exit on error

echo "=== Z-FORGE Trixie Bootstrap Script ==="
echo "This will create a clean Debian Trixie chroot environment"
echo

# Configuration
WORKSPACE="${1:-$HOME/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"
DEBIAN_RELEASE="trixie"
DEBIAN_MIRROR="http://deb.debian.org/debian"
ARCH="amd64"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Configuration:${NC}"
echo "  Workspace: $WORKSPACE"
echo "  Chroot: $CHROOT_PATH"
echo "  Release: $DEBIAN_RELEASE"
echo "  Mirror: $DEBIAN_MIRROR"
echo "  Architecture: $ARCH"
echo

# Step 1: Create workspace
echo -e "${GREEN}Step 1: Creating workspace...${NC}"
mkdir -p "$WORKSPACE"/{logs,cache,iso,tmp}
mkdir -p "$CHROOT_PATH"

# Step 2: Run debootstrap
echo -e "${GREEN}Step 2: Running debootstrap for Trixie...${NC}"
echo "This will download and install a minimal Debian Trixie system"

sudo debootstrap \
    --arch="$ARCH" \
    --variant=minbase \
    --components=main,contrib,non-free,non-free-firmware \
    --include=apt-utils,ca-certificates \
    "$DEBIAN_RELEASE" \
    "$CHROOT_PATH" \
    "$DEBIAN_MIRROR"

# Step 3: Configure APT sources
echo -e "${GREEN}Step 3: Configuring APT sources...${NC}"
cat << EOF | sudo tee "$CHROOT_PATH/etc/apt/sources.list"
# Debian Trixie (testing) repositories
deb $DEBIAN_MIRROR $DEBIAN_RELEASE main contrib non-free non-free-firmware
deb $DEBIAN_MIRROR $DEBIAN_RELEASE-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security $DEBIAN_RELEASE-security main contrib non-free non-free-firmware

# Source packages (optional)
# deb-src $DEBIAN_MIRROR $DEBIAN_RELEASE main contrib non-free non-free-firmware
EOF

# Step 4: Basic chroot setup
echo -e "${GREEN}Step 4: Setting up basic chroot environment...${NC}"

# Mount proc, sys, dev
sudo mount -t proc proc "$CHROOT_PATH/proc" || true
sudo mount -t sysfs sys "$CHROOT_PATH/sys" || true
sudo mount -o bind /dev "$CHROOT_PATH/dev" || true
sudo mount -o bind /dev/pts "$CHROOT_PATH/dev/pts" || true

# Step 5: Update package lists
echo -e "${GREEN}Step 5: Updating package lists in chroot...${NC}"
sudo chroot "$CHROOT_PATH" apt-get update

# Step 6: Install essential packages
echo -e "${GREEN}Step 6: Installing essential packages...${NC}"
sudo chroot "$CHROOT_PATH" apt-get install -y \
    systemd \
    systemd-sysv \
    locales \
    console-setup \
    keyboard-configuration \
    tzdata

# Step 7: Configure locale
echo -e "${GREEN}Step 7: Configuring locale...${NC}"
echo "en_US.UTF-8 UTF-8" | sudo tee "$CHROOT_PATH/etc/locale.gen"
sudo chroot "$CHROOT_PATH" locale-gen
echo "LANG=en_US.UTF-8" | sudo tee "$CHROOT_PATH/etc/default/locale"

# Step 8: Verify installation
echo -e "${GREEN}Step 8: Verifying Trixie installation...${NC}"
echo -n "Debian version: "
sudo cat "$CHROOT_PATH/etc/debian_version"
echo -n "Kernel target: "
sudo chroot "$CHROOT_PATH" apt-cache search "^linux-image-.*-amd64$" | head -1

# Step 9: Create cleanup script
cat << 'CLEANUP_EOF' > "$WORKSPACE/cleanup_chroot.sh"
#!/bin/bash
# Cleanup chroot mounts
CHROOT_PATH="$1"
echo "Cleaning up chroot mounts..."
sudo umount "$CHROOT_PATH/dev/pts" 2>/dev/null || true
sudo umount "$CHROOT_PATH/dev" 2>/dev/null || true
sudo umount "$CHROOT_PATH/sys" 2>/dev/null || true
sudo umount "$CHROOT_PATH/proc" 2>/dev/null || true
echo "Cleanup complete"
CLEANUP_EOF
chmod +x "$WORKSPACE/cleanup_chroot.sh"

echo
echo -e "${GREEN}=== Bootstrap Complete! ===${NC}"
echo
echo "Workspace created at: $WORKSPACE"
echo "Chroot environment at: $CHROOT_PATH"
echo
echo "You can now:"
echo "1. Enter the chroot: sudo chroot $CHROOT_PATH"
echo "2. Install additional packages"
echo "3. Run the Z-FORGE build modules"
echo
echo "To cleanup mounts later, run: $WORKSPACE/cleanup_chroot.sh $CHROOT_PATH"
echo
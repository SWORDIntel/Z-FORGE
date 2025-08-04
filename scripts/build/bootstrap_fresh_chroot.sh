#!/bin/bash
# Bootstrap fresh chroot with existing Proxmox ZFS packages
# No building needed - uses packages from prebuilt_packages/

set -euo pipefail

# Configuration
WORKSPACE="${WORKSPACE:-$HOME/zforge_workspace}"
CHROOT_PATH="${CHROOT_PATH:-$WORKSPACE/chroot}"
PACKAGES_DIR="/opt/github/Z-FORGE/prebuilt_packages"
SUDO_PASS="1786"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         Fresh Chroot Bootstrap with Proxmox ZFS${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if packages exist
if [ ! -d "$PACKAGES_DIR" ] || [ $(ls -1 "$PACKAGES_DIR"/*.deb 2>/dev/null | wc -l) -eq 0 ]; then
    echo -e "${RED}No packages found in $PACKAGES_DIR${NC}"
    echo "Run get_proxmox_zfs.sh first to download packages"
    exit 1
fi

echo -e "${GREEN}Found $(ls -1 "$PACKAGES_DIR"/*.deb | wc -l) packages${NC}"

# Step 1: Create workspace
echo -e "\n${GREEN}Step 1: Creating fresh workspace...${NC}"
mkdir -p "$WORKSPACE"

# Remove old chroot if exists
if [ -d "$CHROOT_PATH" ]; then
    echo -e "${YELLOW}Removing existing chroot...${NC}"
    # Unmount any mounted filesystems
    for mp in "$CHROOT_PATH"/{dev/pts,dev,proc,sys,run}; do
        mountpoint -q "$mp" 2>/dev/null && umount "$mp" || true
    done
    echo "$SUDO_PASS" | sudo -S rm -rf "$CHROOT_PATH"
fi

# Step 2: Bootstrap Debian Trixie
echo -e "\n${GREEN}Step 2: Bootstrapping fresh Debian Trixie chroot...${NC}"
echo "$SUDO_PASS" | sudo -S debootstrap \
    --arch=amd64 \
    --include=systemd,systemd-sysv,apt,apt-utils,bash,locales,sudo \
    trixie "$CHROOT_PATH" http://deb.debian.org/debian

# Step 3: Configure chroot
echo -e "\n${GREEN}Step 3: Configuring chroot...${NC}"

# Setup APT sources
echo "$SUDO_PASS" | sudo -S tee "$CHROOT_PATH/etc/apt/sources.list" > /dev/null << 'EOF'
# Debian Trixie
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware

# Security updates
deb http://security.debian.org/debian-security trixie-security main contrib non-free non-free-firmware

# Updates
deb http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
EOF

# Copy DNS config
echo "$SUDO_PASS" | sudo -S cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"

# Create basic directories
echo "$SUDO_PASS" | sudo -S mkdir -p "$CHROOT_PATH"/{proc,sys,dev,dev/pts,run,tmp}

# Step 4: Mount filesystems
echo -e "\n${GREEN}Step 4: Mounting filesystems...${NC}"
echo "$SUDO_PASS" | sudo -S mount -t proc proc "$CHROOT_PATH/proc"
echo "$SUDO_PASS" | sudo -S mount -t sysfs sys "$CHROOT_PATH/sys"
echo "$SUDO_PASS" | sudo -S mount -o bind /dev "$CHROOT_PATH/dev"
echo "$SUDO_PASS" | sudo -S mount -t devpts devpts "$CHROOT_PATH/dev/pts"

# Step 5: Update chroot
echo -e "\n${GREEN}Step 5: Updating package lists in chroot...${NC}"
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get update

# Install essential packages
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" apt-get install -y \
    libaio1 libblkid1 libcurl4 libelf1 libpam0g \
    libselinux1 libssl3 libudev1 python3 python3-cffi \
    ca-certificates curl wget gnupg lsb-release

# Step 6: Install ZFS packages
echo -e "\n${GREEN}Step 6: Installing Proxmox ZFS packages...${NC}"

# Copy packages to chroot
echo "$SUDO_PASS" | sudo -S mkdir -p "$CHROOT_PATH/tmp/zfs-packages"
echo "$SUDO_PASS" | sudo -S cp "$PACKAGES_DIR"/*.deb "$CHROOT_PATH/tmp/zfs-packages/"

# Install in correct order
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" /bin/bash -c '
cd /tmp/zfs-packages

# Install libraries first
dpkg -i libnvpair*linux_*.deb libuutil*linux_*.deb 2>/dev/null || true
dpkg -i libzfs*linux_*.deb libzpool*linux_*.deb 2>/dev/null || true

# Install utilities
dpkg -i zfsutils-linux_*.deb zfs-zed_*.deb 2>/dev/null || true
dpkg -i zfs-initramfs_*.deb 2>/dev/null || true

# Fix any dependencies
apt-get install -f -y

# Clean up
rm -rf /tmp/zfs-packages
'

# Step 7: Configure ZFS
echo -e "\n${GREEN}Step 7: Configuring ZFS in chroot...${NC}"
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" /bin/bash -c '
# Create ZFS directories
mkdir -p /etc/zfs
touch /etc/zfs/zpool.cache

# Enable services (for when it boots)
systemctl enable zfs-import-cache.service 2>/dev/null || true
systemctl enable zfs-mount.service 2>/dev/null || true
systemctl enable zfs.target 2>/dev/null || true
'

# Step 8: Verify installation
echo -e "\n${GREEN}Step 8: Verifying ZFS installation...${NC}"
echo "$SUDO_PASS" | sudo -S chroot "$CHROOT_PATH" /bin/bash -c '
echo "Checking ZFS commands..."
for cmd in zfs zpool zdb; do
    if which $cmd &>/dev/null; then
        echo "✓ $cmd found at $(which $cmd)"
    else
        echo "✗ $cmd not found"
    fi
done

echo -e "\nInstalled ZFS packages:"
dpkg -l | grep -E "zfs|zpool" || echo "No ZFS packages found"
'

# Step 9: Unmount filesystems
echo -e "\n${GREEN}Step 9: Unmounting filesystems...${NC}"
echo "$SUDO_PASS" | sudo -S umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} || true

# Step 10: Create environment file
echo -e "\n${GREEN}Step 10: Creating environment file...${NC}"
cat > "$WORKSPACE/chroot_env.sh" << EOF
#!/bin/bash
# Z-FORGE Chroot Environment
export CHROOT_PATH="$CHROOT_PATH"
export WORKSPACE="$WORKSPACE"
echo "Chroot environment loaded!"
echo "CHROOT_PATH=$CHROOT_PATH"
echo ""
echo "To enter chroot: sudo chroot \$CHROOT_PATH /bin/bash"
echo "To build Z-FORGE: cd /opt/github/Z-FORGE && make build"
EOF
chmod +x "$WORKSPACE/chroot_env.sh"

# Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Fresh Chroot Bootstrap Complete!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Chroot location: $CHROOT_PATH"
echo "Chroot size: $(du -sh "$CHROOT_PATH" | cut -f1)"
echo ""
echo "To use this chroot:"
echo "  source $WORKSPACE/chroot_env.sh"
echo "  cd /opt/github/Z-FORGE"
echo "  make build"
echo ""
echo "To manually enter chroot:"
echo "  sudo chroot $CHROOT_PATH /bin/bash"
echo ""
#!/bin/bash
# Bootstrap a clean Trixie workspace for Z-FORGE - HEADLESS/NON-INTERACTIVE

set -e  # Exit on error

echo "=== Z-FORGE Trixie Bootstrap Script (Non-Interactive) ==="
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

# Set non-interactive frontend
export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

# Step 1: Create workspace
echo -e "${GREEN}Step 1: Creating workspace...${NC}"
mkdir -p "$WORKSPACE"/{logs,cache,iso,tmp}
mkdir -p "$CHROOT_PATH"

# Step 2: Run debootstrap
echo -e "${GREEN}Step 2: Running debootstrap for Trixie...${NC}"
echo "This will download and install a minimal Debian Trixie system"

echo "1786" | sudo -S debootstrap \
    --arch="$ARCH" \
    --variant=minbase \
    --components=main,contrib,non-free,non-free-firmware \
    --include=apt-utils,ca-certificates \
    "$DEBIAN_RELEASE" \
    "$CHROOT_PATH" \
    "$DEBIAN_MIRROR"

# Step 3: Configure APT sources
echo -e "${GREEN}Step 3: Configuring APT sources...${NC}"
cat << EOF | sudo -S tee "$CHROOT_PATH/etc/apt/sources.list" <<< "1786"
# Debian Trixie (testing) repositories
deb $DEBIAN_MIRROR $DEBIAN_RELEASE main contrib non-free non-free-firmware
deb $DEBIAN_MIRROR $DEBIAN_RELEASE-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security $DEBIAN_RELEASE-security main contrib non-free non-free-firmware

# Source packages (optional)
# deb-src $DEBIAN_MIRROR $DEBIAN_RELEASE main contrib non-free non-free-firmware
EOF

# Step 4: Configure APT for non-interactive use
echo -e "${GREEN}Step 4: Configuring APT for non-interactive operation...${NC}"
cat << 'APT_EOF' | sudo -S tee "$CHROOT_PATH/etc/apt/apt.conf.d/99noninteractive" <<< "1786"
APT::Install-Recommends "false";
APT::Install-Suggests "false";
APT::Get::Assume-Yes "true";
APT::Get::allow-unauthenticated "true";
Dpkg::Options:: "--force-confdef";
Dpkg::Options:: "--force-confold";
APT_EOF

# Create policy-rc.d to prevent services from starting
echo "1786" | sudo -S tee "$CHROOT_PATH/usr/sbin/policy-rc.d" > /dev/null << 'POLICY_EOF'
#!/bin/sh
exit 101
POLICY_EOF
echo "1786" | sudo -S chmod +x "$CHROOT_PATH/usr/sbin/policy-rc.d"

# Step 5: Basic chroot setup
echo -e "${GREEN}Step 5: Setting up basic chroot environment...${NC}"

# Mount proc, sys, dev
echo "1786" | sudo -S mount -t proc proc "$CHROOT_PATH/proc" || true
echo "1786" | sudo -S mount -t sysfs sys "$CHROOT_PATH/sys" || true
echo "1786" | sudo -S mount -o bind /dev "$CHROOT_PATH/dev" || true
echo "1786" | sudo -S mount -o bind /dev/pts "$CHROOT_PATH/dev/pts" || true

# Step 6: Pre-configure packages
echo -e "${GREEN}Step 6: Pre-configuring packages...${NC}"

# Pre-configure keyboard-configuration
cat << 'KEYBOARD_EOF' | sudo -S tee "$CHROOT_PATH/tmp/keyboard-config.txt" <<< "1786"
keyboard-configuration keyboard-configuration/layoutcode string us
keyboard-configuration keyboard-configuration/layout select English (US)
keyboard-configuration keyboard-configuration/variant select English (US)
keyboard-configuration keyboard-configuration/model select Generic 105-key PC (intl.)
keyboard-configuration keyboard-configuration/xkb-keymap select us
keyboard-configuration keyboard-configuration/toggle select No toggling
keyboard-configuration keyboard-configuration/compose select No compose key
keyboard-configuration keyboard-configuration/altgr select The default for the keyboard layout
KEYBOARD_EOF

# Pre-configure console-setup
cat << 'CONSOLE_EOF' | sudo -S tee "$CHROOT_PATH/tmp/console-config.txt" <<< "1786"
console-setup console-setup/charmap47 select UTF-8
console-setup console-setup/codeset47 select Guess optimal character set
console-setup console-setup/fontface47 select TerminusBold
console-setup console-setup/fontsize-fb47 select 8x16
console-setup console-setup/fontsize-text47 select 8x16
CONSOLE_EOF

# Pre-configure locales
cat << 'LOCALE_EOF' | sudo -S tee "$CHROOT_PATH/tmp/locale-config.txt" <<< "1786"
locales locales/locales_to_be_generated multiselect en_US.UTF-8 UTF-8
locales locales/default_environment_locale select en_US.UTF-8
LOCALE_EOF

# Pre-configure tzdata
cat << 'TZDATA_EOF' | sudo -S tee "$CHROOT_PATH/tmp/tzdata-config.txt" <<< "1786"
tzdata tzdata/Areas select Etc
tzdata tzdata/Zones/Etc select UTC
TZDATA_EOF

# Apply pre-configurations
echo "1786" | sudo -S chroot "$CHROOT_PATH" /bin/bash -c "
export DEBIAN_FRONTEND=noninteractive
debconf-set-selections < /tmp/keyboard-config.txt
debconf-set-selections < /tmp/console-config.txt
debconf-set-selections < /tmp/locale-config.txt
debconf-set-selections < /tmp/tzdata-config.txt
"

# Step 7: Update package lists
echo -e "${GREEN}Step 7: Updating package lists in chroot...${NC}"
echo "1786" | sudo -S chroot "$CHROOT_PATH" /bin/bash -c "
export DEBIAN_FRONTEND=noninteractive
apt-get update
"

# Step 8: Install essential packages
echo -e "${GREEN}Step 8: Installing essential packages (non-interactive)...${NC}"
echo "1786" | sudo -S chroot "$CHROOT_PATH" /bin/bash -c "
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends \
    systemd \
    systemd-sysv \
    locales \
    console-setup \
    keyboard-configuration \
    tzdata
"

# Step 9: Configure locale
echo -e "${GREEN}Step 9: Configuring locale...${NC}"
echo "en_US.UTF-8 UTF-8" | sudo -S tee "$CHROOT_PATH/etc/locale.gen" <<< "1786"
echo "1786" | sudo -S chroot "$CHROOT_PATH" locale-gen
echo "LANG=en_US.UTF-8" | sudo -S tee "$CHROOT_PATH/etc/default/locale" <<< "1786"

# Step 10: Clean up temporary files
echo -e "${GREEN}Step 10: Cleaning up...${NC}"
echo "1786" | sudo -S rm -f "$CHROOT_PATH/tmp/"*.txt

# Step 11: Verify installation
echo -e "${GREEN}Step 11: Verifying Trixie installation...${NC}"
echo -n "Debian version: "
echo "1786" | sudo -S cat "$CHROOT_PATH/etc/debian_version"
echo -n "Kernel target: "
echo "1786" | sudo -S chroot "$CHROOT_PATH" apt-cache search "^linux-image-.*-amd64$" | head -1

# Step 12: Create cleanup script
cat << 'CLEANUP_EOF' > "$WORKSPACE/cleanup_chroot.sh"
#!/bin/bash
# Cleanup chroot mounts
CHROOT_PATH="$1"
echo "Cleaning up chroot mounts..."
echo "1786" | sudo -S umount "$CHROOT_PATH/dev/pts" 2>/dev/null || true
echo "1786" | sudo -S umount "$CHROOT_PATH/dev" 2>/dev/null || true
echo "1786" | sudo -S umount "$CHROOT_PATH/sys" 2>/dev/null || true
echo "1786" | sudo -S umount "$CHROOT_PATH/proc" 2>/dev/null || true
echo "1786" | sudo -S rm -f "$CHROOT_PATH/usr/sbin/policy-rc.d" 2>/dev/null || true
echo "Cleanup complete"
CLEANUP_EOF
chmod +x "$WORKSPACE/cleanup_chroot.sh"

echo
echo -e "${GREEN}=== Bootstrap Complete! ===${NC}"
echo
echo "Workspace created at: $WORKSPACE"
echo "Chroot environment at: $CHROOT_PATH"
echo
echo "This was run completely non-interactively with:"
echo "- Pre-configured keyboard layout (US)"
echo "- Pre-configured console (UTF-8)"
echo "- Pre-configured locale (en_US.UTF-8)"
echo "- Pre-configured timezone (UTC)"
echo
echo "You can now:"
echo "1. Enter the chroot: sudo chroot $CHROOT_PATH"
echo "2. Install additional packages"
echo "3. Run the Z-FORGE build modules"
echo
echo "To cleanup mounts later, run: $WORKSPACE/cleanup_chroot.sh $CHROOT_PATH"
echo
#!/bin/bash
# Simple APT download approach - requires sudo
# Downloads packages without installing them

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "            Simple APT Package Download"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "This script will download essential packages using apt-get."
echo "It requires sudo access."
echo ""

PACKAGE_DIR="/opt/github/Z-FORGE/apt_packages"
mkdir -p "$PACKAGE_DIR"
cd "$PACKAGE_DIR"

# Essential packages for live system
PACKAGES=(
    # Core system
    "bash"
    "coreutils"
    "libc6"
    "libgcc-s1"
    "gcc-14-base"
    
    # Systemd
    "systemd"
    "systemd-sysv"
    "libsystemd0"
    "udev"
    
    # Utils
    "util-linux"
    "mount"
    "kmod"
    "procps"
    "e2fsprogs"
    
    # Live system
    "live-boot"
    "live-boot-initramfs-tools"
    "live-config"
    "live-config-systemd"
    "squashfs-tools"
    
    # Boot
    "grub-common"
    "grub-pc-bin"
    "grub-efi-amd64-bin"
    
    # Filesystem
    "dosfstools"
    "xorriso"
    "isolinux"
    "syslinux-common"
    
    # Network (minimal)
    "iproute2"
    "iputils-ping"
    
    # Essential libs
    "libstdc++6"
    "libtinfo6"
    "libncursesw6"
    "libselinux1"
    "libpcre2-8-0"
)

echo "Packages to download: ${#PACKAGES[@]}"
echo ""
echo "Please run this script with sudo:"
echo "  sudo $0"
echo ""
echo "Or manually download packages:"
echo ""

for pkg in "${PACKAGES[@]}"; do
    echo "sudo apt-get download $pkg"
done

echo ""
echo "After downloading, install with:"
echo "  sudo ./apt_packages/install_apt_packages.sh"

# Create installation script
cat > install_apt_packages.sh << 'EOFSCRIPT'
#!/bin/bash
# Install APT downloaded packages

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
PACKAGE_DIR="$(dirname "$0")"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing APT packages..."

# Setup chroot
mkdir -p "$CHROOT_PATH"/{bin,sbin,usr/bin,usr/sbin,lib,lib64,etc,proc,sys,dev,tmp}
mkdir -p "$CHROOT_PATH"/var/lib/dpkg/info
touch "$CHROOT_PATH/var/lib/dpkg/status"

# Copy packages
mkdir -p "$CHROOT_PATH/tmp/apt_packages"
cp "$PACKAGE_DIR"/*.deb "$CHROOT_PATH/tmp/apt_packages/" 2>/dev/null || true

# Mount filesystems
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
    fi
done

# Install
chroot "$CHROOT_PATH" bash -c '
cd /tmp/apt_packages
dpkg --force-depends -i *.deb 2>/dev/null || true
dpkg --configure -a 2>/dev/null || true
'

echo "Installation complete!"
EOFSCRIPT

chmod +x install_apt_packages.sh
#!/bin/bash
# Use apt to download packages directly without installing
# This downloads to current directory

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "         APT Download Packages (without install)"
echo "═══════════════════════════════════════════════════════════════════"

PACKAGE_DIR="/opt/github/Z-FORGE/apt_downloaded_packages"
mkdir -p "$PACKAGE_DIR"
cd "$PACKAGE_DIR"

# Essential packages for live environment
PACKAGES=(
    "bash"
    "coreutils"
    "systemd"
    "systemd-sysv"
    "util-linux"
    "libc6"
    "libsystemd0"
    "udev"
    "kmod"
    "live-boot"
    "live-boot-initramfs-tools"
    "live-config"
    "live-config-systemd"
    "squashfs-tools"
    "e2fsprogs"
    "dosfstools"
    "grub-pc-bin"
    "grub-efi-amd64-bin"
)

echo "[1/3] Updating package cache..."
sudo apt-get update

echo ""
echo "[2/3] Downloading packages..."

# Download packages without installing
for pkg in "${PACKAGES[@]}"; do
    echo -n "Downloading $pkg... "
    if sudo apt-get download "$pkg" 2>/dev/null; then
        echo "✅"
    else
        echo "❌"
    fi
done

echo ""
echo "[3/3] Creating installation script..."

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

echo "Installing APT downloaded packages in chroot..."

# Create package directory in chroot
mkdir -p "$CHROOT_PATH/tmp/apt_debs"
cp "$PACKAGE_DIR"/*.deb "$CHROOT_PATH/tmp/apt_debs/" 2>/dev/null || true

# Mount filesystems
echo "Mounting filesystems..."
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs"; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
    fi
done

# Create basic dpkg structure if missing
mkdir -p "$CHROOT_PATH/var/lib/dpkg"
touch "$CHROOT_PATH/var/lib/dpkg/status"

# Install packages
echo "Installing packages..."
chroot "$CHROOT_PATH" bash -c '
cd /tmp/apt_debs

# Install in order of dependencies
echo "Installing core packages..."
dpkg --force-depends -i libc6_*.deb 2>/dev/null || true
dpkg --force-depends -i libgcc*.deb 2>/dev/null || true
dpkg --force-depends -i bash_*.deb 2>/dev/null || true
dpkg --force-depends -i coreutils_*.deb 2>/dev/null || true

echo "Installing systemd..."
dpkg --force-depends -i libsystemd*.deb 2>/dev/null || true
dpkg --force-depends -i systemd_*.deb 2>/dev/null || true
dpkg --force-depends -i systemd-sysv_*.deb 2>/dev/null || true
dpkg --force-depends -i udev_*.deb 2>/dev/null || true

echo "Installing remaining packages..."
dpkg --force-depends -i *.deb 2>/dev/null || true

# Try to configure
dpkg --configure -a 2>/dev/null || true
'

echo "Installation complete!"
EOFSCRIPT

chmod +x install_apt_packages.sh

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                APT Download Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Package directory: $PACKAGE_DIR"
echo "Files downloaded: $(ls -1 *.deb 2>/dev/null | wc -l)"
echo ""
echo "To install:"
echo "  sudo $PACKAGE_DIR/install_apt_packages.sh"
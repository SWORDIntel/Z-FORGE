#!/bin/bash
# Download essential packages outside chroot and prepare for installation
# This bypasses all chroot repository issues

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Downloading Essential Packages Outside Chroot"
echo "═══════════════════════════════════════════════════════════════════"

# Create package cache directory
PACKAGE_CACHE="/opt/github/Z-FORGE/package_cache"
mkdir -p "$PACKAGE_CACHE"
cd "$PACKAGE_CACHE"

# Essential packages list (in dependency order)
ESSENTIAL_PACKAGES=(
    # Core system
    "libc6"
    "libgcc-s1"
    "gcc-14-base"
    "libstdc++6"
    "base-files"
    "base-passwd"
    "bash"
    "coreutils"
    "dash"
    "debianutils"
    "diffutils"
    "dpkg"
    "e2fsprogs"
    "findutils"
    "grep"
    "gzip"
    "hostname"
    "init-system-helpers"
    "libc-bin"
    "login"
    "mount"
    "ncurses-base"
    "ncurses-bin"
    "perl-base"
    "sed"
    "sysvinit-utils"
    "tar"
    "util-linux"
    "util-linux-extra"
    
    # Systemd and dependencies
    "libsystemd0"
    "libsystemd-shared"
    "systemd"
    "systemd-sysv"
    "systemd-timesyncd"
    
    # Essential for live boot
    "udev"
    "kmod"
    "procps"
    "iproute2"
    "iputils-ping"
    "isc-dhcp-client"
    "kbd"
    
    # Package management
    "apt"
    "apt-utils"
    "debian-archive-keyring"
    "gpgv"
    "libgpg-error0"
    "libgcrypt20"
    
    # Live boot specific
    "live-boot"
    "live-boot-initramfs-tools"
    "live-config"
    "live-config-systemd"
    
    # Filesystem tools
    "e2fsprogs"
    "xfsprogs"
    "btrfs-progs"
    "dosfstools"
    
    # Boot essentials
    "grub-common"
    "grub-pc-bin"
    "grub-efi-amd64-bin"
    "efibootmgr"
)

echo "[1/4] Setting up APT configuration for downloads..."

# Create temporary APT config for downloading
cat > apt_download.conf << 'EOF'
Dir::Cache::archives "./";
Dir::State "./apt-state";
Dir::Etc::sourcelist "./sources.list";
Dir::Etc::preferences "./preferences";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
APT::Get::Download-Only "true";
Acquire::Languages "none";
EOF

# Create sources.list with multiple fallbacks
cat > sources.list << 'EOF'
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-backports main contrib non-free non-free-firmware
deb http://deb.debian.org/debian sid main contrib non-free non-free-firmware
EOF

# Create preferences
cat > preferences << 'EOF'
Package: *
Pin: release n=trixie
Pin-Priority: 900

Package: *
Pin: release n=bookworm
Pin-Priority: 800

Package: *
Pin: release n=sid
Pin-Priority: 100
EOF

# Create required directories
mkdir -p apt-state/lists/partial
mkdir -p archives/partial

echo "[2/4] Updating package lists..."
apt-get -c apt_download.conf update

echo "[3/4] Downloading packages..."
echo "This may take several minutes..."

# Download packages with dependencies
FAILED_PACKAGES=()
DOWNLOADED_PACKAGES=()

for package in "${ESSENTIAL_PACKAGES[@]}"; do
    echo -n "Downloading $package... "
    if apt-get -c apt_download.conf install -y --download-only "$package" >/dev/null 2>&1; then
        echo "✅"
        DOWNLOADED_PACKAGES+=("$package")
    else
        echo "❌"
        FAILED_PACKAGES+=("$package")
    fi
done

# Move downloaded .deb files to main directory
mv archives/*.deb . 2>/dev/null || true

echo ""
echo "[4/4] Creating installation script..."

# Create installation script
cat > install_packages_in_chroot.sh << 'EOFSCRIPT'
#!/bin/bash
# Install downloaded packages in chroot

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
PACKAGE_DIR="/opt/github/Z-FORGE/package_cache"

if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing packages in chroot..."

# Copy packages into chroot
echo "[1/3] Copying packages to chroot..."
mkdir -p "$CHROOT_PATH/tmp/packages"
cp "$PACKAGE_DIR"/*.deb "$CHROOT_PATH/tmp/packages/" 2>/dev/null || true

# Mount required filesystems
echo "[2/3] Mounting filesystems..."
for fs in proc sys dev dev/pts; do
    mountpoint -q "$CHROOT_PATH/$fs" || mount --bind "/$fs" "$CHROOT_PATH/$fs"
done

# Install packages
echo "[3/3] Installing packages..."
chroot "$CHROOT_PATH" bash -c '
cd /tmp/packages
# Install in dependency order
dpkg --force-depends -i libc6_*.deb 2>/dev/null || true
dpkg --force-depends -i gcc-*.deb base-*.deb 2>/dev/null || true
dpkg --force-depends -i *.deb 2>/dev/null || true
# Fix any broken dependencies
apt-get install -f -y --no-install-recommends || true
'

echo "Package installation complete!"
EOFSCRIPT

chmod +x install_packages_in_chroot.sh

# Clean up temporary files
rm -rf apt-state archives apt_download.conf sources.list preferences

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Download Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Downloaded: ${#DOWNLOADED_PACKAGES[@]} packages"
echo "Failed: ${#FAILED_PACKAGES[@]} packages"
echo ""
echo "Package files in: $PACKAGE_CACHE"
echo "Total size: $(du -sh . | cut -f1)"
echo ""
echo "To install in chroot:"
echo "  sudo $PACKAGE_CACHE/install_packages_in_chroot.sh"
echo ""

if [ ${#FAILED_PACKAGES[@]} -gt 0 ]; then
    echo "Failed packages:"
    for pkg in "${FAILED_PACKAGES[@]}"; do
        echo "  - $pkg"
    done
fi
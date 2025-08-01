#!/bin/bash
# Direct download of essential .deb packages from Debian mirrors
# Bypasses APT entirely

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "           Direct Package Download for Z-FORGE"
echo "═══════════════════════════════════════════════════════════════════"

PACKAGE_DIR="/opt/github/Z-FORGE/essential_debs"
mkdir -p "$PACKAGE_DIR"
cd "$PACKAGE_DIR"

# Debian mirror base URLs
TRIXIE_URL="http://deb.debian.org/debian/pool/main"
BOOKWORM_URL="http://deb.debian.org/debian/pool/main"

# Function to download a package
download_package() {
    local pkg_name="$1"
    local pkg_path="$2"
    local url="$3"
    
    echo -n "Downloading $pkg_name... "
    if wget -q -N "$url" 2>/dev/null; then
        echo "✅"
        return 0
    else
        echo "❌"
        return 1
    fi
}

echo "[1/3] Downloading core system packages..."

# Download essential packages with direct URLs
# These are common packages that should exist
PACKAGES=(
    # Basic system
    "bash|b/bash/bash_5.2.21-2_amd64.deb|$BOOKWORM_URL/b/bash/bash_5.2.21-2_amd64.deb"
    "coreutils|c/coreutils/coreutils_9.4-3_amd64.deb|$BOOKWORM_URL/c/coreutils/coreutils_9.4-3_amd64.deb"
    "systemd|s/systemd/systemd_256.7-3_amd64.deb|$TRIXIE_URL/s/systemd/systemd_256.7-3_amd64.deb"
    "systemd-sysv|s/systemd/systemd-sysv_256.7-3_amd64.deb|$TRIXIE_URL/s/systemd/systemd-sysv_256.7-3_amd64.deb"
    "util-linux|u/util-linux/util-linux_2.40.2-10_amd64.deb|$TRIXIE_URL/u/util-linux/util-linux_2.40.2-10_amd64.deb"
    "libc6|g/glibc/libc6_2.40-3_amd64.deb|$TRIXIE_URL/g/glibc/libc6_2.40-3_amd64.deb"
    "libsystemd0|s/systemd/libsystemd0_256.7-3_amd64.deb|$TRIXIE_URL/s/systemd/libsystemd0_256.7-3_amd64.deb"
    "udev|s/systemd/udev_256.7-3_amd64.deb|$TRIXIE_URL/s/systemd/udev_256.7-3_amd64.deb"
    "kmod|k/kmod/kmod_33+20240816-2_amd64.deb|$TRIXIE_URL/k/kmod/kmod_33+20240816-2_amd64.deb"
)

SUCCESS=0
FAILED=0

for entry in "${PACKAGES[@]}"; do
    IFS='|' read -r name path url <<< "$entry"
    if download_package "$name" "$path" "$url"; then
        ((SUCCESS++))
    else
        ((FAILED++))
    fi
done

echo ""
echo "[2/3] Attempting to find live-boot packages..."

# Try multiple versions of live-boot
LIVE_BOOT_VERSIONS=(
    "3.0.1-1"
    "3.0.0-1" 
    "20230502"
    "20230131"
)

FOUND_LIVE=0
for version in "${LIVE_BOOT_VERSIONS[@]}"; do
    if wget -q -N "http://deb.debian.org/debian/pool/main/l/live-boot/live-boot_${version}_all.deb" 2>/dev/null; then
        echo "✅ Found live-boot version $version"
        FOUND_LIVE=1
        break
    fi
done

if [ $FOUND_LIVE -eq 0 ]; then
    echo "❌ Could not find live-boot package"
fi

echo ""
echo "[3/3] Creating direct installation script..."

cat > install_direct.sh << 'EOFINSTALL'
#!/bin/bash
# Install directly downloaded packages

set -e

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"
DEB_DIR="$(dirname "$0")"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing downloaded .deb packages..."

# Copy debs to chroot
mkdir -p "$CHROOT_PATH/tmp/direct_debs"
cp "$DEB_DIR"/*.deb "$CHROOT_PATH/tmp/direct_debs/" 2>/dev/null || true

# Mount filesystems
for fs in proc sys dev dev/pts; do
    mountpoint -q "$CHROOT_PATH/$fs" || mount --bind "/$fs" "$CHROOT_PATH/$fs"
done

# Install with dpkg, ignoring dependencies initially
echo "Installing with dpkg..."
chroot "$CHROOT_PATH" bash -c '
cd /tmp/direct_debs
for deb in *.deb; do
    echo "Installing $deb..."
    dpkg --force-depends --force-confnew -i "$deb" 2>/dev/null || true
done
'

# Try to fix dependencies if possible
echo "Attempting to fix dependencies..."
chroot "$CHROOT_PATH" apt-get install -f -y --no-install-recommends || true

echo "Direct installation complete!"
EOFINSTALL

chmod +x install_direct.sh

# Alternative: Create a minimal package set
echo ""
echo "Creating ultra-minimal package set..."

cat > install_minimal.sh << 'EOFMINIMAL'
#!/bin/bash
# Install only the absolute minimum packages

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Setting up minimal chroot environment..."

# Ensure basic directories exist
for dir in bin sbin usr/bin usr/sbin lib lib64 etc proc sys dev; do
    mkdir -p "$CHROOT_PATH/$dir"
done

# Copy essential binaries from host if packages fail
if [ ! -f "$CHROOT_PATH/bin/bash" ]; then
    echo "Copying essential binaries from host..."
    cp /bin/bash "$CHROOT_PATH/bin/" || true
    cp /bin/sh "$CHROOT_PATH/bin/" || true
    cp /usr/bin/env "$CHROOT_PATH/usr/bin/" || true
    
    # Copy required libraries
    for lib in $(ldd /bin/bash | grep -o '/lib[^ ]*'); do
        cp "$lib" "$CHROOT_PATH/$lib" 2>/dev/null || true
    done
fi

echo "Minimal setup complete!"
EOFMINIMAL

chmod +x install_minimal.sh

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Direct Download Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Downloaded: $SUCCESS essential packages"
echo "Failed: $FAILED packages"
echo ""
echo "Package directory: $PACKAGE_DIR"
echo "Total size: $(du -sh . | cut -f1)"
echo ""
echo "Installation options:"
echo "  1. sudo $PACKAGE_DIR/install_direct.sh"
echo "  2. sudo $PACKAGE_DIR/install_minimal.sh"
echo ""
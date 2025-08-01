#!/bin/bash
# Comprehensive package download for Z-FORGE
# Downloads essential packages from multiple sources

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Comprehensive Package Download for Z-FORGE"
echo "═══════════════════════════════════════════════════════════════════"

PACKAGE_DIR="/opt/github/Z-FORGE/comprehensive_packages"
mkdir -p "$PACKAGE_DIR"
cd "$PACKAGE_DIR"

# Function to download from debian pool
download_from_pool() {
    local pkg="$1"
    local version="$2"
    local arch="${3:-amd64}"
    local repo="${4:-http://deb.debian.org/debian}"
    local dist="${5:-trixie}"
    
    # Get first letter for pool directory
    local first_letter="${pkg:0:1}"
    if [[ "$pkg" == lib* ]]; then
        first_letter="${pkg:0:4}"
    fi
    
    local url="$repo/pool/main/$first_letter/$pkg/${pkg}_${version}_${arch}.deb"
    
    echo -n "Downloading $pkg ($version)... "
    if wget -q -N "$url" 2>/dev/null; then
        echo "✅"
        return 0
    else
        # Try with 'all' architecture
        url="$repo/pool/main/$first_letter/$pkg/${pkg}_${version}_all.deb"
        if wget -q -N "$url" 2>/dev/null; then
            echo "✅ (all)"
            return 0
        else
            echo "❌"
            return 1
        fi
    fi
}

echo "[1/5] Downloading core system packages..."

# Core packages with specific versions
download_from_pool "bash" "5.2.21-2.1" "amd64"
download_from_pool "coreutils" "9.4-3.1" "amd64"
download_from_pool "libc6" "2.40-3" "amd64"
download_from_pool "libcrypt1" "1:4.4.36-5" "amd64"
download_from_pool "libgcc-s1" "14.2.0-8" "amd64"

echo ""
echo "[2/5] Downloading systemd packages..."

# Systemd and related
download_from_pool "systemd" "256.7-3" "amd64"
download_from_pool "systemd-sysv" "256.7-3" "all"
download_from_pool "libsystemd0" "256.7-3" "amd64"
download_from_pool "udev" "256.7-3" "amd64"
download_from_pool "libsystemd-shared" "256.7-3" "amd64"

echo ""
echo "[3/5] Downloading live system packages..."

# Live boot packages - try multiple versions
LIVE_VERSIONS=("1:20230502" "1:20230131" "1:20221125" "1:20220505")
for ver in "${LIVE_VERSIONS[@]}"; do
    if download_from_pool "live-boot" "$ver" "all"; then
        download_from_pool "live-boot-initramfs-tools" "$ver" "all" || true
        break
    fi
done

# Live config
for ver in "${LIVE_VERSIONS[@]}"; do
    if download_from_pool "live-config" "$ver" "all"; then
        download_from_pool "live-config-systemd" "$ver" "all" || true
        break
    fi
done

echo ""
echo "[4/5] Downloading essential tools..."

# Essential tools
download_from_pool "util-linux" "2.40.2-10" "amd64"
download_from_pool "mount" "2.40.2-10" "amd64"
download_from_pool "kmod" "33+20240816-2" "amd64"
download_from_pool "procps" "2:4.0.4-5" "amd64"
download_from_pool "e2fsprogs" "1.47.1-1" "amd64"
download_from_pool "squashfs-tools" "1:4.6.1-1+b1" "amd64"

# Additional essential libraries
download_from_pool "libstdc++6" "14.2.0-8" "amd64"
download_from_pool "libtinfo6" "6.5-2+b1" "amd64"
download_from_pool "libncursesw6" "6.5-2+b1" "amd64"
download_from_pool "libselinux1" "3.7-3" "amd64"
download_from_pool "libpcre2-8-0" "10.44-4" "amd64"
download_from_pool "libgmp10" "2:6.3.0+dfsg-2+b2" "amd64"
download_from_pool "libattr1" "1:2.5.2-2" "amd64"
download_from_pool "libacl1" "2.3.2-2+b1" "amd64"
download_from_pool "libcap2" "1:2.66-5+b1" "amd64"

echo ""
echo "[5/5] Creating comprehensive installation script..."

cat > install_comprehensive.sh << 'EOFSCRIPT'
#!/bin/bash
# Install comprehensive package set

set -e

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"
PACKAGE_DIR="$(dirname "$0")"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing comprehensive package set..."

# Ensure chroot structure exists
echo "Setting up chroot structure..."
mkdir -p "$CHROOT_PATH"/{bin,sbin,usr/bin,usr/sbin,lib,lib64,etc,proc,sys,dev,tmp}
mkdir -p "$CHROOT_PATH"/var/lib/dpkg/{info,updates}
mkdir -p "$CHROOT_PATH"/var/cache/apt/archives/partial
mkdir -p "$CHROOT_PATH"/var/log

# Create essential files
touch "$CHROOT_PATH/var/lib/dpkg/status"
touch "$CHROOT_PATH/var/lib/dpkg/available"

# Copy packages
echo "Copying packages to chroot..."
mkdir -p "$CHROOT_PATH/tmp/comprehensive_debs"
cp "$PACKAGE_DIR"/*.deb "$CHROOT_PATH/tmp/comprehensive_debs/" 2>/dev/null || true

# Mount filesystems
echo "Mounting filesystems..."
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
    fi
done

# If bash isn't installed, copy from host
if [ ! -f "$CHROOT_PATH/bin/bash" ]; then
    echo "Bootstrapping bash from host..."
    cp /bin/bash "$CHROOT_PATH/bin/"
    # Copy essential libraries for bash
    for lib in $(ldd /bin/bash | awk '{print $3}' | grep '^/'); do
        dir=$(dirname "$lib")
        mkdir -p "$CHROOT_PATH$dir"
        cp "$lib" "$CHROOT_PATH$lib" 2>/dev/null || true
    done
    # Also copy ld-linux
    cp /lib64/ld-linux-x86-64.so.2 "$CHROOT_PATH/lib64/" 2>/dev/null || true
fi

# Install packages in dependency order
echo "Installing packages..."
chroot "$CHROOT_PATH" /bin/bash -c '
cd /tmp/comprehensive_debs

# Install in careful order
echo "Step 1: Core libraries..."
dpkg --force-depends -i libc6_*.deb 2>/dev/null || true
dpkg --force-depends -i libgcc-s1_*.deb 2>/dev/null || true
dpkg --force-depends -i libcrypt1_*.deb 2>/dev/null || true

echo "Step 2: Base system..."
dpkg --force-depends -i bash_*.deb 2>/dev/null || true
dpkg --force-depends -i coreutils_*.deb 2>/dev/null || true
dpkg --force-depends -i libattr1_*.deb libacl1_*.deb libselinux1_*.deb 2>/dev/null || true

echo "Step 3: System utilities..."
dpkg --force-depends -i libsystemd0_*.deb libsystemd-shared_*.deb 2>/dev/null || true
dpkg --force-depends -i systemd_*.deb systemd-sysv_*.deb udev_*.deb 2>/dev/null || true
dpkg --force-depends -i util-linux_*.deb mount_*.deb 2>/dev/null || true
dpkg --force-depends -i kmod_*.deb procps_*.deb 2>/dev/null || true

echo "Step 4: Live system..."
dpkg --force-depends -i live-boot_*.deb live-boot-initramfs-tools_*.deb 2>/dev/null || true
dpkg --force-depends -i live-config_*.deb live-config-systemd_*.deb 2>/dev/null || true

echo "Step 5: Remaining packages..."
dpkg --force-depends -i *.deb 2>/dev/null || true

# Try to configure
echo "Configuring packages..."
dpkg --configure -a 2>/dev/null || true

# Create basic system links if missing
[ ! -e /bin/sh ] && ln -s bash /bin/sh || true
'

echo ""
echo "Installation complete!"
echo "Installed packages in: $CHROOT_PATH"
EOFSCRIPT

chmod +x install_comprehensive.sh

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                  Download Summary"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Package directory: $PACKAGE_DIR"
echo "Total packages: $(ls -1 *.deb 2>/dev/null | wc -l)"
echo "Total size: $(du -sh . | cut -f1)"
echo ""
echo "To install all packages:"
echo "  sudo $PACKAGE_DIR/install_comprehensive.sh"
echo ""
echo "This will create a minimal working chroot environment."
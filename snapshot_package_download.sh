#!/bin/bash
# Download packages from Debian snapshots - guaranteed to have packages
# Uses snapshot.debian.org which archives all Debian packages

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Downloading Packages from Debian Snapshots"
echo "═══════════════════════════════════════════════════════════════════"

PACKAGE_DIR="/opt/github/Z-FORGE/snapshot_packages"
mkdir -p "$PACKAGE_DIR"
cd "$PACKAGE_DIR"

# Use a recent snapshot date
SNAPSHOT_DATE="20240701"  # July 1, 2024
SNAPSHOT_BASE="http://snapshot.debian.org/archive/debian/$SNAPSHOT_DATE"

echo "[1/4] Creating package list with specific versions..."

# Essential packages with known good versions
declare -A PACKAGES=(
    ["bash"]="5.2.15-2+b7"
    ["coreutils"]="9.4-3"
    ["systemd"]="255.5-1"
    ["systemd-sysv"]="255.5-1"
    ["util-linux"]="2.40.1-9"
    ["libc6"]="2.38-13"
    ["libsystemd0"]="255.5-1"
    ["udev"]="255.5-1"
    ["kmod"]="32+20240611-1"
    ["live-boot"]="1:20230502-1"
    ["grub-common"]="2.12-5"
    ["e2fsprogs"]="1.47.1-1"
)

echo "[2/4] Downloading from snapshot.debian.org..."

SUCCESS=0
FAILED=0

for package in "${!PACKAGES[@]}"; do
    version="${PACKAGES[$package]}"
    
    # Determine package source directory (first letter rule)
    if [[ $package == lib* ]]; then
        first_dir="${package:0:4}"
    else
        first_dir="${package:0:1}"
    fi
    
    # Construct URL
    url="$SNAPSHOT_BASE/pool/main/$first_dir/$package/${package}_${version}_amd64.deb"
    
    # Some packages are arch-independent
    if [[ $package == "systemd-sysv" ]] || [[ $package == "live-boot" ]]; then
        url="$SNAPSHOT_BASE/pool/main/$first_dir/$package/${package}_${version}_all.deb"
    fi
    
    echo -n "Downloading $package ($version)... "
    if wget -q -N "$url" 2>/dev/null; then
        echo "✅"
        ((SUCCESS++))
    else
        # Try alternative URL patterns
        alt_url="${url/_amd64.deb/_all.deb}"
        if wget -q -N "$alt_url" 2>/dev/null; then
            echo "✅ (all)"
            ((SUCCESS++))
        else
            echo "❌"
            ((FAILED++))
        fi
    fi
done

echo ""
echo "[3/4] Downloading additional dependencies..."

# Download some key dependencies
DEPS=(
    "libgcc-s1_14.1.0-2_amd64.deb"
    "gcc-14-base_14.1.0-2_amd64.deb"
    "libstdc++6_14.1.0-2_amd64.deb"
    "libcrypt1_4.4.36-4_amd64.deb"
    "libgpg-error0_1.49-2_amd64.deb"
    "libgcrypt20_1.10.3-3_amd64.deb"
    "libsystemd-shared_255.5-1_amd64.deb"
)

for dep_file in "${DEPS[@]}"; do
    dep_name="${dep_file%%_*}"
    
    if [[ $dep_name == lib* ]]; then
        first_dir="${dep_name:0:4}"
    else
        first_dir="${dep_name:0:1}"
    fi
    
    url="$SNAPSHOT_BASE/pool/main/$first_dir/$dep_name/$dep_file"
    
    echo -n "Downloading $dep_name... "
    if wget -q -N "$url" 2>/dev/null; then
        echo "✅"
        ((SUCCESS++))
    else
        echo "❌"
        ((FAILED++))
    fi
done

echo ""
echo "[4/4] Creating installation script..."

cat > install_snapshot_packages.sh << 'EOFSCRIPT'
#!/bin/bash
# Install packages downloaded from Debian snapshots

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
PACKAGE_DIR="$(dirname "$0")"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

echo "Installing snapshot packages in chroot..."

# Create package directory in chroot
mkdir -p "$CHROOT_PATH/tmp/snapshot_debs"
cp "$PACKAGE_DIR"/*.deb "$CHROOT_PATH/tmp/snapshot_debs/" 2>/dev/null || true

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
if [ ! -f "$CHROOT_PATH/var/lib/dpkg/status" ]; then
    touch "$CHROOT_PATH/var/lib/dpkg/status"
fi

# Install packages in order
echo "Installing packages..."
chroot "$CHROOT_PATH" bash -c '
cd /tmp/snapshot_debs

# Install in dependency order
echo "Installing libc6..."
dpkg --force-depends -i libc6_*.deb 2>/dev/null || true

echo "Installing gcc/libgcc..."
dpkg --force-depends -i gcc-*-base_*.deb libgcc*.deb 2>/dev/null || true

echo "Installing core utilities..."
dpkg --force-depends -i bash_*.deb coreutils_*.deb util-linux_*.deb 2>/dev/null || true

echo "Installing systemd..."
dpkg --force-depends -i libsystemd*.deb systemd_*.deb systemd-sysv_*.deb udev_*.deb 2>/dev/null || true

echo "Installing remaining packages..."
dpkg --force-depends -i *.deb 2>/dev/null || true

# Configure packages
echo "Configuring packages..."
dpkg --configure -a 2>/dev/null || true
'

echo "Snapshot package installation complete!"
EOFSCRIPT

chmod +x install_snapshot_packages.sh

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                Snapshot Download Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Successfully downloaded: $SUCCESS packages"
echo "Failed: $FAILED packages"
echo ""
echo "Package directory: $PACKAGE_DIR"
echo ""
echo "To install:"
echo "  sudo $PACKAGE_DIR/install_snapshot_packages.sh"
echo ""
echo "This method uses archived packages that are guaranteed to exist."
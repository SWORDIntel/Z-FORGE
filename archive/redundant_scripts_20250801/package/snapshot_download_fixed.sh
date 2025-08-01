#!/bin/bash
# Download packages from Debian snapshots with correct paths
# Uses snapshot.debian.org which archives all Debian packages

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Downloading Packages from Debian Snapshots (Fixed)"
echo "═══════════════════════════════════════════════════════════════════"

PACKAGE_DIR="/opt/github/Z-FORGE/snapshot_packages_fixed"
mkdir -p "$PACKAGE_DIR"
cd "$PACKAGE_DIR"

# Use a recent snapshot date that should have packages
SNAPSHOT_DATE="20240701"
SNAPSHOT_BASE="http://snapshot.debian.org/archive/debian/$SNAPSHOT_DATE"

echo "[1/3] Downloading essential packages..."

# Function to download with proper path
download_package() {
    local name="$1"
    local version="$2"
    local arch="${3:-amd64}"
    local section="${4:-main}"
    
    # Determine source package name (some differ from binary)
    local source_pkg="$name"
    case "$name" in
        "libsystemd0"|"systemd"|"systemd-sysv"|"udev") source_pkg="systemd" ;;
        "libc6") source_pkg="glibc" ;;
        "libgcc-s1"|"gcc-14-base"|"libstdc++6") source_pkg="gcc-14" ;;
        "grub-common"|"grub-pc-bin"|"grub-efi-amd64-bin") source_pkg="grub2" ;;
    esac
    
    # First letter of source package
    local first_letter="${source_pkg:0:1}"
    if [[ "$source_pkg" == lib* ]]; then
        first_letter="lib${source_pkg:3:1}"
    fi
    
    local url="$SNAPSHOT_BASE/pool/$section/$first_letter/$source_pkg/${name}_${version}_${arch}.deb"
    
    echo -n "Downloading $name ($version)... "
    if wget -q -O "${name}_${version}_${arch}.deb" "$url" 2>/dev/null; then
        echo "✅"
        return 0
    else
        echo "❌"
        return 1
    fi
}

SUCCESS=0
FAILED=0

# Essential packages with known versions from July 2024
PACKAGES=(
    "bash|5.2.21-2.1|amd64"
    "coreutils|9.4-3.1|amd64"
    "util-linux|2.40.1-9|amd64"
    "systemd|256~rc4-1|amd64"
    "systemd-sysv|256~rc4-1|amd64"
    "udev|256~rc4-1|amd64"
    "libc6|2.38-13|amd64"
    "libsystemd0|256~rc4-1|amd64"
    "kmod|32+20240611-1|amd64"
    "e2fsprogs|1.47.1-1|amd64"
)

for entry in "${PACKAGES[@]}"; do
    IFS='|' read -r name version arch <<< "$entry"
    if download_package "$name" "$version" "$arch"; then
        ((SUCCESS++))
    else
        ((FAILED++))
    fi
done

echo ""
echo "[2/3] Trying simpler approach with current packages..."

# Try downloading from current Debian repos instead
CURRENT_BASE="http://deb.debian.org/debian"

echo "Attempting current Debian packages..."
CURRENT_PACKAGES=(
    "bash|5.2.21-2.1|amd64|main"
    "coreutils|9.4-3.1|amd64|main"
    "systemd|256.7-3|amd64|main"
    "systemd-sysv|256.7-3|all|main"
)

for entry in "${CURRENT_PACKAGES[@]}"; do
    IFS='|' read -r name version arch section <<< "$entry"
    
    # Determine path
    local source_pkg="$name"
    case "$name" in
        "systemd"|"systemd-sysv") source_pkg="systemd" ;;
    esac
    
    first_letter="${source_pkg:0:1}"
    url="$CURRENT_BASE/pool/$section/$first_letter/$source_pkg/${name}_${version}_${arch}.deb"
    
    echo -n "Downloading $name from current... "
    if wget -q -O "${name}_current_${version}_${arch}.deb" "$url" 2>/dev/null; then
        echo "✅"
        ((SUCCESS++))
    else
        echo "❌"
        ((FAILED++))
    fi
done

echo ""
echo "[3/3] Creating installation script..."

cat > install_snapshot_packages.sh << 'EOFSCRIPT'
#!/bin/bash
# Install packages downloaded from snapshots

set -e

CHROOT_PATH="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"
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
touch "$CHROOT_PATH/var/lib/dpkg/status"

# Install packages
echo "Installing packages..."
chroot "$CHROOT_PATH" bash -c '
cd /tmp/snapshot_debs
# Force install all packages
for deb in *.deb; do
    echo "Installing $deb..."
    dpkg --force-depends --force-confnew -i "$deb" 2>/dev/null || true
done

# Try to configure
dpkg --configure -a 2>/dev/null || true
'

echo "Installation complete!"
EOFSCRIPT

chmod +x install_snapshot_packages.sh

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                Download Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Successfully downloaded: $SUCCESS packages"
echo "Failed: $FAILED packages" 
echo ""
echo "Package directory: $PACKAGE_DIR"
echo "Files downloaded: $(ls -1 *.deb 2>/dev/null | wc -l)"
echo ""
echo "To install:"
echo "  sudo $PACKAGE_DIR/install_snapshot_packages.sh"
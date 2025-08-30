#!/bin/bash
# Z-FORGE Quick ZFS Prebuilt Package Creator
# Builds ZFS 2.3.4 userspace packages on Ubuntu for Debian/Proxmox
# This is the simplified version - userspace only (usually sufficient)

set -euo pipefail

ZFS_VERSION="2.3.4"
BUILD_DIR="./zfs-build-temp"
OUTPUT_DIR="./prebuilt_packages/zfs-${ZFS_VERSION}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Z-FORGE ZFS ${ZFS_VERSION} Prebuilt Package Builder${NC}"
echo "================================================"
echo ""
echo "This script builds ZFS userspace packages on Ubuntu"
echo "for use in Debian-based Z-FORGE ISOs."
echo ""

# Check dependencies
echo "Checking dependencies..."
MISSING_DEPS=""
for pkg in build-essential autoconf automake libtool \
           libblkid-dev libssl-dev libudev-dev zlib1g-dev \
           uuid-dev libattr1-dev libelf-dev python3-all-dev \
           python3-cffi python3-setuptools python3-packaging; do
    if ! dpkg -l | grep -q "^ii.*$pkg"; then
        MISSING_DEPS="$MISSING_DEPS $pkg"
    fi
done

if [ -n "$MISSING_DEPS" ]; then
    echo -e "${YELLOW}Missing dependencies:${MISSING_DEPS}${NC}"
    echo "Install with: sudo apt-get install${MISSING_DEPS}"
    exit 1
fi

# Create directories
mkdir -p "${BUILD_DIR}"
mkdir -p "${OUTPUT_DIR}"

# Download ZFS source
cd "${BUILD_DIR}"
if [ ! -f "zfs-${ZFS_VERSION}.tar.gz" ]; then
    echo "Downloading ZFS ${ZFS_VERSION}..."
    wget "https://github.com/openzfs/zfs/releases/download/zfs-${ZFS_VERSION}/zfs-${ZFS_VERSION}.tar.gz"
fi

# Extract
echo "Extracting ZFS source..."
rm -rf "zfs-${ZFS_VERSION}"
tar -xzf "zfs-${ZFS_VERSION}.tar.gz"
cd "zfs-${ZFS_VERSION}"

# Configure for userspace only
echo "Configuring ZFS userspace build..."
./configure \
    --prefix=/usr \
    --with-config=user \
    --enable-systemd \
    --enable-pyzfs \
    --disable-static

# Build
echo "Building ZFS userspace (this will take a few minutes)..."
make -j$(nproc)

# Create Debian packages
echo "Creating Debian packages..."
make deb-utils

# Copy packages
echo "Copying packages to output directory..."
cd ..
cp *.deb "../../${OUTPUT_DIR}/" 2>/dev/null || true

# Create install script
cat > "../../${OUTPUT_DIR}/install.sh" <<'EOF'
#!/bin/bash
# Install ZFS userspace packages
dpkg -i *.deb || apt-get -f install -y
systemctl enable zfs.target
echo "ZFS userspace installed successfully!"
EOF
chmod +x "../../${OUTPUT_DIR}/install.sh"

# Clean up
cd ../..
rm -rf "${BUILD_DIR}"

echo ""
echo -e "${GREEN}Success!${NC} ZFS userspace packages built successfully."
echo "Packages location: ${OUTPUT_DIR}"
echo ""
echo "These packages will be automatically used by Z-FORGE build system."
echo "To build ISO with these packages:"
echo "  sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml"
#!/bin/bash
# Build ZFS with AVX-512 optimizations for Meteor Lake

set -e

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║          ZFS OPTIMIZED BUILD FOR METEOR LAKE                 ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"

# Configuration
ZFS_VERSION="${ZFS_VERSION:-2.3.3}"  # Latest stable release
BUILD_DIR="/opt/zfs-build"
INSTALL_PREFIX="/usr/local"

# Meteor Lake optimizations - P-cores have AVX-512, E-cores have AVX2
# Use AVX2 as baseline for compatibility, runtime detection will use AVX-512 on P-cores
export CFLAGS="-O3 -march=alderlake -mtune=alderlake -pipe"
export CFLAGS="$CFLAGS -mavx -mavx2 -mfma -mbmi -mbmi2"
export CFLAGS="$CFLAGS -flto=auto -fomit-frame-pointer"
export CXXFLAGS="$CFLAGS"
export LDFLAGS="-Wl,-O3 -Wl,--as-needed -flto=auto -fuse-ld=mold"

# For P-core specific builds (optional)
export PCORE_FLAGS="-mavx512f -mavx512dq -mavx512cd -mavx512bw -mavx512vl"

# Use optimized tools
export CC="ccache gcc"
export CXX="ccache g++"
export LD="mold"

echo -e "${CYAN}Build Configuration:${NC}"
echo "  CPU: Intel Meteor Lake with AVX-512"
echo "  Compiler: $CC with AVX-512"
echo "  Linker: mold (fast)"
echo "  Optimizations: -O3 with LTO"
echo ""

# Install dependencies
echo -e "${YELLOW}Installing build dependencies...${NC}"
apt-get update
apt-get install -y \
    build-essential \
    autoconf \
    automake \
    libtool \
    gawk \
    alien \
    fakeroot \
    dkms \
    libblkid-dev \
    uuid-dev \
    libudev-dev \
    libssl-dev \
    zlib1g-dev \
    libaio-dev \
    libattr1-dev \
    libelf-dev \
    python3 \
    python3-dev \
    python3-setuptools \
    python3-cffi \
    libffi-dev \
    python3-packaging \
    git \
    libcurl4-openssl-dev

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Download ZFS source
if [ ! -d "zfs-$ZFS_VERSION" ]; then
    echo -e "${CYAN}Downloading ZFS $ZFS_VERSION...${NC}"
    wget -q --show-progress "https://github.com/openzfs/zfs/releases/download/zfs-$ZFS_VERSION/zfs-$ZFS_VERSION.tar.gz"
    tar -xzf "zfs-$ZFS_VERSION.tar.gz"
fi

cd "zfs-$ZFS_VERSION"

# ZFS 2.3.3 already has runtime CPU detection for AVX-512
# It will automatically use AVX-512 on P-cores when available
echo -e "${CYAN}ZFS 2.3.3 includes runtime CPU feature detection${NC}"
echo "• AVX-512 will be used on P-cores automatically"
echo "• AVX2 will be used on E-cores"
echo "• No patches needed!"

# Configure with optimizations
echo -e "${YELLOW}Configuring ZFS build...${NC}"
./autogen.sh

./configure \
    --prefix="$INSTALL_PREFIX" \
    --with-linux="/lib/modules/$(uname -r)/build" \
    --enable-linux-builtin=no \
    --enable-systemd \
    --enable-pyzfs \
    --with-config=user \
    --with-mounthelperdir=/sbin \
    --with-udevdir=/lib/udev \
    --with-zfsexecdir=/usr/lib/zfs \
    --disable-debug \
    --enable-silent-rules

# Build with all cores (or use P-cores for better performance)
if [ -f /opt/scripts/build-with-pcores.sh ]; then
    echo -e "${CYAN}Building ZFS on P-cores for maximum performance...${NC}"
    /opt/scripts/build-with-pcores.sh make -j$(nproc) V=0
else
    echo -e "${CYAN}Building ZFS with $(nproc) cores...${NC}"
    make -j$(nproc) V=0
fi

# Create packages
echo -e "${YELLOW}Creating optimized packages...${NC}"
make deb-utils deb-kmod

# Install packages
echo -e "${GREEN}ZFS packages built successfully!${NC}"
echo -e "${CYAN}Packages location: $BUILD_DIR/zfs-$ZFS_VERSION/*.deb${NC}"

# Create installation script
cat > "$BUILD_DIR/install-zfs-optimized.sh" << 'INSTALL'
#!/bin/bash
# Install optimized ZFS packages

cd "$(dirname "$0")"

echo "Installing optimized ZFS packages..."

# Install in correct order
dpkg -i \
    zfs-dkms_*.deb \
    libnvpair3_*.deb \
    libuutil3_*.deb \
    libzfs5_*.deb \
    libzpool5_*.deb \
    zfsutils-linux_*.deb \
    zfs-zed_*.deb \
    python3-pyzfs_*.deb || apt-get -f install -y

echo "Optimized ZFS installed!"
zfs version
INSTALL
chmod +x "$BUILD_DIR/install-zfs-optimized.sh"

echo -e "${GREEN}Build complete!${NC}"
echo -e "${YELLOW}To install:${NC} $BUILD_DIR/install-zfs-optimized.sh"
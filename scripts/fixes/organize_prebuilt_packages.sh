#!/bin/bash
# Organize prebuilt packages for outside packages build

set -euo pipefail

PREBUILT_DIR="/opt/github/Z-FORGE/prebuilt_packages"

echo "=== Organizing Prebuilt Packages for Outside Build ==="

# Create directory structure
echo "Creating directory structure..."
mkdir -p "$PREBUILT_DIR/zfs"
mkdir -p "$PREBUILT_DIR/proxmox"
mkdir -p "$PREBUILT_DIR/kernel"
mkdir -p "$PREBUILT_DIR/bootloaders"
mkdir -p "$PREBUILT_DIR/calamares"

# Move ZFS packages to proper location
echo ""
echo "Organizing ZFS packages..."
cd "$PREBUILT_DIR"

# Move all ZFS 2.3.3 packages to zfs directory
for pkg in *zfs*.deb *zpool*.deb *nvpair*.deb *uutil*.deb; do
    if [ -f "$pkg" ] && [[ "$pkg" =~ 2\.3\.3 ]]; then
        echo "  Moving $pkg to zfs/"
        mv "$pkg" zfs/ 2>/dev/null || true
    fi
done

# Also check archive directory
if [ -d "/opt/github/Z-FORGE/archive/packages/live_cd_packages" ]; then
    echo "Checking archive for additional packages..."
    cd "/opt/github/Z-FORGE/archive/packages/live_cd_packages"
    for pkg in *zfs*.deb; do
        if [ -f "$pkg" ] && [[ "$pkg" =~ 2\.3\.3 ]]; then
            echo "  Copying $pkg to prebuilt/zfs/"
            cp "$pkg" "$PREBUILT_DIR/zfs/" 2>/dev/null || true
        fi
    done
fi

# Create install script for ZFS
echo ""
echo "Creating ZFS install script..."
cat > "$PREBUILT_DIR/zfs/install.sh" << 'EOF'
#!/bin/bash
# Install ZFS 2.3.3 packages in correct order

set -e

echo "Installing ZFS 2.3.3 packages..."

# Install dependencies first
apt-get update
apt-get install -y --no-install-recommends \
    libc6 \
    libblkid1 \
    libuuid1 \
    zlib1g \
    python3

# Install ZFS libraries in order
dpkg -i libuutil3*.deb || apt-get -f install -y
dpkg -i libnvpair3*.deb || apt-get -f install -y
dpkg -i libzpool5*.deb libzfs4*.deb || apt-get -f install -y

# Install ZFS utilities
dpkg -i zfsutils-linux*.deb zfs-zed*.deb || apt-get -f install -y

# Install ZFS initramfs support
dpkg -i zfs-initramfs*.deb || apt-get -f install -y

# Fix any remaining dependencies
apt-get -f install -y

echo "ZFS 2.3.3 installation complete!"
zfs --version
EOF

chmod +x "$PREBUILT_DIR/zfs/install.sh"

# Create main install script
echo ""
echo "Creating main install script..."
cat > "$PREBUILT_DIR/install_in_chroot.sh" << 'EOF'
#!/bin/bash
# Install all prebuilt packages in chroot

set -e

PACKAGES_DIR="/tmp/prebuilt_packages"

echo "=== Installing Prebuilt Packages ==="

# Install ZFS if packages exist
if [ -d "$PACKAGES_DIR/zfs" ] && [ -n "$(ls -A $PACKAGES_DIR/zfs/*.deb 2>/dev/null)" ]; then
    echo "Installing ZFS packages..."
    cd "$PACKAGES_DIR/zfs"
    if [ -x "./install.sh" ]; then
        ./install.sh
    else
        dpkg -i *.deb || apt-get -f install -y
    fi
fi

# Install Proxmox if packages exist
if [ -d "$PACKAGES_DIR/proxmox" ] && [ -n "$(ls -A $PACKAGES_DIR/proxmox/*.deb 2>/dev/null)" ]; then
    echo "Installing Proxmox packages..."
    cd "$PACKAGES_DIR/proxmox"
    dpkg -i *.deb || apt-get -f install -y
fi

# Install kernel modules if they exist
if [ -d "$PACKAGES_DIR/kernel" ] && [ -n "$(ls -A $PACKAGES_DIR/kernel/*.deb 2>/dev/null)" ]; then
    echo "Installing kernel packages..."
    cd "$PACKAGES_DIR/kernel"
    dpkg -i *.deb || apt-get -f install -y
fi

# Install bootloaders if they exist
if [ -d "$PACKAGES_DIR/bootloaders" ] && [ -n "$(ls -A $PACKAGES_DIR/bootloaders/*.deb 2>/dev/null)" ]; then
    echo "Installing bootloader packages..."
    cd "$PACKAGES_DIR/bootloaders"
    dpkg -i *.deb || apt-get -f install -y
fi

echo "=== Prebuilt package installation complete ==="
EOF

chmod +x "$PREBUILT_DIR/install_in_chroot.sh"

# Check what we have
echo ""
echo "=== Package Summary ==="
echo "ZFS packages:"
ls -la "$PREBUILT_DIR/zfs/"*.deb 2>/dev/null | wc -l
ls -la "$PREBUILT_DIR/zfs/"*.deb 2>/dev/null || echo "  No ZFS packages found"

echo ""
echo "Proxmox packages:"
ls -la "$PREBUILT_DIR/proxmox/"*.deb 2>/dev/null | wc -l
ls -la "$PREBUILT_DIR/proxmox/"*.deb 2>/dev/null || echo "  No Proxmox packages found"

echo ""
echo "To download Proxmox packages, you can:"
echo "  1. Download from Proxmox repository"
echo "  2. Build from Proxmox source"
echo "  3. Use the proxmox_full build spec instead"

echo ""
echo "=== Organization Complete ==="
echo ""
echo "The prebuilt packages are now organized."
echo "To use the outside packages build:"
echo "  ./launch-enhanced-gui.sh"
echo "  Select: 'Outside Packages Build (Fastest)'"
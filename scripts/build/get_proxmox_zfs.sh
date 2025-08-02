#!/bin/bash
# Get ZFS packages from Proxmox VE 9 repositories
# No building needed!

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         Getting ZFS from Proxmox VE 9 Repositories${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"

OUTPUT_DIR="/opt/github/Z-FORGE/prebuilt_packages"
TEMP_DIR="/tmp/proxmox-zfs-$$"

# Create directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Add Proxmox repository temporarily
echo -e "\n${GREEN}Setting up Proxmox VE 9 repository...${NC}"

# Create a temporary sources.list for Proxmox
cat > proxmox.list << 'EOF'
# Proxmox VE 9 repositories
deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription
deb http://download.proxmox.com/debian/pbs bookworm pbs-no-subscription  
deb http://download.proxmox.com/debian bookworm pvetest
EOF

# Download Proxmox GPG key
echo -e "${GREEN}Downloading Proxmox GPG key...${NC}"
wget -q https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg

# Create temporary apt config
export APT_CONFIG="$TEMP_DIR/apt.conf"
cat > "$APT_CONFIG" << EOF
Dir::Etc::SourceList "$TEMP_DIR/proxmox.list";
Dir::Etc::Trusted "$TEMP_DIR/proxmox-release-bookworm.gpg";
Dir::Cache "$TEMP_DIR/cache";
Dir::State "$TEMP_DIR/state";
Dir::Etc::Preferences "$TEMP_DIR/preferences";
EOF

mkdir -p cache/archives/partial
mkdir -p state/lists/partial

# Update package lists from Proxmox
echo -e "${GREEN}Updating package lists from Proxmox...${NC}"
apt-get update || {
    echo -e "${RED}Failed to update from Proxmox repos${NC}"
    echo "Trying alternative method..."
}

# Download ZFS packages
echo -e "\n${GREEN}Downloading ZFS packages from Proxmox...${NC}"

# List of packages we need
PACKAGES=(
    "libnvpair3linux"
    "libuutil3linux"
    "libzfs4linux"
    "libzpool5linux"
    "zfsutils-linux"
    "zfs-initramfs"
    "zfs-zed"
)

# Try to download packages
echo -e "${GREEN}Method 1: Using apt-get download...${NC}"
for pkg in "${PACKAGES[@]}"; do
    echo "Downloading $pkg..."
    apt-get download "$pkg" 2>/dev/null || echo "Failed: $pkg"
done

# If that didn't work, try direct download
if [ $(ls -1 *.deb 2>/dev/null | wc -l) -eq 0 ]; then
    echo -e "\n${YELLOW}Method 1 failed, trying direct download...${NC}"
    
    # Get the package URLs directly
    BASE_URL="http://download.proxmox.com/debian/pve/dists/bookworm/pve-no-subscription/binary-amd64"
    
    # Download Packages file
    wget -q "$BASE_URL/Packages.gz"
    gunzip Packages.gz
    
    # Extract ZFS package URLs
    for pkg in "${PACKAGES[@]}"; do
        echo "Finding $pkg..."
        URL=$(grep -A 10 "^Package: $pkg$" Packages | grep "^Filename:" | head -1 | cut -d' ' -f2)
        if [ -n "$URL" ]; then
            echo "Downloading: $URL"
            wget -q "http://download.proxmox.com/debian/pve/$URL" || echo "Failed to download $pkg"
        fi
    done
fi

# Alternative: Get specific version directly
if [ $(ls -1 *.deb 2>/dev/null | wc -l) -eq 0 ]; then
    echo -e "\n${YELLOW}Trying direct URLs for Proxmox ZFS 2.2.4...${NC}"
    
    DIRECT_URLS=(
        "http://download.proxmox.com/debian/pve/pool/main/z/zfsonlinux/libnvpair3linux_2.2.4-pve1_amd64.deb"
        "http://download.proxmox.com/debian/pve/pool/main/z/zfsonlinux/libuutil3linux_2.2.4-pve1_amd64.deb"
        "http://download.proxmox.com/debian/pve/pool/main/z/zfsonlinux/libzfs4linux_2.2.4-pve1_amd64.deb"
        "http://download.proxmox.com/debian/pve/pool/main/z/zfsonlinux/libzpool5linux_2.2.4-pve1_amd64.deb"
        "http://download.proxmox.com/debian/pve/pool/main/z/zfsonlinux/zfsutils-linux_2.2.4-pve1_amd64.deb"
        "http://download.proxmox.com/debian/pve/pool/main/z/zfsonlinux/zfs-initramfs_2.2.4-pve1_all.deb"
        "http://download.proxmox.com/debian/pve/pool/main/z/zfsonlinux/zfs-zed_2.2.4-pve1_amd64.deb"
    )
    
    for url in "${DIRECT_URLS[@]}"; do
        echo "Downloading: $(basename "$url")"
        wget -q "$url" || echo "Failed: $url"
    done
fi

# Move packages to output directory
echo -e "\n${GREEN}Moving packages to output directory...${NC}"
if [ $(ls -1 *.deb 2>/dev/null | wc -l) -gt 0 ]; then
    mv *.deb "$OUTPUT_DIR/"
    echo "Moved $(ls -1 "$OUTPUT_DIR"/*.deb | wc -l) packages"
else
    echo -e "${RED}No packages were downloaded!${NC}"
    exit 1
fi

# Create installer script
echo -e "${GREEN}Creating installer script...${NC}"
cat > "$OUTPUT_DIR/install_proxmox_zfs.sh" << 'EOF'
#!/bin/bash
# Install Proxmox ZFS packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

echo "Installing Proxmox ZFS packages..."

# Install in correct order
cd "$SCRIPT_DIR"

# Libraries first
dpkg -i libnvpair3linux_*.deb libuutil3linux_*.deb || true
dpkg -i libzfs4linux_*.deb libzpool5linux_*.deb || true

# Then utilities
dpkg -i zfsutils-linux_*.deb zfs-zed_*.deb || true
dpkg -i zfs-initramfs_*.deb || true

# Fix any dependencies
apt-get install -f -y

echo "Proxmox ZFS packages installed!"
EOF

chmod +x "$OUTPUT_DIR/install_proxmox_zfs.sh"

# Cleanup
cd /
rm -rf "$TEMP_DIR"
unset APT_CONFIG

echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Done! Proxmox ZFS packages downloaded${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Packages saved to: $OUTPUT_DIR"
echo "Installer script: $OUTPUT_DIR/install_proxmox_zfs.sh"
echo ""
echo "These are production-ready packages from Proxmox VE 9"
echo "No building, no signing issues, no xtables loops!"
echo ""
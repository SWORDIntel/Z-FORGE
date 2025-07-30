#!/bin/bash
# Fix Proxmox repository GPG key issue
# Properly adds the Proxmox signing key to the chroot

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Fixing Proxmox Repository GPG Key"
echo "═══════════════════════════════════════════════════════════════════"

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    echo "Usage: sudo $0 [chroot_path]"
    exit 1
fi

echo "Target chroot: $CHROOT_PATH"
echo ""

# Mount filesystems if needed
for fs in proc sys dev dev/pts; do
    if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
        mkdir -p "$CHROOT_PATH/$fs"
        mount --bind "/$fs" "$CHROOT_PATH/$fs"
    fi
done

echo "[1/4] Removing old repository files..."
rm -f "$CHROOT_PATH/etc/apt/sources.list.d/proxmox.list"
rm -f "$CHROOT_PATH/etc/apt/trusted.gpg.d/proxmox*"

echo ""
echo "[2/4] Adding Proxmox GPG key properly..."

# Method 1: Direct key addition
chroot "$CHROOT_PATH" bash -c '
# Install required tools
apt-get update
apt-get install -y wget gnupg apt-transport-https ca-certificates

# Create keyrings directory
mkdir -p /etc/apt/keyrings

# Download and add the key properly
wget -O- https://enterprise.proxmox.com/debian/proxmox-release-bullseye.gpg | \
    gpg --dearmor > /etc/apt/keyrings/proxmox-release-keyring.gpg

# Also try the specific key ID
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 24B30F06ECC1836A4E5EFECBA7BCD1420BFE778E || true
'

echo ""
echo "[3/4] Adding Proxmox repository with signed-by option..."

# Add repository with proper signed-by
cat > "$CHROOT_PATH/etc/apt/sources.list.d/proxmox.list" << 'EOF'
# Proxmox VE repository for Debian Trixie
deb [arch=amd64 signed-by=/etc/apt/keyrings/proxmox-release-keyring.gpg] http://download.proxmox.com/debian/pve trixie pve-no-subscription

# Alternative: Allow unsigned temporarily (NOT RECOMMENDED for production)
# deb [arch=amd64 trusted=yes] http://download.proxmox.com/debian/pve trixie pve-no-subscription
EOF

echo ""
echo "[4/4] Testing repository access..."

# Try to update
chroot "$CHROOT_PATH" bash -c '
apt-get update 2>&1 | grep -E "(proxmox|error|warning)" || true

echo ""
echo "Checking if Proxmox packages are available:"
apt-cache search proxmox-ve | head -3
'

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    GPG Key Fix Applied"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "If you still see GPG errors, you can:"
echo ""
echo "Option 1: Use unsigned repository (for testing only):"
echo "  Edit $CHROOT_PATH/etc/apt/sources.list.d/proxmox.list"
echo "  Uncomment the 'trusted=yes' line"
echo ""
echo "Option 2: Use Debian ZFS packages instead:"
echo "  apt-get install zfsutils-linux (from Debian repos)"
echo ""
echo "Option 3: Skip Proxmox for now and use after ISO boots"
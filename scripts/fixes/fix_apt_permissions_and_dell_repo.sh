#!/bin/bash
# Fix APT permissions and Dell repository issues

set -euo pipefail

echo "=== Fixing APT Permissions and Repository Issues ==="

# 1. Fix APT partial directory permissions
echo "Fixing APT permissions..."
if [ -d /var/lib/apt/lists/partial ]; then
    chown -R _apt:root /var/lib/apt/lists/partial
    chmod 755 /var/lib/apt/lists/partial
fi

# Fix the main lists directory too
if [ -d /var/lib/apt/lists ]; then
    chown -R root:root /var/lib/apt/lists
    chown -R _apt:root /var/lib/apt/lists/partial
    chmod 755 /var/lib/apt/lists
fi

# 2. Handle Dell repository issue
echo "Checking for Dell repository..."
if grep -q "linux.dell.com" /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null; then
    echo "Dell repository found. Options:"
    echo "1. Remove Dell repository (recommended for build)"
    echo "2. Add Dell GPG key"
    read -p "Choose option (1/2): " choice
    
    case $choice in
        1)
            echo "Removing Dell repository..."
            # Remove from sources.list
            sed -i '/linux\.dell\.com/d' /etc/apt/sources.list 2>/dev/null || true
            # Remove from sources.list.d
            find /etc/apt/sources.list.d/ -name "*.list" -exec sed -i '/linux\.dell\.com/d' {} \; 2>/dev/null || true
            # Remove Dell-specific list files
            rm -f /etc/apt/sources.list.d/dell*.list 2>/dev/null || true
            echo "Dell repository removed."
            ;;
        2)
            echo "Adding Dell GPG key..."
            # Create keyrings directory if it doesn't exist
            mkdir -p /usr/share/keyrings
            
            # Download Dell GPG key
            wget -qO - https://linux.dell.com/repo/pgp_pubkeys/0x1285491434D8786F.asc | \
                gpg --dearmor -o /usr/share/keyrings/dell-trusted.gpg
            
            # Update Dell repository to use the keyring
            find /etc/apt/sources.list.d/ -name "*.list" -exec sed -i \
                's|deb https://linux.dell.com|deb [signed-by=/usr/share/keyrings/dell-trusted.gpg] https://linux.dell.com|g' {} \; 2>/dev/null || true
            
            echo "Dell GPG key added."
            ;;
        *)
            echo "Invalid choice. Skipping Dell repository fix."
            ;;
    esac
fi

# 3. Clean APT cache and update
echo "Cleaning APT cache..."
apt-get clean
rm -rf /var/lib/apt/lists/*
mkdir -p /var/lib/apt/lists/partial
chown -R _apt:root /var/lib/apt/lists/partial

# 4. Update package lists
echo "Updating package lists..."
apt-get update || {
    echo "Update failed. Attempting to fix..."
    # Try without Dell repo if it still fails
    find /etc/apt/sources.list.d/ -name "*.list" -exec grep -l "dell" {} \; | xargs rm -f 2>/dev/null || true
    apt-get update
}

# 5. Fix any broken packages
echo "Fixing any broken packages..."
dpkg --configure -a || true
apt-get install -f -y || true

echo "=== APT Permissions and Repository Issues Fixed ==="

# Show current status
echo ""
echo "Current APT status:"
echo "- Partial directory owner: $(stat -c '%U:%G' /var/lib/apt/lists/partial 2>/dev/null || echo 'N/A')"
echo "- Active repositories:"
apt-cache policy | grep http | head -5

echo ""
echo "You can now proceed with the build."
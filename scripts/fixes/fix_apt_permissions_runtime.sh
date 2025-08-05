#!/bin/bash
# Fix APT permission denied errors during runtime

set -euo pipefail

echo "=== Fixing APT Permission Denied Errors ==="

# Function to fix permissions with proper ownership
fix_apt_permissions() {
    local base_path="$1"
    local desc="$2"
    
    echo "Fixing APT permissions in $desc..."
    
    # Create directories if they don't exist
    mkdir -p "$base_path/var/lib/apt/lists/partial"
    mkdir -p "$base_path/var/cache/apt/archives/partial"
    
    # Fix ownership and permissions
    # The _apt user needs to own the partial directories
    if id "_apt" >/dev/null 2>&1; then
        chown -R _apt:root "$base_path/var/lib/apt/lists/partial" 2>/dev/null || true
        chown -R _apt:root "$base_path/var/cache/apt/archives/partial" 2>/dev/null || true
    fi
    
    # Set proper permissions
    chmod 755 "$base_path/var/lib/apt/lists" 2>/dev/null || true
    chmod 755 "$base_path/var/lib/apt/lists/partial" 2>/dev/null || true
    chmod 755 "$base_path/var/cache/apt/archives" 2>/dev/null || true
    chmod 755 "$base_path/var/cache/apt/archives/partial" 2>/dev/null || true
    
    # Fix the parent directories too
    chown root:root "$base_path/var/lib/apt/lists" 2>/dev/null || true
    chown root:root "$base_path/var/cache/apt/archives" 2>/dev/null || true
    
    echo "  ✅ Fixed permissions in $desc"
}

# Fix host system permissions
echo "1. Fixing host system APT permissions..."
fix_apt_permissions "" "host system"

# Fix chroot permissions if it exists
WORKSPACE="${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
CHROOT_PATH="$WORKSPACE/chroot"

if [ -d "$CHROOT_PATH" ]; then
    echo ""
    echo "2. Fixing chroot APT permissions..."
    fix_apt_permissions "$CHROOT_PATH" "chroot"
    
    # Also fix the chroot's _apt user if it exists
    if [ -f "$CHROOT_PATH/etc/passwd" ] && grep -q "_apt" "$CHROOT_PATH/etc/passwd"; then
        echo "  Fixing chroot _apt user permissions..."
        chroot "$CHROOT_PATH" chown -R _apt:root /var/lib/apt/lists/partial 2>/dev/null || true
        chroot "$CHROOT_PATH" chown -R _apt:root /var/cache/apt/archives/partial 2>/dev/null || true
    fi
fi

# Clean APT cache to force regeneration with correct permissions
echo ""
echo "3. Cleaning APT cache..."
apt-get clean 2>/dev/null || true
if [ -d "$CHROOT_PATH" ]; then
    chroot "$CHROOT_PATH" apt-get clean 2>/dev/null || true
fi

# Test permissions
echo ""
echo "4. Testing permissions..."
if [ -d "/var/lib/apt/lists/partial" ]; then
    ls -la /var/lib/apt/lists/partial | head -1
fi

if [ -d "$CHROOT_PATH/var/lib/apt/lists/partial" ]; then
    ls -la "$CHROOT_PATH/var/lib/apt/lists/partial" | head -1
fi

echo ""
echo "=== APT Permissions Fixed ==="
echo ""
echo "The 'Download is performed unsandboxed as root' warnings should now be resolved."
echo "You can continue with your build."
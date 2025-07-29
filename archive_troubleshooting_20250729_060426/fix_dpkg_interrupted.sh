#!/bin/bash
# Fix interrupted dpkg in chroot environment

set -e

CHROOT_PATH="/tmp/zforge_workspace/chroot"

echo "=== Fixing Interrupted DPKG in Chroot ==="
echo "Chroot path: $CHROOT_PATH"

# Check if chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot directory not found at $CHROOT_PATH"
    exit 1
fi

# Step 1: Configure interrupted packages
echo ""
echo "Step 1: Running dpkg --configure -a..."
if sudo chroot "$CHROOT_PATH" dpkg --configure -a; then
    echo "Successfully configured pending packages"
else
    echo "WARNING: dpkg --configure -a encountered issues, continuing..."
fi

# Step 2: Fix any broken packages
echo ""
echo "Step 2: Fixing broken packages..."
sudo chroot "$CHROOT_PATH" apt-get update
sudo chroot "$CHROOT_PATH" apt-get install -f -y

# Step 3: Clean package cache
echo ""
echo "Step 3: Cleaning package cache..."
sudo chroot "$CHROOT_PATH" apt-get clean
sudo chroot "$CHROOT_PATH" apt-get autoclean

# Step 4: Remove any problematic lock files
echo ""
echo "Step 4: Checking for lock files..."
LOCK_FILES=(
    "$CHROOT_PATH/var/lib/dpkg/lock"
    "$CHROOT_PATH/var/lib/dpkg/lock-frontend"
    "$CHROOT_PATH/var/cache/apt/archives/lock"
    "$CHROOT_PATH/var/lib/apt/lists/lock"
)

for lock_file in "${LOCK_FILES[@]}"; do
    if [ -f "$lock_file" ]; then
        echo "Removing lock file: $lock_file"
        sudo rm -f "$lock_file"
    fi
done

# Step 5: Update package database
echo ""
echo "Step 5: Updating package database..."
sudo chroot "$CHROOT_PATH" apt-get update

# Check dpkg status
echo ""
echo "=== DPKG Status ==="
echo "Checking for broken packages..."
if sudo chroot "$CHROOT_PATH" dpkg -l | grep -E '^[^ii]' | grep -v '^Desired' | grep -v '^|' | grep -v '^++'; then
    echo "WARNING: Some packages may still have issues"
else
    echo "All packages appear to be properly configured"
fi

echo ""
echo "=== DPKG fix completed! ==="
echo "You can now proceed with package installation."
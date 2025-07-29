#!/bin/bash
# Nuclear option for kernel installation - handles all edge cases

set +e  # Continue on errors

CHROOT="/tmp/zforge_workspace/chroot"
LOG_FILE="/opt/github/Z-FORGE/nuclear_kernel_$(date +%Y%m%d_%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         NUCLEAR KERNEL FIX PROTOCOL          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo

log "Starting nuclear kernel fix protocol"
log "Target: Force install Trixie kernel 6.12.x"

# Step 1: Diagnose current state
echo -e "${YELLOW}Phase 1: Current State Analysis${NC}"
log "=== Current State Analysis ==="

echo "Checking what kernel APT wants to install..."
POLICY_OUTPUT=$(sudo chroot "$CHROOT" apt-cache policy linux-image-amd64 2>&1)
echo "$POLICY_OUTPUT" | head -10
echo "$POLICY_OUTPUT" | head -10 >> "$LOG_FILE"

echo
echo "Available 6.x kernels:"
AVAILABLE_KERNELS=$(sudo chroot "$CHROOT" apt-cache search "^linux-image-6\." 2>/dev/null | grep -v "dbg\|cloud\|rt" | sort -V)
echo "$AVAILABLE_KERNELS"
echo "$AVAILABLE_KERNELS" >> "$LOG_FILE"

# Step 2: Nuclear APT cleanup
echo
echo -e "${YELLOW}Phase 2: Nuclear APT Cleanup${NC}"
log "=== Nuclear APT Cleanup ==="

# Kill everything
log "Killing all package management processes..."
sudo killall -9 apt apt-get dpkg apt-cache 2>/dev/null || true
sleep 2

# Remove ALL lock files
log "Removing ALL lock files..."
sudo find "$CHROOT" -name "*lock*" -type f -delete 2>/dev/null || true

# Nuclear APT cache clear
log "Nuclear APT cache clear..."
sudo rm -rf "$CHROOT/var/lib/apt/lists"/*
sudo rm -rf "$CHROOT/var/cache/apt"/*
sudo rm -rf "$CHROOT/var/log/apt"/*

# Rebuild APT directories
log "Rebuilding APT directories..."
sudo mkdir -p "$CHROOT/var/lib/apt/lists"
sudo mkdir -p "$CHROOT/var/cache/apt/archives"
sudo mkdir -p "$CHROOT/var/log/apt"

# Step 3: Force update with timeout
echo
echo -e "${YELLOW}Phase 3: Force APT Update${NC}"
log "=== Force APT Update ==="

# Update with timeout and retry
for attempt in 1 2 3; do
    log "APT update attempt $attempt..."
    if timeout 300 sudo chroot "$CHROOT" apt-get update 2>&1 | tee -a "$LOG_FILE"; then
        log "APT update successful"
        break
    else
        log "APT update attempt $attempt failed, retrying..."
        sleep 5
    fi
done

# Step 4: Nuclear kernel removal
echo
echo -e "${YELLOW}Phase 4: Nuclear Old Kernel Removal${NC}"
log "=== Nuclear Old Kernel Removal ==="

# Remove ALL old kernels aggressively
OLD_KERNELS=$(sudo chroot "$CHROOT" dpkg -l 2>/dev/null | grep '^ii.*linux-image' | grep -v '6\.12\|6\.1[3-9]\|6\.[2-9]' | awk '{print $2}')
if [ -n "$OLD_KERNELS" ]; then
    log "Force removing old kernels: $OLD_KERNELS"
    echo "$OLD_KERNELS" | xargs -r sudo chroot "$CHROOT" dpkg --force-depends --purge 2>&1 | tee -a "$LOG_FILE" || true
    
    # Clean up any remaining files
    sudo chroot "$CHROOT" apt-get autoremove -y 2>&1 | tee -a "$LOG_FILE" || true
fi

# Step 5: Force install kernel with multiple methods
echo
echo -e "${YELLOW}Phase 5: Nuclear Kernel Installation${NC}"
log "=== Nuclear Kernel Installation ==="

KERNEL_INSTALLED=false

# Method 1: Force install specific 6.12 kernel
echo -e "${BLUE}Method 1: Specific 6.12.38 kernel${NC}"
log "Attempting specific 6.12.38 kernel installation..."
if sudo chroot "$CHROOT" apt-get install -y --no-install-recommends \
    --allow-downgrades --allow-remove-essential --allow-change-held-packages \
    linux-image-6.12.38+deb13-amd64 \
    linux-headers-6.12.38+deb13-amd64 2>&1 | tee -a "$LOG_FILE"; then
    KERNEL_INSTALLED=true
    INSTALLED_KERNEL="6.12.38+deb13-amd64"
    log "SUCCESS: Installed specific 6.12.38 kernel"
fi

# Method 2: Try any 6.12 kernel
if [ "$KERNEL_INSTALLED" = false ]; then
    echo -e "${BLUE}Method 2: Any available 6.12 kernel${NC}"
    KERNEL_612=$(echo "$AVAILABLE_KERNELS" | grep "6\.12" | head -1 | awk '{print $1}')
    if [ -n "$KERNEL_612" ]; then
        log "Attempting kernel: $KERNEL_612"
        KERNEL_VERSION=$(echo "$KERNEL_612" | sed 's/linux-image-//')
        
        if sudo chroot "$CHROOT" apt-get install -y --no-install-recommends \
            --allow-downgrades --allow-remove-essential --allow-change-held-packages \
            "$KERNEL_612" \
            "linux-headers-${KERNEL_VERSION}" 2>&1 | tee -a "$LOG_FILE"; then
            KERNEL_INSTALLED=true
            INSTALLED_KERNEL="$KERNEL_VERSION"
            log "SUCCESS: Installed $KERNEL_612"
        fi
    fi
fi

# Method 3: Force metapackage with dist-upgrade
if [ "$KERNEL_INSTALLED" = false ]; then
    echo -e "${BLUE}Method 3: Force metapackage with full upgrade${NC}"
    log "Attempting metapackage with full dist-upgrade..."
    
    # First do a full dist-upgrade
    sudo chroot "$CHROOT" apt-get dist-upgrade -y --no-install-recommends \
        --allow-downgrades --allow-remove-essential --allow-change-held-packages 2>&1 | tee -a "$LOG_FILE" || true
    
    # Then install metapackage
    if sudo chroot "$CHROOT" apt-get install -y --no-install-recommends \
        --allow-downgrades --allow-remove-essential --allow-change-held-packages \
        linux-image-amd64 linux-headers-amd64 2>&1 | tee -a "$LOG_FILE"; then
        KERNEL_INSTALLED=true
        INSTALLED_KERNEL="metapackage"
        log "SUCCESS: Installed kernel metapackage"
    fi
fi

# Method 4: Try any 6.x kernel (6.6, 6.8, etc.)
if [ "$KERNEL_INSTALLED" = false ]; then
    echo -e "${BLUE}Method 4: Any newer 6.x kernel${NC}"
    KERNEL_6X=$(echo "$AVAILABLE_KERNELS" | grep -E "6\.[6-9]\.|6\.1[0-9]\." | head -1 | awk '{print $1}')
    if [ -n "$KERNEL_6X" ]; then
        log "Attempting newer 6.x kernel: $KERNEL_6X"
        KERNEL_VERSION=$(echo "$KERNEL_6X" | sed 's/linux-image-//')
        
        if sudo chroot "$CHROOT" apt-get install -y --no-install-recommends \
            --allow-downgrades --allow-remove-essential --allow-change-held-packages \
            "$KERNEL_6X" \
            "linux-headers-${KERNEL_VERSION}" 2>&1 | tee -a "$LOG_FILE"; then
            KERNEL_INSTALLED=true
            INSTALLED_KERNEL="$KERNEL_VERSION"
            log "SUCCESS: Installed $KERNEL_6X"
        fi
    fi
fi

# Method 5: Download and install manually
if [ "$KERNEL_INSTALLED" = false ]; then
    echo -e "${BLUE}Method 5: Manual download and install${NC}"
    log "Attempting manual download and install..."
    
    # Try to download kernel package directly
    cd "$CHROOT/tmp" || exit 1
    
    # Find download URL
    KERNEL_URL=$(sudo chroot "$CHROOT" apt-cache show linux-image-6.12.38+deb13-amd64 2>/dev/null | grep "^Filename:" | awk '{print $2}')
    if [ -n "$KERNEL_URL" ]; then
        log "Downloading kernel package manually..."
        if sudo wget -O "$CHROOT/tmp/kernel.deb" "http://deb.debian.org/debian/$KERNEL_URL" 2>&1 | tee -a "$LOG_FILE"; then
            if sudo chroot "$CHROOT" dpkg -i /tmp/kernel.deb 2>&1 | tee -a "$LOG_FILE"; then
                KERNEL_INSTALLED=true
                INSTALLED_KERNEL="manual-6.12.38"
                log "SUCCESS: Manually installed kernel package"
            fi
        fi
    fi
fi

# Step 6: Install essential packages
echo
echo -e "${YELLOW}Phase 6: Essential Packages${NC}"
log "=== Installing Essential Packages ==="

# Install build tools
sudo chroot "$CHROOT" apt-get install -y --no-install-recommends \
    build-essential dkms linux-base bc kmod cpio 2>&1 | tee -a "$LOG_FILE" || true

# Step 7: Final verification
echo
echo -e "${YELLOW}Phase 7: Final Verification${NC}"
log "=== Final Verification ==="

echo
echo -e "${BLUE}=== FINAL RESULTS ===${NC}"

# Check installed kernels
echo -n "Kernel 6.12+ installed: "
if sudo chroot "$CHROOT" dpkg -l 2>/dev/null | grep -q '^ii.*linux-image-6\.1[2-9]\|^ii.*linux-image-6\.[2-9]'; then
    echo -e "${GREEN}✓ YES${NC}"
    KERNEL_SUCCESS=true
    
    # Show which kernel
    FINAL_KERNEL=$(sudo chroot "$CHROOT" dpkg -l 2>/dev/null | grep '^ii.*linux-image-6' | grep -v dbg | head -1 | awk '{print $2}' | sed 's/linux-image-//')
    echo "  Installed kernel: $FINAL_KERNEL"
else
    echo -e "${RED}✗ NO${NC}"
    KERNEL_SUCCESS=false
fi

# Check ZFS
echo -n "ZFS packages: "
if sudo chroot "$CHROOT" which zfs >/dev/null 2>&1; then
    echo -e "${GREEN}✓ YES${NC}"
    ZFS_SUCCESS=true
else
    echo -e "${RED}✗ NO${NC}"
    ZFS_SUCCESS=false
fi

# Overall result
echo
if [ "$KERNEL_SUCCESS" = true ] && [ "$ZFS_SUCCESS" = true ]; then
    echo -e "${GREEN}🎉 NUCLEAR FIX SUCCESSFUL!${NC}"
    log "Nuclear fix completed successfully"
    echo
    echo "Your system now has:"
    echo "  • Trixie kernel 6.12+ installed"
    echo "  • ZFS packages ready"
    echo "  • System ready to continue Z-FORGE build"
    exit 0
else
    echo -e "${RED}💥 NUCLEAR FIX FAILED${NC}"
    log "Nuclear fix failed - manual intervention required"
    echo
    echo "Issues remaining:"
    [ "$KERNEL_SUCCESS" = false ] && echo "  • Kernel 6.12+ not installed"
    [ "$ZFS_SUCCESS" = false ] && echo "  • ZFS packages missing"
    
    echo
    echo "Log file: $LOG_FILE"
    echo
    echo "Manual commands to try:"
    echo "  sudo chroot $CHROOT apt-cache search linux-image | grep 6"
    echo "  sudo chroot $CHROOT apt-get install linux-image-amd64 --reinstall"
    echo "  sudo chroot $CHROOT dpkg --configure -a"
    exit 1
fi
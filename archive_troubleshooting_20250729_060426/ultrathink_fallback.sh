#!/bin/bash
# UltraThink Fallback - Comprehensive manual fix

set +e  # Continue on errors

CHROOT_PATH="/tmp/zforge_workspace/chroot"
LOG_FILE="/opt/github/Z-FORGE/ultrathink_fallback_$(date +%Y%m%d_%H%M%S).log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║        UltraThink Fallback Manual Fix System              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo

log "Starting UltraThink Fallback Fix"
log "Log file: $LOG_FILE"

# Check prerequisites
if [ ! -d "$CHROOT_PATH" ]; then
    log "ERROR: Chroot not found at $CHROOT_PATH"
    exit 1
fi

# Function to fix dpkg
fix_dpkg() {
    log "=== Fixing DPKG Issues ==="
    
    # Kill any stuck processes
    log "Killing any stuck apt/dpkg processes..."
    killall -9 apt apt-get dpkg 2>/dev/null || true
    sleep 2
    
    # Remove all lock files
    log "Removing lock files..."
    rm -f "$CHROOT_PATH"/var/lib/dpkg/lock* 2>/dev/null || true
    rm -f "$CHROOT_PATH"/var/lib/apt/lists/lock* 2>/dev/null || true
    rm -f "$CHROOT_PATH"/var/cache/apt/archives/lock* 2>/dev/null || true
    
    # Fix dpkg database
    log "Configuring dpkg..."
    chroot "$CHROOT_PATH" dpkg --configure -a 2>&1 | tee -a "$LOG_FILE" || true
    
    # Fix broken packages
    log "Fixing broken packages..."
    chroot "$CHROOT_PATH" apt-get install -f -y 2>&1 | tee -a "$LOG_FILE" || true
    
    # Clean cache
    log "Cleaning package cache..."
    chroot "$CHROOT_PATH" apt-get clean
    chroot "$CHROOT_PATH" apt-get autoclean
    
    log "DPKG fix completed"
}

# Function to fix repositories
fix_repositories() {
    log "=== Fixing APT Repositories ==="
    
    # Backup current sources
    if [ -f "$CHROOT_PATH/etc/apt/sources.list" ]; then
        cp "$CHROOT_PATH/etc/apt/sources.list" "$CHROOT_PATH/etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Create comprehensive Trixie sources
    log "Creating Trixie APT sources..."
    cat > "$CHROOT_PATH/etc/apt/sources.list" << 'EOF'
# Debian Testing (Trixie) - Primary repositories
deb http://deb.debian.org/debian testing main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian testing main contrib non-free non-free-firmware

# Security updates
deb http://deb.debian.org/debian-security testing-security main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian-security testing-security main contrib non-free non-free-firmware

# Trixie by name (fallback)
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware

# Testing updates
deb http://deb.debian.org/debian testing-updates main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian testing-updates main contrib non-free non-free-firmware
EOF
    
    # Remove any pinning
    log "Removing APT pinning..."
    rm -f "$CHROOT_PATH/etc/apt/preferences" 2>/dev/null || true
    rm -f "$CHROOT_PATH/etc/apt/preferences.d/"* 2>/dev/null || true
    
    # Clear entire apt cache
    log "Clearing entire APT cache..."
    rm -rf "$CHROOT_PATH/var/lib/apt/lists/"*
    
    # Update package lists
    log "Updating package lists..."
    chroot "$CHROOT_PATH" apt-get update 2>&1 | tee -a "$LOG_FILE"
    
    log "Repository fix completed"
}

# Function to install kernel
install_kernel() {
    log "=== Installing Trixie Kernel ==="
    
    # Remove old kernels first
    log "Removing any old kernels..."
    OLD_KERNELS=$(chroot "$CHROOT_PATH" dpkg -l | grep '^ii.*linux-image-6\.1\.' | awk '{print $2}')
    if [ -n "$OLD_KERNELS" ]; then
        log "Removing: $OLD_KERNELS"
        chroot "$CHROOT_PATH" apt-get remove -y $OLD_KERNELS 2>&1 | tee -a "$LOG_FILE" || true
    fi
    
    # Install prerequisites
    log "Installing prerequisites..."
    chroot "$CHROOT_PATH" apt-get install -y \
        build-essential \
        dkms \
        linux-base \
        initramfs-tools \
        bc \
        kmod \
        cpio 2>&1 | tee -a "$LOG_FILE" || true
    
    # Try different kernel installation methods
    KERNEL_INSTALLED=false
    
    # Method 1: Specific 6.12 kernel
    log "Trying specific 6.12 kernel..."
    if chroot "$CHROOT_PATH" apt-get install -y \
        linux-image-6.12.38+deb13-amd64 \
        linux-headers-6.12.38+deb13-amd64 2>&1 | tee -a "$LOG_FILE"; then
        KERNEL_INSTALLED=true
        log "SUCCESS: Installed 6.12.38 kernel"
    else
        log "Failed to install specific 6.12 kernel"
        
        # Method 2: Any 6.12 kernel
        log "Trying any 6.12 kernel..."
        KERNEL_612=$(chroot "$CHROOT_PATH" apt-cache search '^linux-image-6\.12' | grep -v dbg | head -1 | awk '{print $1}')
        if [ -n "$KERNEL_612" ]; then
            VERSION=$(echo "$KERNEL_612" | sed 's/linux-image-//')
            if chroot "$CHROOT_PATH" apt-get install -y \
                "$KERNEL_612" \
                "linux-headers-$VERSION" 2>&1 | tee -a "$LOG_FILE"; then
                KERNEL_INSTALLED=true
                log "SUCCESS: Installed $KERNEL_612"
            fi
        fi
        
        # Method 3: Metapackage with dist-upgrade
        if [ "$KERNEL_INSTALLED" = false ]; then
            log "Trying metapackage with dist-upgrade..."
            chroot "$CHROOT_PATH" apt-get dist-upgrade -y 2>&1 | tee -a "$LOG_FILE" || true
            if chroot "$CHROOT_PATH" apt-get install -y \
                linux-image-amd64 \
                linux-headers-amd64 2>&1 | tee -a "$LOG_FILE"; then
                KERNEL_INSTALLED=true
                log "SUCCESS: Installed kernel metapackage"
            fi
        fi
    fi
    
    if [ "$KERNEL_INSTALLED" = true ]; then
        log "Kernel installation successful"
    else
        log "ERROR: All kernel installation methods failed"
    fi
}

# Function to install ZFS
install_zfs() {
    log "=== Installing ZFS ==="
    
    # Remove conflicting packages
    log "Removing conflicting packages..."
    chroot "$CHROOT_PATH" apt-get remove -y zfs-initramfs 2>/dev/null || true
    
    # Install ZFS packages
    log "Installing ZFS packages..."
    if chroot "$CHROOT_PATH" apt-get install -y \
        zfsutils-linux \
        zfs-dkms 2>&1 | tee -a "$LOG_FILE"; then
        log "ZFS base packages installed"
        
        # Try dracut support
        if chroot "$CHROOT_PATH" apt-get install -y zfs-dracut 2>&1 | tee -a "$LOG_FILE"; then
            log "ZFS dracut support installed"
        else
            log "WARNING: Could not install zfs-dracut"
        fi
    else
        log "ERROR: Failed to install ZFS packages"
    fi
    
    # Check DKMS status
    log "Checking DKMS status..."
    chroot "$CHROOT_PATH" dkms status 2>&1 | tee -a "$LOG_FILE" || true
}

# Function to verify system
verify_system() {
    log "=== System Verification ==="
    
    echo
    echo -e "${YELLOW}Verification Results:${NC}"
    
    # Check kernel
    echo -n "Kernel 6.12.x installed: "
    if chroot "$CHROOT_PATH" dpkg -l | grep -q '^ii.*linux-image-6\.12'; then
        echo -e "${GREEN}✓ YES${NC}"
        KERNEL_OK=true
    else
        echo -e "${RED}✗ NO${NC}"
        KERNEL_OK=false
    fi
    
    # Check ZFS
    echo -n "ZFS packages installed: "
    if chroot "$CHROOT_PATH" which zfs >/dev/null 2>&1; then
        echo -e "${GREEN}✓ YES${NC}"
        ZFS_OK=true
    else
        echo -e "${RED}✗ NO${NC}"
        ZFS_OK=false
    fi
    
    # Check APT sources
    echo -n "APT sources configured for Trixie: "
    if grep -q "testing\|trixie" "$CHROOT_PATH/etc/apt/sources.list"; then
        echo -e "${GREEN}✓ YES${NC}"
        APT_OK=true
    else
        echo -e "${RED}✗ NO${NC}"
        APT_OK=false
    fi
    
    # Overall status
    echo
    if [ "$KERNEL_OK" = true ] && [ "$ZFS_OK" = true ] && [ "$APT_OK" = true ]; then
        echo -e "${GREEN}✅ SYSTEM SUCCESSFULLY FIXED!${NC}"
        return 0
    else
        echo -e "${RED}❌ SYSTEM STILL HAS ISSUES${NC}"
        return 1
    fi
}

# Main execution
main() {
    log "Starting comprehensive fallback fix..."
    
    # Execute all fixes in sequence
    fix_dpkg
    echo
    
    fix_repositories
    echo
    
    install_kernel
    echo
    
    install_zfs
    echo
    
    # Final verification
    verify_system
    RESULT=$?
    
    # Save summary
    echo
    log "=== Fix Summary ==="
    log "Log file saved to: $LOG_FILE"
    
    if [ $RESULT -eq 0 ]; then
        log "System successfully fixed!"
        echo
        echo -e "${GREEN}🎉 Success! Your system is now properly configured.${NC}"
        echo "The Trixie kernel and ZFS are installed and ready."
    else
        log "System still has issues - manual intervention required"
        echo
        echo -e "${RED}⚠️  Some issues remain. Please check the log file:${NC}"
        echo "  $LOG_FILE"
        echo
        echo "Manual debugging commands:"
        echo "  sudo chroot $CHROOT_PATH apt-cache policy linux-image-amd64"
        echo "  sudo chroot $CHROOT_PATH apt-cache search linux-image-6"
        echo "  sudo chroot $CHROOT_PATH dpkg --configure -a"
    fi
    
    return $RESULT
}

# Run main function
main
exit $?
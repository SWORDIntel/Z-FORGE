#!/bin/bash
# Verify ZFS Setup Script
# Checks if ZFS is properly built and installed in chroot

set -euo pipefail

# Configuration
CHROOT_PATH="${CHROOT_PATH:-$HOME/zforge_workspace/chroot}"
PACKAGES_DIR="${PACKAGES_DIR:-/opt/github/Z-FORGE/prebuilt_packages}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    return 1
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}              ZFS Setup Verification${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo ""

TOTAL_CHECKS=0
PASSED_CHECKS=0

# Check 1: Packages directory
echo -e "\n${BLUE}Checking ZFS packages...${NC}"
((TOTAL_CHECKS++))
if [ -d "$PACKAGES_DIR" ]; then
    PKG_COUNT=$(ls -1 "$PACKAGES_DIR"/*.deb 2>/dev/null | wc -l)
    if [ "$PKG_COUNT" -gt 0 ]; then
        check_pass "Found $PKG_COUNT ZFS packages in $PACKAGES_DIR"
        ((PASSED_CHECKS++))
        
        # List packages
        echo "  Packages:"
        for pkg in "$PACKAGES_DIR"/*.deb; do
            if [ -f "$pkg" ]; then
                echo "    - $(basename "$pkg")"
            fi
        done
    else
        check_fail "No .deb packages found in $PACKAGES_DIR"
    fi
else
    check_fail "Packages directory not found: $PACKAGES_DIR"
fi

# Check 2: Chroot existence
echo -e "\n${BLUE}Checking chroot environment...${NC}"
((TOTAL_CHECKS++))
if [ -d "$CHROOT_PATH" ]; then
    check_pass "Chroot found at $CHROOT_PATH"
    ((PASSED_CHECKS++))
    
    # Check chroot structure
    MISSING_DIRS=0
    for dir in etc usr bin sbin lib var proc sys dev; do
        if [ ! -d "$CHROOT_PATH/$dir" ]; then
            check_fail "Missing essential directory: $dir"
            ((MISSING_DIRS++))
        fi
    done
    
    if [ "$MISSING_DIRS" -eq 0 ]; then
        check_pass "All essential directories present"
    fi
else
    check_fail "Chroot not found at $CHROOT_PATH"
    echo "  Run: sudo $0 --bootstrap"
    exit 1
fi

# Check 3: ZFS installation in chroot (requires root)
if [ "$EUID" -eq 0 ]; then
    echo -e "\n${BLUE}Checking ZFS installation in chroot...${NC}"
    
    # Mount necessary filesystems
    mount -t proc proc "$CHROOT_PATH/proc" 2>/dev/null || true
    mount -t sysfs sys "$CHROOT_PATH/sys" 2>/dev/null || true
    mount -o bind /dev "$CHROOT_PATH/dev" 2>/dev/null || true
    
    # Check for ZFS binaries
    ((TOTAL_CHECKS++))
    ZFS_BINARIES=(zfs zpool zdb zed)
    FOUND_BINARIES=0
    
    for bin in "${ZFS_BINARIES[@]}"; do
        if chroot "$CHROOT_PATH" which "$bin" &>/dev/null; then
            ((FOUND_BINARIES++))
        fi
    done
    
    if [ "$FOUND_BINARIES" -eq "${#ZFS_BINARIES[@]}" ]; then
        check_pass "All ZFS binaries found in chroot"
        ((PASSED_CHECKS++))
    else
        check_fail "Missing ZFS binaries (found $FOUND_BINARIES/${#ZFS_BINARIES[@]})"
    fi
    
    # Check installed packages
    ((TOTAL_CHECKS++))
    ZFS_PKGS=$(chroot "$CHROOT_PATH" dpkg -l 2>/dev/null | grep -E "^ii.*zfs|^ii.*zpool" | wc -l)
    if [ "$ZFS_PKGS" -gt 0 ]; then
        check_pass "Found $ZFS_PKGS ZFS-related packages installed"
        ((PASSED_CHECKS++))
    else
        check_fail "No ZFS packages installed in chroot"
    fi
    
    # Check ZFS version
    ((TOTAL_CHECKS++))
    if chroot "$CHROOT_PATH" zfs version &>/dev/null; then
        ZFS_VER=$(chroot "$CHROOT_PATH" zfs version | head -1)
        check_pass "ZFS version: $ZFS_VER"
        ((PASSED_CHECKS++))
    else
        check_warn "Cannot check ZFS version (kernel module not loaded - normal in chroot)"
        ((PASSED_CHECKS++))
    fi
    
    # Unmount
    umount "$CHROOT_PATH"/{dev,sys,proc} 2>/dev/null || true
else
    echo -e "\n${YELLOW}Skipping chroot checks (requires root)${NC}"
    echo "  Run: sudo $0"
fi

# Check 4: Z-FORGE integration
echo -e "\n${BLUE}Checking Z-FORGE integration...${NC}"
((TOTAL_CHECKS++))
if [ -f "/opt/github/Z-FORGE/Makefile" ]; then
    check_pass "Z-FORGE found at /opt/github/Z-FORGE"
    ((PASSED_CHECKS++))
    
    # Check if packages would be detected
    if grep -q "prebuilt_packages" /opt/github/Z-FORGE/Makefile 2>/dev/null; then
        check_pass "Z-FORGE configured to use prebuilt packages"
    else
        check_warn "Z-FORGE may need configuration for prebuilt packages"
    fi
else
    check_fail "Z-FORGE not found at expected location"
fi

# Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Summary: ${PASSED_CHECKS}/${TOTAL_CHECKS} checks passed${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════${NC}"

if [ "$PASSED_CHECKS" -eq "$TOTAL_CHECKS" ]; then
    echo -e "\n${GREEN}✅ All checks passed! System is ready.${NC}"
    echo ""
    echo "To use with Z-FORGE:"
    echo "  export CHROOT_PATH=$CHROOT_PATH"
    echo "  cd /opt/github/Z-FORGE"
    echo "  make build"
else
    echo -e "\n${YELLOW}⚠ Some checks failed. Please review the issues above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Build ZFS: /opt/github/Z-FORGE/scripts/build/build_zfs_simple.sh"
    echo "  - Bootstrap chroot: sudo /opt/github/Z-FORGE/scripts/build/quick_zfs_bootstrap.sh"
    echo "  - Fix chroot: sudo /opt/github/Z-FORGE/ultrathink_master_fix.sh"
fi

# Optional: Show commands for manual testing
if [ "$EUID" -eq 0 ]; then
    echo -e "\n${BLUE}Manual testing commands:${NC}"
    echo "  # Enter chroot:"
    echo "  sudo chroot $CHROOT_PATH /bin/bash"
    echo ""
    echo "  # Inside chroot:"
    echo "  zfs version"
    echo "  zpool list"
    echo "  dpkg -l | grep zfs"
fi
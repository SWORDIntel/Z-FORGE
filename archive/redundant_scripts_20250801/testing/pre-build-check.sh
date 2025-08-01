#!/bin/bash
# Pre-build safety check for Z-FORGE T30 ISO

echo "=== Z-FORGE Pre-Build Safety Check ==="
echo "Target: Dell PowerEdge T30"
echo "Date: $(date)"
echo

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

# Function to check requirement
check() {
    local test_name="$1"
    local test_cmd="$2"
    local is_critical="${3:-true}"
    
    printf "Checking %-40s" "$test_name..."
    
    if eval "$test_cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}[OK]${NC}"
    else
        if [ "$is_critical" = "true" ]; then
            echo -e "${RED}[FAIL]${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}[WARN]${NC}"
            ((WARNINGS++))
        fi
    fi
}

# System Requirements
echo "=== System Requirements ==="
check "Running as root" "[ $EUID -eq 0 ]"
check "CPU architecture (x86_64)" "[ $(uname -m) = 'x86_64' ]"
check "Minimum RAM (4GB)" "[ $(free -g | awk '/^Mem:/{print $2}') -ge 4 ]"
check "Available disk space (50GB)" "[ $(df -BG /tmp | tail -1 | awk '{print $4}' | sed 's/G//') -ge 50 ]"

# Essential Tools
echo -e "\n=== Essential Build Tools ==="
check "Python 3" "command -v python3"
check "Git" "command -v git"
check "Debootstrap" "command -v debootstrap"
check "Xorriso" "command -v xorriso"
check "Sudo" "command -v sudo"
check "Chroot" "command -v chroot"

# Build Environment
echo -e "\n=== Build Environment ==="
check "Z-FORGE directory" "[ -d /opt/github/Z-FORGE ]"
check "Builder modules" "[ -d /opt/github/Z-FORGE/builder/modules ]"
check "T30 configuration" "[ -f /opt/github/Z-FORGE/config/t30/t30_build_spec.yml ]"
check "T30 scripts" "[ -f /opt/github/Z-FORGE/config/t30/t30_post_install.sh ]"

# Network Connectivity
echo -e "\n=== Network Connectivity ==="
check "Internet connection" "ping -c 1 -W 2 debian.org"
check "Debian mirror" "curl -s -f -m 5 http://deb.debian.org/debian/dists/trixie/Release" "false"
check "Kernel.org API" "curl -s -f -m 5 https://www.kernel.org/releases.json" "false"

# Optional Features
echo -e "\n=== Optional Features ==="
check "ZFS kernel module" "lsmod | grep -q zfs" "false"
check "ISOLINUX for BIOS boot" "[ -f /usr/lib/ISOLINUX/isolinux.bin ]" "false"
check "EFI support" "[ -d /sys/firmware/efi ]" "false"

# Module Checks
echo -e "\n=== Module Integrity ==="
check "KernelAcquisition module" "python3 -c 'from builder.modules.kernel_acquisition import KernelAcquisition'"
check "ZFSBuild module" "python3 -c 'from builder.modules.zfs_build import ZFSBuild'"
check "DellT30Optimize module" "python3 -c 'from builder.modules.dell_t30_optimize import DellT30Optimize'"

# Workspace Preparation
echo -e "\n=== Workspace Preparation ==="
if [ -d ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace} ]; then
    echo -e "${YELLOW}[WARN]${NC} Workspace already exists at ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
    echo "      Run 'sudo rm -rf ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}' to clean before build"
    ((WARNINGS++))
else
    echo -e "${GREEN}[OK]${NC} Workspace is clean"
fi

# Summary
echo -e "\n=== Pre-Build Check Summary ==="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠ $WARNINGS warnings found (non-critical)${NC}"
    fi
    echo -e "\n${GREEN}Ready to build T30 ISO:${NC}"
    echo "  cd /opt/github/Z-FORGE"
    echo "  sudo python3 builder/z-forge.py --build-spec config/t30/t30_build_spec.yml"
    exit 0
else
    echo -e "${RED}✗ $ERRORS critical errors found!${NC}"
    echo -e "Please fix the issues above before attempting build."
    exit 1
fi
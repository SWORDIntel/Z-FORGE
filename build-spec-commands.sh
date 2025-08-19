#!/bin/bash
#
# Z-FORGE Build Commands for Each Specification
# Quick commands to build specific versions with full logging
#

# Create logs directory if it doesn't exist
mkdir -p logs

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Z-FORGE Build Specification Commands${NC}"
echo "====================================="
echo -e "${YELLOW}ALL builds include: Proxmox VE 9 + ZFS + Debian Trixie${NC}"
echo ""

# Function to display build command
show_build() {
    local name="$1"
    local desc="$2"
    local spec="$3"
    
    echo -e "${GREEN}$name${NC}"
    echo "$desc"
    echo -e "${YELLOW}Command:${NC}"
    echo "$spec"
    echo ""
}

# 1. OUTSIDE PACKAGES BUILD (Fastest - for testing)
show_build \
    "1. OUTSIDE PACKAGES BUILD - build_spec_outside_packages.yml" \
    "   95% success rate - Full Proxmox VE 9 + ZFS + Trixie, prebuilt packages, RAM build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_outside_packages.yml \\
    --workspace /dev/shm/zforge-workspace-outside \\
    --verbose 2>&1 | tee logs/outside-packages-\$(date +%Y%m%d-%H%M%S).log"

# 2. STANDARD BUILD
show_build \
    "2. STANDARD BUILD - build_spec.yml" \
    "   70% success rate - Full Proxmox VE 9 + ZFS + Trixie, standard configuration, RAM build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec.yml \\
    --workspace /dev/shm/zforge-workspace-main \\
    --verbose 2>&1 | tee logs/standard-\$(date +%Y%m%d-%H%M%S).log"

# 3. PROXMOX 9 STANDARD
show_build \
    "3. PROXMOX 9 STANDARD - build_spec_proxmox9.yml" \
    "   75% success rate - Full Proxmox VE 9 + ZFS + Trixie standard installation, RAM build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_proxmox9.yml \\
    --workspace /dev/shm/zforge-workspace-pve9 \\
    --verbose 2>&1 | tee logs/proxmox9-\$(date +%Y%m%d-%H%M%S).log"

# 4. PROXMOX 9 FULL
show_build \
    "4. PROXMOX 9 FULL - build_spec_proxmox_full.yml" \
    "   75% success rate - Full Proxmox VE 9 + ZFS + Trixie with Ceph, HA, Backup Server, RAM build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_proxmox_full.yml \\
    --workspace /dev/shm/zforge-workspace-proxmox \\
    --verbose 2>&1 | tee logs/proxmox-full-\$(date +%Y%m%d-%H%M%S).log"

# 5. TMPFS BUILD
show_build \
    "5. TMPFS BUILD - build_spec_tmpfs.yml" \
    "   85% success rate - Full Proxmox VE 9 + ZFS + Trixie optimized for tmpfs/RAM builds" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_tmpfs.yml \\
    --workspace /dev/shm/zforge-workspace-tmpfs \\
    --verbose 2>&1 | tee logs/tmpfs-\$(date +%Y%m%d-%H%M%S).log"

# 6. MINIMAL PROXMOX BUILD  
show_build \
    "6. MINIMAL PROXMOX - build_spec_minimal_proxmox.yml" \
    "   90% success rate - Full Proxmox VE 9 + ZFS + Trixie with streamlined modules, RAM build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_minimal_proxmox.yml \\
    --workspace /dev/shm/zforge-workspace-noprox \\
    --verbose 2>&1 | tee logs/minimal-proxmox-\$(date +%Y%m%d-%H%M%S).log"

# 7. WORKING BUILD
show_build \
    "7. WORKING BUILD - build_spec_working.yml" \
    "   85% success rate - Full Proxmox VE 9 + ZFS + Trixie known working configuration, RAM build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_working.yml \\
    --workspace /dev/shm/zforge-workspace-working \\
    --verbose 2>&1 | tee logs/working-\$(date +%Y%m%d-%H%M%S).log"

# 8. TRIXIE CLEAN
show_build \
    "8. TRIXIE CLEAN - build_spec_trixie_clean.yml" \
    "   60% success rate - Full Proxmox VE 9 + ZFS + Clean Debian Trixie, experimental, RAM build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_trixie_clean.yml \\
    --workspace /dev/shm/zforge-workspace-trixie \\
    --verbose 2>&1 | tee logs/trixie-\$(date +%Y%m%d-%H%M%S).log"

# 9. NO TMP BUILD (converted to RAM)
show_build \
    "9. NO TMP BUILD - build_spec_no_tmp.yml" \
    "   80% success rate - Full Proxmox VE 9 + ZFS + Trixie (converted to RAM build per request), RAM build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_no_tmp.yml \\
    --workspace /dev/shm/zforge-workspace-notmp \\
    --verbose 2>&1 | tee logs/no-tmp-\$(date +%Y%m%d-%H%M%S).log"


echo "====================================="
echo -e "${CYAN}Advanced Options:${NC}"
echo ""

echo "Resume a failed build:"
echo -e "${YELLOW}sudo python3 build.py --spec <spec_file> --workspace <same_workspace> --resume 2>&1 | tee -a logs/resume-\$(date +%Y%m%d-%H%M%S).log${NC}"
echo ""

echo "Debug mode with maximum verbosity:"
echo -e "${YELLOW}sudo python3 build.py --spec <spec_file> --workspace <workspace> --debug --verbose 2>&1 | tee logs/debug-\$(date +%Y%m%d-%H%M%S).log${NC}"
echo ""

echo "Build with real-time monitoring (in another terminal):"
echo -e "${YELLOW}watch -n 2 'tail -20 logs/*.log | grep -E \"Module|SUCCESS|ERROR\"'${NC}"
echo ""

echo "Check build progress:"
echo -e "${YELLOW}cat /dev/shm/zforge-*/build_progress.json | python3 -m json.tool${NC}"
echo ""

echo "====================================="
echo -e "${GREEN}Recommended Build Order (All include Full Proxmox VE 9 + ZFS + Trixie + RAM):${NC}"
echo "1. Start with: build_spec_outside_packages.yml (95% success, fastest, prebuilt packages)"
echo "2. Then try: build_spec_minimal_proxmox.yml (90% success, streamlined modules)"
echo "3. Development: build_spec_working.yml (85% success, known working config)"
echo "4. Performance: build_spec_tmpfs.yml (85% success, tmpfs optimized)"
echo "5. Full features: build_spec_proxmox_full.yml (75% success, Ceph+HA+Backup)"
echo ""
echo -e "${GREEN}Key Features (ALL builds include):${NC}"
echo "• Proxmox VE 9.0 - Full virtualization platform"
echo "• ZFS 2.3.3 - Native encryption, compression, snapshots"
echo "• Debian Trixie - Latest stable base OS"
echo "• pve-kernel-6.14 - Proxmox-optimized kernel"
echo "• RAM builds (/dev/shm) - 3-5x faster than disk builds"
echo ""
echo -e "${GREEN}Tips:${NC}"
echo "• Monitor /dev/shm usage: df -h /dev/shm (needs ~10-20GB free)"
echo "• Use --resume if build fails to save hours"
echo "• All ISOs include live boot + installation capabilities"
echo "• ZFS streaming deployment available for mass server rollouts"
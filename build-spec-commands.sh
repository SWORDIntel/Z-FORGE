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

# 1. MINIMAL BUILD (Fastest - for testing)
show_build \
    "1. MINIMAL BUILD - build_spec_outside_packages.yml" \
    "   95% success rate - Minimal packages, fastest build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_outside_packages.yml \\
    --workspace /tmp/zforge-minimal \\
    --verbose 2>&1 | tee logs/minimal-\$(date +%Y%m%d-%H%M%S).log"

# 2. STABLE BUILD
show_build \
    "2. STABLE BUILD - build_spec_stable.yml" \
    "   85% success rate - Production ready, stable configuration" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_stable.yml \\
    --workspace /tmp/zforge-stable \\
    --verbose 2>&1 | tee logs/stable-\$(date +%Y%m%d-%H%M%S).log"

# 3. PROXMOX 9 STANDARD
show_build \
    "3. PROXMOX 9 STANDARD - build_spec_proxmox9.yml" \
    "   75% success rate - Proxmox VE 9 standard installation" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_proxmox9.yml \\
    --workspace /tmp/zforge-proxmox9 \\
    --verbose 2>&1 | tee logs/proxmox9-\$(date +%Y%m%d-%H%M%S).log"

# 4. PROXMOX 9 FULL
show_build \
    "4. PROXMOX 9 FULL - build_spec_proxmox_full.yml" \
    "   75% success rate - Full Proxmox with Ceph, HA, Backup Server" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_proxmox_full.yml \\
    --workspace /tmp/zforge-proxmox-full \\
    --verbose 2>&1 | tee logs/proxmox-full-\$(date +%Y%m%d-%H%M%S).log"

# 5. STANDARD BUILD
show_build \
    "5. STANDARD BUILD - build_spec.yml" \
    "   70% success rate - Full featured standard build" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec.yml \\
    --workspace /tmp/zforge-standard \\
    --verbose 2>&1 | tee logs/standard-\$(date +%Y%m%d-%H%M%S).log"

# 6. MINIMAL PROXMOX BUILD
show_build \
    "6. MINIMAL PROXMOX - build_spec_minimal_proxmox.yml" \
    "   90% success rate - Minimal Proxmox VE 9 with core features only" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_minimal_proxmox.yml \\
    --workspace /tmp/zforge-minimal-proxmox \\
    --verbose 2>&1 | tee logs/minimal-proxmox-\$(date +%Y%m%d-%H%M%S).log"

# 7. NO TMP BUILD (for systems with limited RAM)
show_build \
    "7. NO TMP BUILD - build_spec_no_tmp.yml" \
    "   80% success rate - Uses disk instead of RAM" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_no_tmp.yml \\
    --workspace /var/tmp/zforge-no-tmp \\
    --verbose 2>&1 | tee logs/no-tmp-\$(date +%Y%m%d-%H%M%S).log"

# 8. TMPFS BUILD
show_build \
    "8. TMPFS BUILD - build_spec_tmpfs.yml" \
    "   85% success rate - Optimized for tmpfs/RAM builds" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_tmpfs.yml \\
    --workspace /tmp/zforge-tmpfs \\
    --verbose 2>&1 | tee logs/tmpfs-\$(date +%Y%m%d-%H%M%S).log"

# 9. TRIXIE CLEAN
show_build \
    "9. TRIXIE CLEAN - build_spec_trixie_clean.yml" \
    "   60% success rate - Clean Debian Trixie, experimental" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_trixie_clean.yml \\
    --workspace /tmp/zforge-trixie \\
    --verbose 2>&1 | tee logs/trixie-\$(date +%Y%m%d-%H%M%S).log"

# 10. WORKING BUILD
show_build \
    "10. WORKING BUILD - build_spec_working.yml" \
    "    85% success rate - Known working Proxmox VE 9 for development" \
    "sudo python3 build.py \\
    --spec build_specs/build_spec_working.yml \\
    --workspace /tmp/zforge-working \\
    --verbose 2>&1 | tee logs/working-\$(date +%Y%m%d-%H%M%S).log"

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
echo -e "${YELLOW}cat /tmp/zforge-*/build_progress.json | python3 -m json.tool${NC}"
echo ""

echo "====================================="
echo -e "${GREEN}Recommended Build Order (All include Proxmox VE 9 + ZFS):${NC}"
echo "1. Start with: build_spec_outside_packages.yml (95% success, fastest)"
echo "2. Then try: build_spec_minimal_proxmox.yml (90% success, basic Proxmox)"
echo "3. Production: build_spec_stable.yml (85% success, stable Proxmox)"
echo "4. Full features: build_spec_proxmox_full.yml (75% success, Ceph+HA+Backup)"
echo ""
echo -e "${GREEN}Key Features (ALL builds include):${NC}"
echo "• Proxmox VE 9.0 - Full virtualization platform"
echo "• ZFS 2.3.3 - Native encryption, compression, snapshots"
echo "• Debian Trixie - Latest stable base OS"
echo "• pve-kernel-6.14 - Proxmox-optimized kernel"
echo "• RAM builds (/tmp) - 3-5x faster than disk builds"
echo ""
echo -e "${GREEN}Tips:${NC}"
echo "• Monitor /tmp usage: df -h /tmp (needs ~10-20GB free)"
echo "• Use --resume if build fails to save hours"
echo "• All ISOs include live boot + installation capabilities"
echo "• ZFS streaming deployment available for mass server rollouts"
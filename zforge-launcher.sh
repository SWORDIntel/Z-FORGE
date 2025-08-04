#!/bin/bash
# Z-FORGE TUI Launcher
# Quick access to all Z-FORGE build and management functions

set -e

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if running with sudo when needed
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}This operation requires sudo. Please run with: sudo $0${NC}"
        read -p "Press Enter to continue..."
        return 1
    fi
    return 0
}

# Clear screen and show header
show_header() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}                    ${BOLD}${WHITE}Z-FORGE BUILD SYSTEM${NC}                        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                      ${YELLOW}TUI Launcher v1.0${NC}                          ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Show system status
show_status() {
    echo -e "${BOLD}${BLUE}=== System Status ===${NC}"
    echo ""
    
    # Check workspace
    WORKSPACE="${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}"
    if [ -d "$WORKSPACE" ]; then
        echo -e "Workspace: ${GREEN}$WORKSPACE ✓${NC}"
    else
        echo -e "Workspace: ${RED}Not created${NC}"
    fi
    
    # Check chroot
    if [ -d "$WORKSPACE/chroot/usr" ]; then
        echo -e "Chroot: ${GREEN}Ready ✓${NC}"
    else
        echo -e "Chroot: ${RED}Not bootstrapped${NC}"
    fi
    
    # Check for ZFS in chroot
    if [ -f "$WORKSPACE/chroot/usr/sbin/zfs" ]; then
        echo -e "ZFS: ${GREEN}Installed ✓${NC}"
    else
        echo -e "ZFS: ${YELLOW}Not installed${NC}"
    fi
    
    # Check for existing ISO
    if [ -f "$WORKSPACE/output/zforge-3.0-amd64.iso" ]; then
        SIZE=$(ls -lh "$WORKSPACE/output/zforge-3.0-amd64.iso" | awk '{print $5}')
        echo -e "ISO: ${GREEN}Built ($SIZE) ✓${NC}"
    else
        echo -e "ISO: ${YELLOW}Not built${NC}"
    fi
    
    # Check git status
    if [ -d .git ]; then
        BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
        MODIFIED=$(git status --porcelain | wc -l)
        if [ $MODIFIED -eq 0 ]; then
            echo -e "Git: ${GREEN}$BRANCH (clean) ✓${NC}"
        else
            echo -e "Git: ${YELLOW}$BRANCH ($MODIFIED modified files)${NC}"
        fi
    fi
    
    echo ""
}

# Quick build menu
quick_build_menu() {
    show_header
    echo -e "${BOLD}${PURPLE}=== Quick Build Menu ===${NC}"
    echo ""
    echo "1) Complete Build (Bootstrap + ZFS + ISO)"
    echo "2) Bootstrap Only"
    echo "3) Install ZFS Only"
    echo "4) Build ISO Only"
    echo "5) Clean and Rebuild Everything"
    echo ""
    echo "0) Back to Main Menu"
    echo ""
    read -p "Select option: " choice
    
    case $choice in
        1)
            check_sudo || return
            echo -e "${GREEN}Starting complete build...${NC}"
            ./scripts/chroot/bootstrap_chroot.sh auto
            ./scripts/chroot/complete_zfs_install.sh
            make -f Makefile.no_tmp build
            read -p "Press Enter to continue..."
            ;;
        2)
            check_sudo || return
            echo -e "${GREEN}Starting bootstrap...${NC}"
            ./scripts/chroot/bootstrap_chroot.sh auto
            read -p "Press Enter to continue..."
            ;;
        3)
            check_sudo || return
            echo -e "${GREEN}Installing ZFS...${NC}"
            ./scripts/chroot/complete_zfs_install.sh
            read -p "Press Enter to continue..."
            ;;
        4)
            check_sudo || return
            echo -e "${GREEN}Building ISO...${NC}"
            make -f Makefile.no_tmp build
            read -p "Press Enter to continue..."
            ;;
        5)
            check_sudo || return
            echo -e "${YELLOW}Cleaning workspace...${NC}"
            rm -rf ~/zforge_workspace
            echo -e "${GREEN}Starting fresh build...${NC}"
            ./scripts/workspace/setup_no_tmp_build.sh
            ./scripts/chroot/bootstrap_chroot.sh auto
            ./scripts/chroot/complete_zfs_install.sh
            make -f Makefile.no_tmp build
            read -p "Press Enter to continue..."
            ;;
        0) return ;;
        *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
    esac
}

# Diagnostics menu
diagnostics_menu() {
    show_header
    echo -e "${BOLD}${PURPLE}=== Diagnostics Menu ===${NC}"
    echo ""
    echo "1) Run Pre-build Check"
    echo "2) Verify Project Consistency"
    echo "3) Check Script Paths"
    echo "4) View Build Logs"
    echo "5) Check Chroot Mounts"
    echo "6) Test Chroot Access"
    echo ""
    echo "0) Back to Main Menu"
    echo ""
    read -p "Select option: " choice
    
    case $choice in
        1)
            echo -e "${GREEN}Running pre-build check...${NC}"
            ./scripts/testing/pre-build-check.sh
            read -p "Press Enter to continue..."
            ;;
        2)
            echo -e "${GREEN}Verifying project consistency...${NC}"
            ./scripts/cleanup/verify_project_consistency.sh
            read -p "Press Enter to continue..."
            ;;
        3)
            echo -e "${GREEN}Checking for old paths...${NC}"
            echo "Searching for /tmp/zforge_workspace references..."
            grep -r "/tmp/zforge_workspace" scripts/ --include="*.sh" 2>/dev/null | wc -l
            echo "Found $(grep -r "/tmp/zforge_workspace" scripts/ --include="*.sh" 2>/dev/null | wc -l) references"
            read -p "Press Enter to continue..."
            ;;
        4)
            echo -e "${GREEN}Recent build logs:${NC}"
            ls -lt ~/zforge_workspace/logs/*.log 2>/dev/null | head -10 || echo "No logs found"
            echo ""
            read -p "Enter log filename to view (or Enter to skip): " logfile
            if [ -n "$logfile" ] && [ -f "~/zforge_workspace/logs/$logfile" ]; then
                less "~/zforge_workspace/logs/$logfile"
            fi
            ;;
        5)
            echo -e "${GREEN}Checking mounts...${NC}"
            mount | grep zforge_workspace || echo "No zforge mounts found"
            read -p "Press Enter to continue..."
            ;;
        6)
            if check_sudo; then
                echo -e "${GREEN}Testing chroot access...${NC}"
                ./scripts/chroot/use_arch_chroot.sh echo "Chroot is working!"
                read -p "Press Enter to continue..."
            fi
            ;;
        0) return ;;
        *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
    esac
}

# Maintenance menu
maintenance_menu() {
    show_header
    echo -e "${BOLD}${PURPLE}=== Maintenance Menu ===${NC}"
    echo ""
    echo "1) Clean Build Workspace"
    echo "2) Remove Old Archives"
    echo "3) Update Script Paths"
    echo "4) Fix Workspace Permissions"
    echo "5) Emergency Cleanup (Unmount All)"
    echo "6) Backup Current State"
    echo ""
    echo "0) Back to Main Menu"
    echo ""
    read -p "Select option: " choice
    
    case $choice in
        1)
            echo -e "${YELLOW}This will remove the build workspace.${NC}"
            read -p "Are you sure? (y/N): " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                rm -rf ~/zforge_workspace
                echo -e "${GREEN}Workspace cleaned.${NC}"
            fi
            read -p "Press Enter to continue..."
            ;;
        2)
            if [ -d archive ] && [ "$(ls -A archive)" ]; then
                echo -e "${YELLOW}Removing archive directory...${NC}"
                rm -rf archive
                echo -e "${GREEN}Archives removed.${NC}"
            else
                echo -e "${GREEN}No archives to remove.${NC}"
            fi
            read -p "Press Enter to continue..."
            ;;
        3)
            echo -e "${GREEN}Updating script paths...${NC}"
            ./scripts/cleanup/fix_old_paths.sh
            read -p "Press Enter to continue..."
            ;;
        4)
            echo -e "${GREEN}Fixing workspace permissions...${NC}"
            ./scripts/workspace/fix_workspace_noexec.sh
            read -p "Press Enter to continue..."
            ;;
        5)
            if check_sudo; then
                echo -e "${YELLOW}Running emergency cleanup...${NC}"
                ./scripts/chroot/emergency_cleanup.sh
                read -p "Press Enter to continue..."
            fi
            ;;
        6)
            echo -e "${GREEN}Creating backup...${NC}"
            BACKUP_NAME="zforge_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
            tar -czf "$HOME/$BACKUP_NAME" \
                --exclude='zforge_workspace' \
                --exclude='.git' \
                --exclude='*.iso' \
                .
            echo -e "${GREEN}Backup saved to: $HOME/$BACKUP_NAME${NC}"
            read -p "Press Enter to continue..."
            ;;
        0) return ;;
        *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
    esac
}

# Documentation menu
docs_menu() {
    show_header
    echo -e "${BOLD}${PURPLE}=== Documentation Menu ===${NC}"
    echo ""
    echo "1) View Quick Reference"
    echo "2) View Build Guide"
    echo "3) View Troubleshooting"
    echo "4) View Latest Checkpoint"
    echo "5) View ISO Build Details"
    echo "6) Open Documentation Index"
    echo ""
    echo "0) Back to Main Menu"
    echo ""
    read -p "Select option: " choice
    
    case $choice in
        1) less checkpoint/QUICK_REFERENCE.md ;;
        2) less BUILD_FROM_FRESH.md ;;
        3) less TROUBLESHOOTING.md ;;
        4) less checkpoint/CHECKPOINT_20250731_SCRIPT_CLEANUP.md ;;
        5) less ISO_BUILD_DETAILS.md ;;
        6) less docs/README.md ;;
        0) return ;;
        *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
    esac
}

# Main menu
main_menu() {
    while true; do
        show_header
        show_status
        
        echo -e "${BOLD}${GREEN}=== Main Menu ===${NC}"
        echo ""
        echo "1) Quick Build Options"
        echo "2) Diagnostics & Testing"
        echo "3) Maintenance & Cleanup"
        echo "4) Documentation"
        echo "5) Enter Chroot Shell"
        echo "6) Git Status"
        echo ""
        echo "q) Quit"
        echo ""
        read -p "Select option: " choice
        
        case $choice in
            1) quick_build_menu ;;
            2) diagnostics_menu ;;
            3) maintenance_menu ;;
            4) docs_menu ;;
            5)
                if check_sudo; then
                    echo -e "${GREEN}Entering chroot shell...${NC}"
                    echo -e "${YELLOW}Type 'exit' to return to launcher${NC}"
                    sleep 2
                    ./scripts/chroot/use_arch_chroot.sh
                fi
                ;;
            6)
                echo -e "${GREEN}Git Status:${NC}"
                git status
                read -p "Press Enter to continue..."
                ;;
            q|Q) 
                echo -e "${GREEN}Exiting Z-FORGE Launcher. Goodbye!${NC}"
                exit 0
                ;;
            *) echo -e "${RED}Invalid option${NC}"; sleep 1 ;;
        esac
    done
}

# Check if we're in the right directory
if [ ! -f "build_specs/build_spec_no_tmp.yml" ]; then
    echo -e "${RED}Error: Not in Z-FORGE root directory!${NC}"
    echo "Please run this script from the Z-FORGE project root."
    exit 1
fi

# Start the launcher
main_menu
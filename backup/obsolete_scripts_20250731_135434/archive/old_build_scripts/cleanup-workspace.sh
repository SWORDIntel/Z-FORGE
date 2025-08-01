#!/bin/bash
# Z-FORGE Workspace Cleanup Script
# Safely cleans up the build workspace including unmounting filesystems

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default workspace path
WORKSPACE="${WORKSPACE:-/tmp/zforge_workspace}"

echo -e "${GREEN}Z-FORGE Workspace Cleanup${NC}"
echo "========================="
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[!] This script must be run as root.${NC}"
    exit 1
fi

# Function to safely unmount a path
safe_unmount() {
    local mount_path="$1"
    
    if mountpoint -q "$mount_path" 2>/dev/null; then
        echo -e "${YELLOW}[*] Unmounting $mount_path...${NC}"
        if umount "$mount_path" 2>/dev/null; then
            echo -e "${GREEN}[+] Successfully unmounted $mount_path${NC}"
        else
            # Try lazy unmount as fallback
            echo -e "${YELLOW}[*] Trying lazy unmount for $mount_path...${NC}"
            if umount -l "$mount_path" 2>/dev/null; then
                echo -e "${GREEN}[+] Successfully lazy-unmounted $mount_path${NC}"
            else
                echo -e "${RED}[!] Failed to unmount $mount_path${NC}"
                return 1
            fi
        fi
    fi
    return 0
}

# Function to check if workspace exists
check_workspace() {
    if [[ ! -d "$WORKSPACE" ]]; then
        echo -e "${YELLOW}[*] Workspace $WORKSPACE does not exist. Nothing to clean.${NC}"
        exit 0
    fi
}

# Function to unmount all chroot filesystems
unmount_chroot() {
    local chroot_path="$WORKSPACE/chroot"
    
    if [[ -d "$chroot_path" ]]; then
        echo -e "${YELLOW}[*] Checking for mounted filesystems in chroot...${NC}"
        
        # Unmount in reverse order of mounting
        local mount_points=("dev/pts" "dev" "proc" "sys" "run")
        
        for mount_point in "${mount_points[@]}"; do
            local full_path="$chroot_path/$mount_point"
            if [[ -d "$full_path" ]]; then
                safe_unmount "$full_path"
            fi
        done
        
        # Check for any other mounts under chroot
        echo -e "${YELLOW}[*] Checking for any remaining mounts under chroot...${NC}"
        while read -r mount_line; do
            local mount_path=$(echo "$mount_line" | awk '{print $3}')
            safe_unmount "$mount_path"
        done < <(mount | grep "$chroot_path" | sort -r)
    fi
}

# Function to kill any processes using the workspace
kill_workspace_processes() {
    echo -e "${YELLOW}[*] Checking for processes using workspace...${NC}"
    
    # Find processes with open files in workspace
    local pids=$(lsof +D "$WORKSPACE" 2>/dev/null | grep -v "^COMMAND" | awk '{print $2}' | sort -u)
    
    if [[ -n "$pids" ]]; then
        echo -e "${YELLOW}[*] Found processes using workspace: $pids${NC}"
        echo -e "${YELLOW}[*] Terminating processes...${NC}"
        
        for pid in $pids; do
            if kill -TERM "$pid" 2>/dev/null; then
                echo -e "${GREEN}[+] Terminated process $pid${NC}"
            fi
        done
        
        # Give processes time to terminate
        sleep 2
        
        # Force kill any remaining processes
        pids=$(lsof +D "$WORKSPACE" 2>/dev/null | grep -v "^COMMAND" | awk '{print $2}' | sort -u)
        if [[ -n "$pids" ]]; then
            echo -e "${YELLOW}[*] Force killing remaining processes...${NC}"
            for pid in $pids; do
                kill -KILL "$pid" 2>/dev/null || true
            done
        fi
    else
        echo -e "${GREEN}[+] No processes using workspace${NC}"
    fi
}

# Function to remove workspace directory
remove_workspace() {
    echo -e "${YELLOW}[*] Removing workspace directory...${NC}"
    
    # First try normal removal
    if rm -rf "$WORKSPACE" 2>/dev/null; then
        echo -e "${GREEN}[+] Successfully removed workspace${NC}"
    else
        # If that fails, try with sudo and more aggressive options
        echo -e "${YELLOW}[*] Trying forceful removal...${NC}"
        
        # Change permissions to ensure we can delete
        find "$WORKSPACE" -type d -exec chmod 777 {} \; 2>/dev/null || true
        find "$WORKSPACE" -type f -exec chmod 666 {} \; 2>/dev/null || true
        
        # Remove with sudo
        if sudo rm -rf "$WORKSPACE"; then
            echo -e "${GREEN}[+] Successfully removed workspace with sudo${NC}"
        else
            echo -e "${RED}[!] Failed to remove workspace. Manual intervention may be required.${NC}"
            return 1
        fi
    fi
    return 0
}

# Function to clean build artifacts
clean_build_artifacts() {
    echo -e "${YELLOW}[*] Cleaning build artifacts...${NC}"
    
    # Remove build progress file if it exists
    if [[ -f "$WORKSPACE/build_progress.json" ]]; then
        rm -f "$WORKSPACE/build_progress.json"
        echo -e "${GREEN}[+] Removed build progress file${NC}"
    fi
    
    # Clean apt cache if it exists
    if [[ -d "$WORKSPACE/apt_cache" ]]; then
        rm -rf "$WORKSPACE/apt_cache"/*
        echo -e "${GREEN}[+] Cleaned apt cache${NC}"
    fi
}

# Main cleanup process
main() {
    echo -e "${YELLOW}[*] Starting cleanup of workspace: $WORKSPACE${NC}"
    echo
    
    # Check if workspace exists
    check_workspace
    
    # Step 1: Unmount all filesystems
    unmount_chroot
    
    # Step 2: Kill any processes using the workspace
    kill_workspace_processes
    
    # Step 3: Clean build artifacts (optional, before full removal)
    # clean_build_artifacts
    
    # Step 4: Remove the workspace directory
    remove_workspace
    
    echo
    echo -e "${GREEN}[+] Cleanup completed successfully!${NC}"
    echo
    
    # Verify cleanup
    if [[ -d "$WORKSPACE" ]]; then
        echo -e "${RED}[!] Warning: Workspace directory still exists!${NC}"
        echo -e "${YELLOW}    You may need to manually remove it with:${NC}"
        echo -e "    sudo rm -rf $WORKSPACE"
        exit 1
    else
        echo -e "${GREEN}[+] Workspace has been completely removed.${NC}"
    fi
}

# Handle script arguments
case "${1:-}" in
    -h|--help)
        echo "Usage: $0 [WORKSPACE_PATH]"
        echo
        echo "Safely cleans up the Z-FORGE build workspace."
        echo
        echo "Arguments:"
        echo "  WORKSPACE_PATH    Path to workspace (default: /tmp/zforge_workspace)"
        echo
        echo "Examples:"
        echo "  $0                    # Clean default workspace"
        echo "  $0 /custom/workspace  # Clean custom workspace"
        exit 0
        ;;
    "")
        # No argument, use default
        ;;
    *)
        # Custom workspace path
        WORKSPACE="$1"
        ;;
esac

# Run main cleanup
main
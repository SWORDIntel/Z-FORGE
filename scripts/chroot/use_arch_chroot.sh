#!/bin/bash
# Script to use arch-chroot with Z-FORGE
# This provides better chroot handling than standard chroot

set -e

# Configuration - Use original user's HOME, not root's
ORIGINAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}
ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER" 2>/dev/null || echo "$HOME")
CHROOT_PATH="${1:-$ORIGINAL_HOME/zforge_workspace/chroot}"

echo "═══════════════════════════════════════════════════════════════════"
echo "           Z-FORGE arch-chroot Helper"
echo "═══════════════════════════════════════════════════════════════════"

# Check if arch-chroot is available
if ! command -v arch-chroot &> /dev/null; then
    echo "arch-chroot not found. Installing arch-install-scripts..."
    sudo apt-get update
    sudo apt-get install -y arch-install-scripts || {
        echo "Failed to install arch-install-scripts"
        echo "Falling back to standard chroot"
        USE_ARCH_CHROOT=false
    }
else
    USE_ARCH_CHROOT=true
fi

# Create chroot if it doesn't exist
if [ ! -d "$CHROOT_PATH" ]; then
    echo ""
    echo "Chroot not found at: $CHROOT_PATH"
    echo "Creating fresh chroot with bootstrap..."
    "$(dirname "$0")/bootstrap_chroot.sh" auto "$CHROOT_PATH"
fi

# Verify chroot exists
if [ ! -d "$CHROOT_PATH" ]; then
    echo "ERROR: Chroot not found at: $CHROOT_PATH"
    echo "Run: $(dirname "$0")/bootstrap_chroot.sh auto $CHROOT_PATH"
    exit 1
fi

echo ""
echo "Original user: $ORIGINAL_USER"
echo "Using chroot at: $CHROOT_PATH"
echo ""

# Function to cleanup mounts
cleanup_mounts() {
    if [ "$USE_STANDARD_CHROOT" = true ]; then
        echo "Cleaning up bind mounts..."
        for fs in dev/pts dev proc sys; do
            if mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
                sudo umount "$CHROOT_PATH/$fs" 2>/dev/null || true
            fi
        done
    fi
}

# Comprehensive cleanup function for all exit scenarios
force_cleanup() {
    echo "Force cleaning up all mounts for: $CHROOT_PATH"
    # Try to unmount everything regardless of tracking variables
    for fs in dev/pts dev proc sys; do
        if mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
            echo "Unmounting $CHROOT_PATH/$fs"
            sudo umount -l "$CHROOT_PATH/$fs" 2>/dev/null || true  # lazy unmount
            sudo umount "$CHROOT_PATH/$fs" 2>/dev/null || true     # normal unmount
        fi
    done
}

# Function to enter chroot
enter_chroot() {
    # Check environment variable for override
    if [ "$ENABLE_ARCH_CHROOT" = "1" ]; then
        echo "ENABLE_ARCH_CHROOT=1 detected, attempting arch-chroot..."
        if [ "$USE_ARCH_CHROOT" = true ]; then
            echo "Testing arch-chroot safety..."
            # Test with timeout
            if timeout 3 sudo arch-chroot "$CHROOT_PATH" /bin/true 2>/dev/null; then
                echo "arch-chroot test passed, using arch-chroot..."
                sudo arch-chroot "$CHROOT_PATH" "$@"
            else
                echo "arch-chroot test failed, falling back to standard chroot..."
                enter_standard_chroot "$@"
            fi
        else
            enter_standard_chroot "$@"
        fi
    else
        # Default to safe standard chroot
        echo "Using standard chroot (set ENABLE_ARCH_CHROOT=1 to try arch-chroot)..."
        enter_standard_chroot "$@"
    fi
}

# Function for standard chroot
enter_standard_chroot() {
    echo "Entering chroot with standard method..."
    USE_STANDARD_CHROOT=true
    
    # Mount necessary filesystems
    for fs in proc sys dev dev/pts; do
        if ! mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
            sudo mkdir -p "$CHROOT_PATH/$fs"
            case "$fs" in
                "proc")
                    sudo mount -t proc proc "$CHROOT_PATH/proc"
                    ;;
                "sys")
                    sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"
                    ;;
                "dev")
                    sudo mount --bind /dev "$CHROOT_PATH/dev"
                    ;;
                "dev/pts")
                    sudo mount --bind /dev/pts "$CHROOT_PATH/dev/pts"
                    ;;
            esac
        fi
    done
    
    # Copy resolv.conf
    sudo cp -L /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
    
    # Set up comprehensive traps for all exit scenarios
    trap 'echo ""; echo "Interrupted! Cleaning up..."; force_cleanup; exit 130' INT
    trap 'echo ""; echo "Terminated! Cleaning up..."; force_cleanup; exit 143' TERM
    trap 'force_cleanup' EXIT
    trap 'force_cleanup; exit 1' QUIT HUP
    
    # Enter chroot with timeout protection
    echo "Entering chroot... (Press Ctrl+C to exit)"
    timeout 3600 sudo chroot "$CHROOT_PATH" "$@" || {
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "Chroot session timed out after 1 hour"
        else
            echo "Chroot exited with code: $exit_code"
        fi
        return $exit_code
    }
}

# Handle special commands
if [ "$1" = "cleanup" ]; then
    echo "Manual cleanup requested..."
    force_cleanup
    exit 0
fi

# If no command provided, enter interactive shell
if [ $# -le 1 ]; then
    echo "Entering interactive shell..."
    echo "Type 'exit' to leave chroot"
    echo ""
    enter_chroot /bin/bash
else
    # Execute command in chroot
    shift  # Remove first argument (chroot path)
    enter_chroot "$@"
fi

echo ""
echo "Exited chroot successfully"
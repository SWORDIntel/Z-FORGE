#!/bin/bash
# Smart chroot wrapper that detects the best method for the environment
# Uses arch-chroot when safe, falls back to standard chroot when needed

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "           Z-FORGE Smart Chroot Wrapper"
echo "═══════════════════════════════════════════════════════════════════"

# Configuration - Use original user's HOME, not root's
ORIGINAL_USER=${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}
ORIGINAL_HOME=$(eval echo "~$ORIGINAL_USER" 2>/dev/null || echo "$HOME")
CHROOT_PATH="${1:-$ORIGINAL_HOME/zforge_workspace/chroot}"

# Detect environment capabilities
detect_environment() {
    local env_score=0
    local env_report=""
    
    echo "Detecting environment capabilities..."
    echo ""
    
    # Check for systemd
    if systemctl --version &>/dev/null; then
        env_report+="✅ systemd detected\n"
        ((env_score+=3))
    else
        env_report+="❌ systemd not found\n"
    fi
    
    # Check for systemd-nspawn
    if command -v systemd-nspawn &>/dev/null; then
        env_report+="✅ systemd-nspawn available\n"
        ((env_score+=2))
    else
        env_report+="⚠️  systemd-nspawn not found\n"
    fi
    
    # Check kernel namespace support
    if [ -f /proc/self/ns/mnt ]; then
        env_report+="✅ Mount namespaces supported\n"
        ((env_score+=2))
    else
        env_report+="❌ Mount namespaces not supported\n"
    fi
    
    # Check if running in container/VM
    if grep -q "docker\|lxc\|containerd" /proc/1/cgroup 2>/dev/null; then
        env_report+="⚠️  Running in container (arch-chroot may fail)\n"
        ((env_score-=3))
    fi
    
    # Check if arch-chroot is installed
    if command -v arch-chroot &>/dev/null; then
        env_report+="✅ arch-chroot installed\n"
        ((env_score+=1))
    else
        env_report+="❌ arch-chroot not installed\n"
        ((env_score-=10))
    fi
    
    echo -e "$env_report"
    echo "Environment score: $env_score/8"
    echo ""
    
    # Decide based on score
    if [ $env_score -ge 5 ]; then
        echo "✅ Environment suitable for arch-chroot"
        return 0
    else
        echo "⚠️  Environment not ideal for arch-chroot, using standard chroot"
        return 1
    fi
}

# Test arch-chroot with timeout
test_arch_chroot() {
    echo "Testing arch-chroot functionality..."
    
    # Try a simple command with short timeout
    if timeout 5 sudo arch-chroot "$CHROOT_PATH" /bin/true 2>/dev/null; then
        echo "✅ arch-chroot test successful"
        return 0
    else
        echo "❌ arch-chroot test failed or timed out"
        return 1
    fi
}

# Function to cleanup mounts
cleanup_mounts() {
    echo "Cleaning up mounts..."
    for fs in dev/pts dev proc sys; do
        if mountpoint -q "$CHROOT_PATH/$fs" 2>/dev/null; then
            sudo umount -l "$CHROOT_PATH/$fs" 2>/dev/null || true
        fi
    done
}

# Standard chroot method
enter_standard_chroot() {
    echo "Using standard chroot method..."
    
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
    
    # Set up traps
    trap 'cleanup_mounts' EXIT INT TERM
    
    # Enter chroot
    shift # Remove chroot path argument
    sudo chroot "$CHROOT_PATH" "$@"
}

# arch-chroot method
enter_arch_chroot() {
    echo "Using arch-chroot method..."
    shift # Remove chroot path argument
    
    # Use timeout to prevent hanging
    timeout 3600 sudo arch-chroot "$CHROOT_PATH" "$@" || {
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "Session timed out after 1 hour"
        fi
        return $exit_code
    }
}

# Main logic
main() {
    # Check if chroot exists
    if [ ! -d "$CHROOT_PATH" ]; then
        echo "ERROR: Chroot not found at: $CHROOT_PATH"
        exit 1
    fi
    
    echo "Using chroot at: $CHROOT_PATH"
    echo "Original user: $ORIGINAL_USER"
    echo ""
    
    # Allow override via environment variable
    if [ "$FORCE_STANDARD_CHROOT" = "1" ]; then
        echo "FORCE_STANDARD_CHROOT=1 detected, using standard chroot"
        enter_standard_chroot "$@"
    elif [ "$FORCE_ARCH_CHROOT" = "1" ]; then
        echo "FORCE_ARCH_CHROOT=1 detected, using arch-chroot"
        enter_arch_chroot "$@"
    else
        # Auto-detect best method
        if detect_environment && test_arch_chroot; then
            enter_arch_chroot "$@"
        else
            enter_standard_chroot "$@"
        fi
    fi
}

# Run main function with all arguments
main "$@"
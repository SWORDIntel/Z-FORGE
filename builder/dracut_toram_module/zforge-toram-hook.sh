#!/bin/bash
# zforge-toram-hook.sh - Enhanced Live ISO to RAM Loader v2.0
# Supports multiple live ISO formats with progress indication and verification

set -euo pipefail

# Configuration
readonly SCRIPT_NAME="Z-FORGE"
readonly MIN_FREE_RAM_MB=512  # Minimum free RAM to keep after loading
readonly BUFFER_PERCENT=15    # Buffer percentage for RAM allocation
readonly BLOCK_SIZE="1M"      # Block size for dd operations

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}${SCRIPT_NAME}:${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}${SCRIPT_NAME}:${NC} WARNING - $*"
}

log_error() {
    echo -e "${RED}${SCRIPT_NAME}:${NC} ERROR - $*" >&2
}

# Progress bar function
show_progress() {
    local current=$1
    local total=$2
    local width=50
    local percent=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))
    
    printf "\r["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "] %3d%% (%d/%d MB)" "$percent" "$current" "$total"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Script failed with exit code $exit_code"
        # Cleanup any partial mounts
        for mount_point in /run/initramfs/toram /run/initramfs/live /mnt; do
            if mountpoint -q "$mount_point" 2>/dev/null; then
                umount "$mount_point" 2>/dev/null || true
            fi
        done
    fi
}

trap cleanup EXIT

# Check if toram boot parameter is set
if ! grep -qE '(^|[[:space:]])toram([[:space:]]|$)' /proc/cmdline; then
    exit 0
fi

log_info "toram boot parameter detected, initializing RAM copy..."

# Function to find live media paths
find_squashfs_paths() {
    local paths=(
        "/LiveOS/squashfs.img"
        "/live/filesystem.squashfs"
        "/casper/filesystem.squashfs"
        "/antiX/linuxfs"
        "/arch/airootfs.sfs"
        "/*.sfs"
        "/*.squashfs"
    )
    echo "${paths[@]}"
}

# Function to detect live media device
detect_live_device() {
    local device=""
    local found_path=""
    
    # Check all block devices
    for dev in /dev/sr* /dev/sd* /dev/nvme*n* /dev/mmcblk*; do
        [ -b "$dev" ] || continue
        
        # Try to mount the device
        if mount -o ro "$dev" /mnt 2>/dev/null; then
            # Check for known squashfs locations
            for path in $(find_squashfs_paths); do
                for file in /mnt${path}; do
                    if [ -f "$file" ]; then
                        device="$dev"
                        found_path="${file#/mnt}"
                        umount /mnt
                        echo "$device:$found_path"
                        return 0
                    fi
                done
            done
            umount /mnt
        fi
    done
    
    return 1
}

# Get memory information
get_memory_info() {
    local total_ram=$(awk '/^MemTotal:/ {print int($2/1024)}' /proc/meminfo)
    local free_ram=$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
    echo "$total_ram:$free_ram"
}

# Main execution
main() {
    # Detect live device
    log_info "Searching for live media device..."
    if ! device_info=$(detect_live_device); then
        log_error "Could not find live media device"
        return 1
    fi
    
    LIVE_DEV="${device_info%%:*}"
    SQUASHFS_PATH="${device_info#*:}"
    log_info "Found live media on $LIVE_DEV with image at $SQUASHFS_PATH"
    
    # Get memory information
    IFS=':' read -r total_ram avail_ram <<< "$(get_memory_info)"
    log_info "System RAM: Total=${total_ram}MB, Available=${avail_ram}MB"
    
    # Mount live device
    mkdir -p /run/initramfs/live
    if ! mount -o ro "$LIVE_DEV" /run/initramfs/live; then
        log_error "Failed to mount live device $LIVE_DEV"
        return 1
    fi
    
    # Calculate required size
    local squashfs_file="/run/initramfs/live${SQUASHFS_PATH}"
    if [ ! -f "$squashfs_file" ]; then
        log_error "Squashfs image not found at $squashfs_file"
        umount /run/initramfs/live
        return 1
    fi
    
    local live_size=$(stat -c%s "$squashfs_file" 2>/dev/null | awk '{print int($1/1048576)}')
    local needed_ram=$((live_size * (100 + BUFFER_PERCENT) / 100))
    local final_free_ram=$((avail_ram - needed_ram))
    
    log_info "Live image size: ${live_size}MB"
    log_info "Required RAM (with ${BUFFER_PERCENT}% buffer): ${needed_ram}MB"
    log_info "RAM remaining after load: ${final_free_ram}MB"
    
    # Check if we have enough RAM
    if [ "$final_free_ram" -lt "$MIN_FREE_RAM_MB" ]; then
        log_error "Insufficient RAM (need ${needed_ram}MB + ${MIN_FREE_RAM_MB}MB free)"
        log_error "Available: ${avail_ram}MB, Required: $((needed_ram + MIN_FREE_RAM_MB))MB"
        umount /run/initramfs/live
        return 1
    fi
    
    # Create tmpfs
    log_info "Creating ${needed_ram}MB tmpfs for toram..."
    mkdir -p /run/initramfs/toram
    if ! mount -t tmpfs -o size=${needed_ram}m tmpfs /run/initramfs/toram; then
        log_error "Failed to create tmpfs"
        umount /run/initramfs/live
        return 1
    fi
    
    # Copy with progress indication
    log_info "Copying live image to RAM..."
    
    # Create directory structure
    local target_dir="/run/initramfs/toram$(dirname "$SQUASHFS_PATH")"
    mkdir -p "$target_dir"
    
    # Copy with dd for progress tracking
    local copied=0
    local block_count=$((live_size))
    
    if command -v pv >/dev/null 2>&1; then
        # Use pv if available for better progress
        pv -pterb "$squashfs_file" > "${target_dir}/$(basename "$SQUASHFS_PATH")"
    else
        # Fall back to dd with manual progress
        (
            while dd if="$squashfs_file" of="${target_dir}/$(basename "$SQUASHFS_PATH")" \
                     bs="$BLOCK_SIZE" count=1 skip=$copied 2>/dev/null; do
                copied=$((copied + 1))
                show_progress $copied $block_count
                [ $copied -ge $block_count ] && break
            done
            echo  # New line after progress
        )
    fi
    
    # Copy any additional files in the live directory
    log_info "Copying additional live files..."
    local src_dir="/run/initramfs/live$(dirname "$SQUASHFS_PATH")"
    if [ -d "$src_dir" ]; then
        find "$src_dir" -mindepth 1 -maxdepth 1 -name "*.img" -o -name "*.sfs" | while read -r file; do
            [ "$file" = "$squashfs_file" ] && continue
            local basename=$(basename "$file")
            log_info "Copying $basename..."
            cp -a "$file" "$target_dir/"
        done
    fi
    
    # Verify copy
    log_info "Verifying copied data..."
    local src_sum=$(md5sum "$squashfs_file" 2>/dev/null | cut -d' ' -f1)
    local dst_sum=$(md5sum "${target_dir}/$(basename "$SQUASHFS_PATH")" 2>/dev/null | cut -d' ' -f1)
    
    if [ -n "$src_sum" ] && [ "$src_sum" != "$dst_sum" ]; then
        log_error "Verification failed! Source and destination checksums don't match"
        umount /run/initramfs/toram
        umount /run/initramfs/live
        return 1
    fi
    
    # Unmount original device
    umount /run/initramfs/live
    
    # Setup bind mount
    mount --bind /run/initramfs/toram /run/initramfs/live
    
    # Success message
    log_info "Successfully loaded live image to RAM"
    log_info "Boot media can now be safely removed"
    
    # Optional: Eject CD/DVD if applicable
    if [[ "$LIVE_DEV" =~ ^/dev/sr ]]; then
        eject "$LIVE_DEV" 2>/dev/null || true
    fi
    
    return 0
}

# Execute main function
main "$@"

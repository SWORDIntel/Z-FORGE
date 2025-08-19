#!/bin/bash
#
# Z-FORGE ZFS Stream Deployment System
# Stream ZFS datasets directly to multiple servers for instant deployment
# Much faster than ISO-based deployment!
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="/tmp/zforge-workspace-proxmox"
SNAPSHOT_NAME="@deploy-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

# Create ZFS pool from built system
create_zfs_source() {
    local chroot_dir="${1:-$WORKSPACE/chroot}"
    local pool_name="zforge-deploy"
    local dataset="$pool_name/proxmox-root"
    
    log_info "Creating ZFS source pool for streaming..."
    
    # Create a file-backed pool for the source
    local pool_file="/tmp/zforge-deploy.img"
    if [[ ! -f "$pool_file" ]]; then
        log_info "Creating 10GB sparse file for ZFS pool..."
        truncate -s 10G "$pool_file"
    fi
    
    # Create pool if not exists
    if ! zpool list "$pool_name" &>/dev/null; then
        log_info "Creating ZFS pool: $pool_name"
        zpool create -f "$pool_name" "$pool_file"
        
        # Create dataset with optimal settings for Proxmox
        zfs create -o compression=lz4 -o atime=off -o xattr=sa "$dataset"
    fi
    
    # Copy chroot contents to ZFS dataset
    log_info "Copying system to ZFS dataset..."
    rsync -axHAXS --info=progress2 "$chroot_dir/" "/$(echo $dataset | sed 's|/|/|')"
    
    # Create snapshot for streaming
    log_info "Creating snapshot: $dataset$SNAPSHOT_NAME"
    zfs snapshot "$dataset$SNAPSHOT_NAME"
    
    echo "$dataset$SNAPSHOT_NAME"
}

# Stream to single server via SSH
stream_to_server() {
    local server_ip="$1"
    local target_pool="${2:-rpool}"
    local target_dataset="${3:-ROOT/proxmox}"
    local source_snapshot="$4"
    
    log_info "Streaming to server: $server_ip"
    log_info "Target: $target_pool/$target_dataset"
    
    # Check SSH connectivity
    if ! ssh -o ConnectTimeout=5 "root@$server_ip" "echo connected" &>/dev/null; then
        log_error "Cannot connect to $server_ip"
        return 1
    fi
    
    # Check if target pool exists
    if ! ssh "root@$server_ip" "zpool list $target_pool" &>/dev/null; then
        log_warn "Creating target pool $target_pool on $server_ip"
        ssh "root@$server_ip" "
            # Create pool on first available disk
            DISK=\$(lsblk -dn -o NAME,TYPE | grep disk | head -1 | awk '{print \$1}')
            if [[ -n \"\$DISK\" ]]; then
                zpool create -f -o ashift=12 -O compression=lz4 -O atime=off $target_pool /dev/\$DISK
            else
                echo 'No available disk found'
                exit 1
            fi
        "
    fi
    
    # Stream the dataset
    log_info "Starting ZFS stream transfer..."
    
    # Calculate size for progress
    local size=$(zfs get -Hp -o value referenced "$source_snapshot")
    local size_mb=$((size / 1048576))
    log_info "Dataset size: ${size_mb}MB"
    
    # Stream with progress monitoring
    zfs send -v "$source_snapshot" | pv -s "$size" | \
        ssh "root@$server_ip" "zfs receive -F $target_pool/$target_dataset"
    
    # Set bootfs property
    ssh "root@$server_ip" "zpool set bootfs=$target_pool/$target_dataset $target_pool"
    
    # Configure boot environment
    log_info "Configuring boot environment on $server_ip..."
    ssh "root@$server_ip" "
        # Mount the new root
        mkdir -p /mnt/newroot
        mount -t zfs $target_pool/$target_dataset /mnt/newroot
        
        # Update fstab
        echo '$target_pool/$target_dataset / zfs defaults 0 0' > /mnt/newroot/etc/fstab
        
        # Install bootloader
        mount --bind /dev /mnt/newroot/dev
        mount --bind /proc /mnt/newroot/proc
        mount --bind /sys /mnt/newroot/sys
        
        chroot /mnt/newroot grub-install /dev/\$(lsblk -dn -o NAME,TYPE | grep disk | head -1 | awk '{print \$1}')
        chroot /mnt/newroot update-grub
        
        # Cleanup
        umount /mnt/newroot/{dev,proc,sys}
        umount /mnt/newroot
    "
    
    log_info "Deployment complete to $server_ip"
}

# Mass parallel streaming
mass_stream_deploy() {
    local servers_file="${1:-servers.txt}"
    local source_snapshot="$2"
    local max_parallel="${3:-5}"
    
    if [[ ! -f "$servers_file" ]]; then
        log_error "Server list not found: $servers_file"
        cat > "$servers_file" << 'EOF'
# Z-FORGE Server List for ZFS Streaming
# Format: IP_ADDRESS POOL DATASET
192.168.1.101 rpool ROOT/proxmox
192.168.1.102 rpool ROOT/proxmox
192.168.1.103 rpool ROOT/proxmox
EOF
        log_info "Created example servers.txt - please edit and retry"
        return 1
    fi
    
    log_info "Starting mass ZFS stream deployment"
    log_info "Max parallel streams: $max_parallel"
    
    # Read servers and deploy
    local count=0
    local pids=()
    
    while IFS=' ' read -r ip pool dataset; do
        # Skip comments and empty lines
        [[ "$ip" =~ ^#.*$ ]] && continue
        [[ -z "$ip" ]] && continue
        
        # Wait if we've hit the parallel limit
        while [[ ${#pids[@]} -ge $max_parallel ]]; do
            # Check for completed streams
            local new_pids=()
            for pid in "${pids[@]}"; do
                if kill -0 "$pid" 2>/dev/null; then
                    new_pids+=("$pid")
                fi
            done
            pids=("${new_pids[@]}")
            sleep 2
        done
        
        # Start streaming in background
        log_info "Starting stream to $ip ($(( ++count )))"
        stream_to_server "$ip" "$pool" "$dataset" "$source_snapshot" &
        pids+=($!)
        
        # Brief delay between starts
        sleep 1
    done < "$servers_file"
    
    # Wait for all streams to complete
    log_info "Waiting for all streams to complete..."
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    log_info "Mass deployment complete!"
}

# Create incremental stream for updates
create_incremental_stream() {
    local dataset="$1"
    local prev_snapshot="$2"
    local new_snapshot="${dataset}@update-$(date +%Y%m%d-%H%M%S)"
    
    log_info "Creating incremental snapshot: $new_snapshot"
    zfs snapshot "$new_snapshot"
    
    log_info "Generating incremental stream..."
    local stream_file="/tmp/zforge-incremental-$(date +%Y%m%d-%H%M%S).zfs"
    
    zfs send -i "$prev_snapshot" "$new_snapshot" | pv > "$stream_file"
    
    log_info "Incremental stream saved to: $stream_file"
    echo "$stream_file"
}

# Apply incremental update
apply_incremental_update() {
    local server_ip="$1"
    local stream_file="$2"
    local target_dataset="$3"
    
    log_info "Applying incremental update to $server_ip"
    
    # Transfer and apply the incremental stream
    pv "$stream_file" | ssh "root@$server_ip" "zfs receive -F $target_dataset"
    
    log_info "Incremental update applied to $server_ip"
}

# Replicate to backup servers
setup_replication() {
    local primary="$1"
    local replicas="$2"  # comma-separated list
    local dataset="$3"
    
    log_info "Setting up ZFS replication"
    log_info "Primary: $primary"
    log_info "Replicas: $replicas"
    
    # Create replication script
    cat > /tmp/zfs-replicate.sh << EOF
#!/bin/bash
# ZFS Replication Script
PRIMARY="$primary"
REPLICAS="$replicas"
DATASET="$dataset"

while true; do
    # Create snapshot
    SNAPSHOT="\${DATASET}@auto-\$(date +%Y%m%d-%H%M%S)"
    ssh root@\$PRIMARY "zfs snapshot \$SNAPSHOT"
    
    # Replicate to each replica
    for REPLICA in \${REPLICAS//,/ }; do
        ssh root@\$PRIMARY "zfs send \$SNAPSHOT" | \\
            ssh root@\$REPLICA "zfs receive -F \$DATASET" &
    done
    
    wait
    sleep 3600  # Replicate hourly
done
EOF
    
    chmod +x /tmp/zfs-replicate.sh
    log_info "Replication script created: /tmp/zfs-replicate.sh"
}

# Main menu
show_menu() {
    echo ""
    echo "============================================"
    echo "   Z-FORGE ZFS Stream Deployment System"
    echo "============================================"
    echo ""
    echo "1) Create ZFS source from build"
    echo "2) Stream to single server"
    echo "3) Mass stream deployment"
    echo "4) Create incremental update"
    echo "5) Apply incremental update"
    echo "6) Setup replication"
    echo "7) Monitor ZFS streams"
    echo "q) Quit"
    echo ""
    echo -n "Select option: "
}

# Main execution
main() {
    log_info "Z-FORGE ZFS Stream Deployment System"
    
    # Check for root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
    
    # Check for ZFS
    if ! command -v zfs &>/dev/null; then
        log_error "ZFS not installed. Please install zfsutils-linux"
        exit 1
    fi
    
    local source_snapshot=""
    
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1)
                source_snapshot=$(create_zfs_source)
                log_info "Source snapshot created: $source_snapshot"
                ;;
            2)
                read -p "Enter server IP: " server_ip
                read -p "Enter target pool [rpool]: " pool
                pool="${pool:-rpool}"
                read -p "Enter target dataset [ROOT/proxmox]: " dataset
                dataset="${dataset:-ROOT/proxmox}"
                
                if [[ -z "$source_snapshot" ]]; then
                    log_error "Please create source snapshot first (option 1)"
                else
                    stream_to_server "$server_ip" "$pool" "$dataset" "$source_snapshot"
                fi
                ;;
            3)
                if [[ -z "$source_snapshot" ]]; then
                    log_error "Please create source snapshot first (option 1)"
                else
                    mass_stream_deploy "servers.txt" "$source_snapshot"
                fi
                ;;
            4)
                read -p "Enter dataset: " dataset
                read -p "Enter previous snapshot: " prev_snap
                create_incremental_stream "$dataset" "$prev_snap"
                ;;
            5)
                read -p "Enter server IP: " server_ip
                read -p "Enter stream file: " stream_file
                read -p "Enter target dataset: " dataset
                apply_incremental_update "$server_ip" "$stream_file" "$dataset"
                ;;
            6)
                read -p "Enter primary server IP: " primary
                read -p "Enter replica IPs (comma-separated): " replicas
                read -p "Enter dataset: " dataset
                setup_replication "$primary" "$replicas" "$dataset"
                ;;
            7)
                watch -n 1 "zfs list -t snapshot | grep deploy; echo; zpool iostat -v 1 1"
                ;;
            q|Q)
                log_info "Exiting..."
                exit 0
                ;;
            *)
                log_error "Invalid option"
                ;;
        esac
    done
}

# Run main function
main "$@"
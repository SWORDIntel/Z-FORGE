#!/bin/bash
# Z-FORGE Universal NVMe Optimization Script
# Detects and optimizes various NVMe SSDs including Sabrent, Samsung, WD, Intel

set -euo pipefail

echo "════════════════════════════════════════════════════════════════"
echo "          Universal NVMe SSD Optimization Script"
echo "════════════════════════════════════════════════════════════════"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "[!] This script must be run as root"
   exit 1
fi

# Arrays for drive detection and settings
declare -A NVME_DRIVES
declare -A NVME_OPTIMIZATIONS

# Function to detect all NVMe drives
detect_nvme_drives() {
    echo "[*] Detecting NVMe drives..."
    local found=0
    
    for nvme in /sys/block/nvme*; do
        if [[ -d "$nvme" && -f "$nvme/device/model" ]]; then
            device=$(basename "$nvme")
            model=$(cat "$nvme/device/model" 2>/dev/null | tr -d '\000' | xargs)
            
            if [[ -n "$model" ]]; then
                NVME_DRIVES[$device]="$model"
                echo "[+] Found: $device - $model"
                found=1
                
                # Determine optimizations based on model
                determine_optimizations "$device" "$model"
            fi
        fi
    done
    
    if [[ $found -eq 0 ]]; then
        echo "[!] No NVMe drives detected"
        return 1
    fi
    
    return 0
}

# Function to determine drive-specific optimizations
determine_optimizations() {
    local device=$1
    local model=$2
    local model_upper=$(echo "$model" | tr '[:lower:]' '[:upper:]')
    
    # Default settings
    local queue_depth=256
    local read_ahead_kb=2048
    local scheduler="none"
    local iostats=0
    
    # Intel 750 Series
    if [[ "$model_upper" =~ "INTEL SSDPE" ]] || [[ "$model_upper" =~ "750" ]]; then
        echo "  └─ Detected Intel 750 Series"
        queue_depth=256
        read_ahead_kb=2048
        
    # Sabrent Rocket series
    elif [[ "$model_upper" =~ "SABRENT" ]] || [[ "$model_upper" =~ "ROCKET" ]]; then
        echo "  └─ Detected Sabrent Rocket NVMe"
        queue_depth=1024  # Sabrent handles high queue depths well
        read_ahead_kb=4096  # Better for sequential workloads
        
    # Samsung 970/980/990 series
    elif [[ "$model_upper" =~ "SAMSUNG" ]] && [[ "$model_upper" =~ "9[789]0" ]]; then
        echo "  └─ Detected Samsung NVMe series"
        queue_depth=512
        read_ahead_kb=2048
        
    # WD Black / SN850 series
    elif [[ "$model_upper" =~ "WD" ]] || [[ "$model_upper" =~ "WESTERN DIGITAL" ]] || [[ "$model_upper" =~ "SN[78]50" ]]; then
        echo "  └─ Detected WD Black NVMe series"
        queue_depth=512
        read_ahead_kb=2048
        
    # Crucial P5/P5 Plus
    elif [[ "$model_upper" =~ "CRUCIAL" ]] || [[ "$model_upper" =~ "CT[0-9]+P5" ]]; then
        echo "  └─ Detected Crucial NVMe series"
        queue_depth=512
        read_ahead_kb=2048
        
    # Kingston KC3000/Fury
    elif [[ "$model_upper" =~ "KINGSTON" ]] || [[ "$model_upper" =~ "KC3000" ]] || [[ "$model_upper" =~ "FURY" ]]; then
        echo "  └─ Detected Kingston NVMe series"
        queue_depth=512
        read_ahead_kb=2048
        
    # Corsair MP600/MP700
    elif [[ "$model_upper" =~ "CORSAIR" ]] || [[ "$model_upper" =~ "MP[67]00" ]]; then
        echo "  └─ Detected Corsair NVMe series"
        queue_depth=512
        read_ahead_kb=4096
        
    # Generic NVMe
    else
        echo "  └─ Using generic NVMe optimizations"
    fi
    
    # Store optimizations
    NVME_OPTIMIZATIONS["${device}_queue_depth"]=$queue_depth
    NVME_OPTIMIZATIONS["${device}_read_ahead_kb"]=$read_ahead_kb
    NVME_OPTIMIZATIONS["${device}_scheduler"]=$scheduler
    NVME_OPTIMIZATIONS["${device}_iostats"]=$iostats
}

# Apply universal NVMe core optimizations
apply_nvme_core_optimizations() {
    echo "[*] Applying NVMe core optimizations..."
    
    # Enable IO polling for lower latency
    echo 1 > /sys/module/nvme_core/parameters/io_poll 2>/dev/null || true
    echo 0 > /sys/module/nvme_core/parameters/io_poll_delay 2>/dev/null || true
    
    # Disable power saving for maximum performance
    echo 0 > /sys/module/nvme_core/parameters/default_ps_max_latency_us 2>/dev/null || true
    
    # Set IO timeout to 30 seconds
    echo 30 > /sys/module/nvme_core/parameters/io_timeout 2>/dev/null || true
    
    # Check kernel version for poll_queues support (4.20+)
    kernel_version=$(uname -r | cut -d. -f1,2)
    if command -v bc >/dev/null 2>&1 && (( $(echo "$kernel_version >= 4.20" | bc -l) )); then
        num_cores=$(nproc)
        echo "[*] Kernel 4.20+ detected, enabling poll_queues=$num_cores"
        
        # Create modprobe config
        cat > /etc/modprobe.d/nvme-optimizations.conf << EOF
# Universal NVMe optimizations
options nvme_core io_poll=1
options nvme_core io_poll_delay=0
options nvme_core default_ps_max_latency_us=0
options nvme_core io_timeout=30
options nvme poll_queues=$num_cores
EOF
    else
        # Older kernel config
        cat > /etc/modprobe.d/nvme-optimizations.conf << EOF
# Universal NVMe optimizations
options nvme_core io_poll=1
options nvme_core io_poll_delay=0
options nvme_core default_ps_max_latency_us=0
options nvme_core io_timeout=30
EOF
    fi
    
    # Disable NVMe APST (Autonomous Power State Transitions)
    for nvme_dev in /sys/class/nvme/nvme*; do
        if [[ -f "$nvme_dev/power/autonomous" ]]; then
            echo 0 > "$nvme_dev/power/autonomous" 2>/dev/null || true
            echo "[+] Disabled APST for $(basename $nvme_dev)"
        fi
    done
    
    echo "[+] NVMe core parameters configured"
}

# Apply per-device optimizations
apply_device_optimizations() {
    echo "[*] Applying per-device optimizations..."
    
    for device in "${!NVME_DRIVES[@]}"; do
        echo "[*] Optimizing $device (${NVME_DRIVES[$device]})..."
        
        # Get settings for this device
        queue_depth=${NVME_OPTIMIZATIONS["${device}_queue_depth"]}
        read_ahead_kb=${NVME_OPTIMIZATIONS["${device}_read_ahead_kb"]}
        scheduler=${NVME_OPTIMIZATIONS["${device}_scheduler"]}
        iostats=${NVME_OPTIMIZATIONS["${device}_iostats"]}
        
        # Apply settings
        echo $queue_depth > "/sys/block/$device/queue/nr_requests" 2>/dev/null || true
        echo $queue_depth > "/sys/block/$device/queue/queue_depth" 2>/dev/null || true
        echo $scheduler > "/sys/block/$device/queue/scheduler" 2>/dev/null || true
        echo $read_ahead_kb > "/sys/block/$device/queue/read_ahead_kb" 2>/dev/null || true
        echo 0 > "/sys/block/$device/queue/rotational" 2>/dev/null || true
        echo $iostats > "/sys/block/$device/queue/iostats" 2>/dev/null || true
        
        # Set optimal rq_affinity (1 = same CPU that submitted request)
        echo 1 > "/sys/block/$device/queue/rq_affinity" 2>/dev/null || true
        
        # Disable add_random (not needed for SSDs)
        echo 0 > "/sys/block/$device/queue/add_random" 2>/dev/null || true
        
        echo "[+] Optimized $device with queue_depth=$queue_depth, read_ahead=${read_ahead_kb}KB"
    done
}

# Apply ZFS optimizations for NVMe
apply_zfs_nvme_optimizations() {
    echo "[*] Checking for ZFS..."
    
    if ! lsmod | grep -q zfs; then
        echo "[!] ZFS module not loaded, skipping ZFS optimizations"
        return
    fi
    
    echo "[*] Applying ZFS optimizations for NVMe..."
    
    # Determine if we have high-performance NVMe (Sabrent, Samsung 980/990)
    local high_perf=0
    for model in "${NVME_DRIVES[@]}"; do
        model_upper=$(echo "$model" | tr '[:lower:]' '[:upper:]')
        if [[ "$model_upper" =~ "SABRENT" ]] || [[ "$model_upper" =~ "SAMSUNG.*9[89]0" ]]; then
            high_perf=1
            break
        fi
    done
    
    if [[ $high_perf -eq 1 ]]; then
        echo "[*] High-performance NVMe detected, applying aggressive settings"
        cat > /etc/modprobe.d/zfs-nvme-highperf.conf << EOF
# ZFS optimizations for high-performance NVMe
options zfs zfs_vdev_async_write_min_active=16
options zfs zfs_vdev_async_write_max_active=64
options zfs zfs_vdev_sync_write_min_active=32
options zfs zfs_vdev_sync_write_max_active=64
options zfs zfs_vdev_queue_depth_pct=400
options zfs zil_slog_bulk=1048576
options zfs zfs_prefetch_disable=0
options zfs zfs_txg_timeout=5
EOF
        
        # Apply runtime
        echo 16 > /sys/module/zfs/parameters/zfs_vdev_async_write_min_active 2>/dev/null || true
        echo 64 > /sys/module/zfs/parameters/zfs_vdev_async_write_max_active 2>/dev/null || true
        echo 32 > /sys/module/zfs/parameters/zfs_vdev_sync_write_min_active 2>/dev/null || true
        echo 64 > /sys/module/zfs/parameters/zfs_vdev_sync_write_max_active 2>/dev/null || true
        echo 400 > /sys/module/zfs/parameters/zfs_vdev_queue_depth_pct 2>/dev/null || true
        echo 1048576 > /sys/module/zfs/parameters/zil_slog_bulk 2>/dev/null || true
    else
        echo "[*] Standard NVMe detected, applying balanced settings"
        cat > /etc/modprobe.d/zfs-nvme.conf << EOF
# ZFS optimizations for standard NVMe
options zfs zfs_vdev_async_write_min_active=8
options zfs zfs_vdev_async_write_max_active=32
options zfs zfs_vdev_sync_write_min_active=16
options zfs zfs_vdev_sync_write_max_active=32
options zfs zfs_vdev_queue_depth_pct=300
options zfs zil_slog_bulk=786432
options zfs zfs_prefetch_disable=0
options zfs zfs_txg_timeout=5
EOF
        
        # Apply runtime
        echo 8 > /sys/module/zfs/parameters/zfs_vdev_async_write_min_active 2>/dev/null || true
        echo 32 > /sys/module/zfs/parameters/zfs_vdev_async_write_max_active 2>/dev/null || true
        echo 16 > /sys/module/zfs/parameters/zfs_vdev_sync_write_min_active 2>/dev/null || true
        echo 32 > /sys/module/zfs/parameters/zfs_vdev_sync_write_max_active 2>/dev/null || true
        echo 300 > /sys/module/zfs/parameters/zfs_vdev_queue_depth_pct 2>/dev/null || true
        echo 786432 > /sys/module/zfs/parameters/zil_slog_bulk 2>/dev/null || true
    fi
    
    echo 0 > /sys/module/zfs/parameters/zfs_prefetch_disable 2>/dev/null || true
    echo 5 > /sys/module/zfs/parameters/zfs_txg_timeout 2>/dev/null || true
    
    echo "[+] ZFS optimizations applied"
}

# Set CPU performance mode
set_cpu_performance() {
    echo "[*] Setting CPU to performance mode..."
    
    if which cpupower >/dev/null 2>&1; then
        cpupower frequency-set -g performance 2>/dev/null || true
    else
        for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
            echo performance > "$gov" 2>/dev/null || true
        done
    fi
    
    # Disable CPU idle states for lowest latency
    if [[ -f /sys/devices/system/cpu/cpu0/cpuidle/state2/disable ]]; then
        for state in /sys/devices/system/cpu/cpu*/cpuidle/state[2-9]/disable; do
            echo 1 > "$state" 2>/dev/null || true
        done
        echo "[+] Disabled deep CPU idle states"
    fi
    
    echo "[+] CPU performance mode set"
}

# Create systemd service for persistence
create_systemd_service() {
    echo "[*] Creating systemd service for persistence..."
    
    cat > /etc/systemd/system/nvme-universal-optimizations.service << EOF
[Unit]
Description=Universal NVMe SSD Optimizations
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/optimize_nvme_universal.sh --apply
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    
    # Copy this script to system location
    cp "$0" /usr/local/bin/optimize_nvme_universal.sh
    chmod +x /usr/local/bin/optimize_nvme_universal.sh
    
    # Enable service
    systemctl daemon-reload
    systemctl enable nvme-universal-optimizations.service
    
    echo "[+] Systemd service created and enabled"
}

# Show current NVMe settings
show_current_settings() {
    echo
    echo "Current NVMe Settings:"
    echo "──────────────────────────────────────────────────────────"
    
    for device in "${!NVME_DRIVES[@]}"; do
        echo "Device: $device (${NVME_DRIVES[$device]})"
        echo "  Queue Depth: $(cat /sys/block/$device/queue/nr_requests 2>/dev/null || echo 'N/A')"
        echo "  Read Ahead: $(cat /sys/block/$device/queue/read_ahead_kb 2>/dev/null || echo 'N/A') KB"
        echo "  Scheduler: $(cat /sys/block/$device/queue/scheduler 2>/dev/null | grep -o '\[.*\]' | tr -d '[]' || echo 'N/A')"
        echo "  IO Stats: $(cat /sys/block/$device/queue/iostats 2>/dev/null || echo 'N/A')"
        echo
    done
}

# Main function
main() {
    local apply_only=0
    local show_only=0
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --apply)
                apply_only=1
                shift
                ;;
            --show)
                show_only=1
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--apply|--show]"
                exit 1
                ;;
        esac
    done
    
    # Detect drives
    if ! detect_nvme_drives; then
        exit 0
    fi
    
    if [[ $show_only -eq 1 ]]; then
        show_current_settings
        exit 0
    fi
    
    # Apply optimizations
    apply_nvme_core_optimizations
    apply_device_optimizations
    apply_zfs_nvme_optimizations
    set_cpu_performance
    
    # Create service unless just applying
    if [[ $apply_only -eq 0 ]]; then
        create_systemd_service
    fi
    
    # Show results
    show_current_settings
    
    echo "[✓] NVMe optimizations complete!"
    echo "[i] Reboot recommended for all settings to take effect"
}

# Run main
main "$@"
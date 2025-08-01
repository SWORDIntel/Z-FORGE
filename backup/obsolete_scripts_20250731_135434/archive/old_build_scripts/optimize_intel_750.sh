#!/bin/bash
# Z-FORGE Intel 750 Series SSD Optimization Script
# Applies specific optimizations for Intel 750 Series PCIe NVMe SSDs

set -euo pipefail

echo "════════════════════════════════════════════════════════════════"
echo "          Intel 750 Series SSD Optimization Script"
echo "════════════════════════════════════════════════════════════════"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "[!] This script must be run as root"
   exit 1
fi

# Function to detect Intel 750 Series SSDs
detect_intel_750() {
    local found=0
    echo "[*] Detecting Intel 750 Series SSDs..."
    
    for nvme in /sys/block/nvme*; do
        if [[ -f "$nvme/device/model" ]]; then
            model=$(cat "$nvme/device/model" 2>/dev/null || echo "")
            if [[ "$model" =~ "INTEL SSDPE" ]] || [[ "$model" =~ "750" ]]; then
                device=$(basename "$nvme")
                echo "[+] Found Intel 750 Series: $device ($model)"
                found=1
            fi
        fi
    done
    
    return $found
}

# Apply Intel 750 optimizations
apply_intel_750_optimizations() {
    echo "[*] Applying Intel 750 Series optimizations..."
    
    # NVMe core module parameters
    echo "[*] Setting NVMe core parameters..."
    
    # Enable IO polling for lower latency
    echo 1 > /sys/module/nvme_core/parameters/io_poll 2>/dev/null || true
    echo 0 > /sys/module/nvme_core/parameters/io_poll_delay 2>/dev/null || true
    
    # Disable power saving for maximum performance
    echo 0 > /sys/module/nvme_core/parameters/default_ps_max_latency_us 2>/dev/null || true
    
    # Set IO timeout to 30 seconds (Intel 750 recommendation)
    echo 30 > /sys/module/nvme_core/parameters/io_timeout 2>/dev/null || true
    
    # Check kernel version for poll_queues support (4.20+)
    kernel_version=$(uname -r | cut -d. -f1,2)
    if (( $(echo "$kernel_version >= 4.20" | bc -l) )); then
        # Set poll queues to number of CPU cores
        num_cores=$(nproc)
        echo "[*] Setting poll_queues to $num_cores (kernel 4.20+ feature)"
        modprobe -r nvme 2>/dev/null || true
        modprobe nvme poll_queues=$num_cores
    fi
    
    # Disable NVMe APST (Autonomous Power State Transitions)
    for nvme_dev in /sys/class/nvme/nvme*; do
        if [[ -f "$nvme_dev/power/autonomous" ]]; then
            echo 0 > "$nvme_dev/power/autonomous" 2>/dev/null || true
            echo "[+] Disabled APST for $(basename $nvme_dev)"
        fi
    done
    
    # Set CPU governor to performance
    if which cpupower >/dev/null 2>&1; then
        cpupower frequency-set -g performance 2>/dev/null || true
    else
        for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
            echo performance > "$gov" 2>/dev/null || true
        done
    fi
    echo "[+] Set CPU governor to performance"
    
    # Make settings persistent
    cat > /etc/modprobe.d/intel-750-nvme.conf << EOF
# Intel 750 Series NVMe optimizations
options nvme_core io_poll=1
options nvme_core io_poll_delay=0
options nvme_core default_ps_max_latency_us=0
options nvme_core io_timeout=30
# For kernel 4.20+, add: options nvme poll_queues=$(nproc)
EOF
    
    echo "[+] NVMe core parameters configured"
}

# Apply per-device optimizations
apply_device_optimizations() {
    echo "[*] Applying per-device optimizations..."
    
    for nvme in /sys/block/nvme*; do
        if [[ -d "$nvme" ]]; then
            device=$(basename "$nvme")
            
            # Check if this is an Intel 750
            if [[ -f "$nvme/device/model" ]]; then
                model=$(cat "$nvme/device/model" 2>/dev/null || echo "")
                if [[ "$model" =~ "INTEL SSDPE" ]] || [[ "$model" =~ "750" ]]; then
                    echo "[*] Optimizing $device..."
                    
                    # Set queue parameters
                    echo 256 > "$nvme/queue/nr_requests" 2>/dev/null || true
                    echo 256 > "$nvme/queue/queue_depth" 2>/dev/null || true
                    
                    # Set scheduler to none (best for NVMe)
                    echo none > "$nvme/queue/scheduler" 2>/dev/null || true
                    
                    # Set read-ahead to 2MB for balanced performance
                    echo 2048 > "$nvme/queue/read_ahead_kb" 2>/dev/null || true
                    
                    # Disable rotational flag
                    echo 0 > "$nvme/queue/rotational" 2>/dev/null || true
                    
                    # Set optimal IO stats (disabled to reduce overhead)
                    echo 0 > "$nvme/queue/iostats" 2>/dev/null || true
                    
                    # Note: Intel 750 has built-in power loss protection
                    # Write cache settings are handled internally by the drive
                    
                    echo "[+] Optimized $device"
                fi
            fi
        fi
    done
}

# Apply ZFS optimizations for Intel 750
apply_zfs_optimizations() {
    echo "[*] Applying ZFS optimizations for Intel 750..."
    
    # Check if ZFS is loaded
    if ! lsmod | grep -q zfs; then
        echo "[!] ZFS module not loaded, skipping ZFS optimizations"
        return
    fi
    
    # ZFS parameters optimized for Intel 750
    cat > /etc/modprobe.d/zfs-intel-750.conf << EOF
# ZFS optimizations for Intel 750 Series
# Increased concurrent I/O operations for NVMe
options zfs zfs_vdev_async_write_min_active=8
options zfs zfs_vdev_async_write_max_active=32
options zfs zfs_vdev_sync_write_min_active=16
options zfs zfs_vdev_sync_write_max_active=32
options zfs zfs_vdev_queue_depth_pct=300
options zfs zil_slog_bulk=786432
options zfs zfs_prefetch_disable=0
options zfs zfs_txg_timeout=5
EOF
    
    # Apply runtime if ZFS is already loaded
    echo 8 > /sys/module/zfs/parameters/zfs_vdev_async_write_min_active 2>/dev/null || true
    echo 32 > /sys/module/zfs/parameters/zfs_vdev_async_write_max_active 2>/dev/null || true
    echo 16 > /sys/module/zfs/parameters/zfs_vdev_sync_write_min_active 2>/dev/null || true
    echo 32 > /sys/module/zfs/parameters/zfs_vdev_sync_write_max_active 2>/dev/null || true
    echo 300 > /sys/module/zfs/parameters/zfs_vdev_queue_depth_pct 2>/dev/null || true
    echo 786432 > /sys/module/zfs/parameters/zil_slog_bulk 2>/dev/null || true
    echo 0 > /sys/module/zfs/parameters/zfs_prefetch_disable 2>/dev/null || true
    echo 5 > /sys/module/zfs/parameters/zfs_txg_timeout 2>/dev/null || true
    
    echo "[+] ZFS optimizations applied"
}

# Create systemd service for persistence
create_systemd_service() {
    echo "[*] Creating systemd service for persistence..."
    
    cat > /etc/systemd/system/intel-750-optimizations.service << EOF
[Unit]
Description=Intel 750 Series SSD Optimizations
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/optimize_intel_750.sh --apply
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    
    # Copy this script to system location
    cp "$0" /usr/local/bin/optimize_intel_750.sh
    chmod +x /usr/local/bin/optimize_intel_750.sh
    
    # Enable service
    systemctl daemon-reload
    systemctl enable intel-750-optimizations.service
    
    echo "[+] Systemd service created and enabled"
}

# Main function
main() {
    local apply_only=0
    
    # Parse arguments
    if [[ $# -gt 0 ]] && [[ "$1" == "--apply" ]]; then
        apply_only=1
    fi
    
    # Detect Intel 750
    if ! detect_intel_750; then
        echo "[!] No Intel 750 Series SSDs detected"
        exit 0
    fi
    
    # Apply optimizations
    apply_intel_750_optimizations
    apply_device_optimizations
    apply_zfs_optimizations
    
    # Create service unless just applying
    if [[ $apply_only -eq 0 ]]; then
        create_systemd_service
    fi
    
    echo
    echo "[✓] Intel 750 Series optimizations complete!"
    echo "[i] Reboot recommended for all settings to take effect"
}

# Run main
main "$@"
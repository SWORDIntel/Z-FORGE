#!/bin/bash
# Dell PowerEdge T30 Hardware Optimization Script
# Applies T30-specific performance tuning and hardware optimizations

set -euo pipefail

echo "Dell PowerEdge T30 Hardware Optimization Script"
echo "=============================================="

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Detect system information
detect_system() {
    log "Detecting T30 hardware configuration..."
    
    # CPU Information
    CPU_MODEL=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
    CPU_CORES=$(nproc)
    
    # Memory Information
    TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
    
    # Storage Detection
    NVME_DEVICES=$(ls /dev/nvme* 2>/dev/null | grep -E "nvme[0-9]+n[0-9]+$" || true)
    SATA_DEVICES=$(ls /dev/sd* 2>/dev/null | grep -E "sd[a-z]$" || true)
    
    log "CPU: $CPU_MODEL ($CPU_CORES cores)"
    log "Memory: ${TOTAL_MEM}GB"
    log "NVMe devices: ${NVME_DEVICES:-None detected}"
    log "SATA devices: ${SATA_DEVICES:-None detected}"
}

# Intel Xeon E3 v5 specific optimizations
optimize_cpu() {
    log "Applying CPU optimizations for Intel Xeon E3 v5..."
    
    # Enable all CPU features
    if [ -d /sys/devices/system/cpu ]; then
        # Enable turbo boost
        if [ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
            echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo
            log "Turbo Boost enabled"
        fi
        
        # Set performance governor
        for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
            if [ -f "$cpu" ]; then
                echo "performance" > "$cpu"
            fi
        done
        log "CPU governor set to performance"
        
        # Configure Intel P-states
        if [ -d /sys/devices/system/cpu/intel_pstate ]; then
            echo 100 > /sys/devices/system/cpu/intel_pstate/max_perf_pct
            echo 100 > /sys/devices/system/cpu/intel_pstate/min_perf_pct
            log "Intel P-states configured for maximum performance"
        fi
        
        # Disable CPU frequency scaling
        if command -v cpupower >/dev/null 2>&1; then
            cpupower frequency-set -g performance >/dev/null 2>&1 || true
        fi
    fi
    
    # Set CPU affinity for interrupts
    if [ -f /proc/irq/default_smp_affinity ]; then
        # Use all CPUs for interrupt handling
        echo "ff" > /proc/irq/default_smp_affinity
        log "CPU interrupt affinity optimized"
    fi
}

# Memory optimizations for DDR4 ECC
optimize_memory() {
    log "Applying memory optimizations..."
    
    # Calculate optimal ZFS ARC size (50% of RAM for T30)
    ARC_MAX=$(( TOTAL_MEM * 1024 * 1024 * 1024 / 2 ))
    
    # Configure ZFS ARC
    if command -v zfs >/dev/null 2>&1; then
        echo "$ARC_MAX" > /sys/module/zfs/parameters/zfs_arc_max
        log "ZFS ARC max set to $(( ARC_MAX / 1024 / 1024 / 1024 ))GB"
        
        # Additional ZFS tuning for T30
        echo 67108864 > /sys/module/zfs/parameters/zfs_dirty_data_max  # 64MB
        echo 1 > /sys/module/zfs/parameters/zfs_prefetch_disable
        log "ZFS memory parameters optimized"
    fi
    
    # Configure vm parameters
    echo 10 > /proc/sys/vm/swappiness
    echo 10 > /proc/sys/vm/dirty_ratio
    echo 5 > /proc/sys/vm/dirty_background_ratio
    echo 0 > /proc/sys/vm/zone_reclaim_mode
    log "VM memory parameters configured"
    
    # Enable memory compaction
    echo 1 > /proc/sys/vm/compact_memory 2>/dev/null || true
}

# Storage optimizations
optimize_storage() {
    log "Applying storage optimizations..."
    
    # NVMe optimizations
    if [ -n "$NVME_DEVICES" ]; then
        for nvme in $NVME_DEVICES; do
            DEVICE_NAME=$(basename "$nvme")
            log "Optimizing NVMe device: $DEVICE_NAME"
            
            # Set I/O scheduler
            echo "none" > /sys/block/$DEVICE_NAME/queue/scheduler 2>/dev/null || true
            
            # Set queue depth
            echo 1024 > /sys/block/$DEVICE_NAME/queue/nr_requests 2>/dev/null || true
            
            # Set read-ahead
            echo 256 > /sys/block/$DEVICE_NAME/queue/read_ahead_kb 2>/dev/null || true
            
            # Disable add_random (reduce CPU overhead)
            echo 0 > /sys/block/$DEVICE_NAME/queue/add_random 2>/dev/null || true
            
            # Set optimal I/O size
            echo 0 > /sys/block/$DEVICE_NAME/queue/io_poll 2>/dev/null || true
            echo 2 > /sys/block/$DEVICE_NAME/queue/nomerges 2>/dev/null || true
            
            # Configure NVMe specific parameters
            if [ -d "/sys/block/$DEVICE_NAME/device" ]; then
                # Set timeout to maximum
                echo 4294967295 > /sys/block/$DEVICE_NAME/device/timeout 2>/dev/null || true
            fi
        done
    fi
    
    # SATA optimizations
    if [ -n "$SATA_DEVICES" ]; then
        for sata in $SATA_DEVICES; do
            DEVICE_NAME=$(basename "$sata")
            log "Optimizing SATA device: $DEVICE_NAME"
            
            # Set I/O scheduler (mq-deadline for SATA)
            echo "mq-deadline" > /sys/block/$DEVICE_NAME/queue/scheduler 2>/dev/null || true
            
            # Set queue parameters
            echo 256 > /sys/block/$DEVICE_NAME/queue/nr_requests 2>/dev/null || true
            echo 256 > /sys/block/$DEVICE_NAME/queue/read_ahead_kb 2>/dev/null || true
            
            # Enable NCQ if supported
            if [ -f "/sys/block/$DEVICE_NAME/device/queue_depth" ]; then
                echo 31 > /sys/block/$DEVICE_NAME/device/queue_depth 2>/dev/null || true
            fi
        done
    fi
    
    # Configure AHCI link power management
    for host in /sys/class/scsi_host/host*/link_power_management_policy; do
        if [ -f "$host" ]; then
            echo "max_performance" > "$host" 2>/dev/null || true
        fi
    done
    log "AHCI link power management set to max performance"
}

# Network optimizations for T30
optimize_network() {
    log "Applying network optimizations..."
    
    # Detect network interfaces
    for interface in /sys/class/net/*; do
        if [ -d "$interface/device" ]; then
            IFACE=$(basename "$interface")
            log "Optimizing network interface: $IFACE"
            
            # Set interface queue length
            ip link set dev "$IFACE" txqueuelen 10000 2>/dev/null || true
            
            # Enable offloading features
            ethtool -K "$IFACE" gso on gro on tso on 2>/dev/null || true
            
            # Set ring buffer sizes
            ethtool -G "$IFACE" rx 4096 tx 4096 2>/dev/null || true
            
            # Disable interrupt coalescing for low latency
            ethtool -C "$IFACE" rx-usecs 0 tx-usecs 0 2>/dev/null || true
        fi
    done
    
    # Configure network stack
    # Enable BBR congestion control
    modprobe tcp_bbr 2>/dev/null || true
    echo "bbr" > /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || true
    
    # Set network buffer sizes
    echo 134217728 > /proc/sys/net/core/rmem_max
    echo 134217728 > /proc/sys/net/core/wmem_max
    echo "4096 87380 134217728" > /proc/sys/net/ipv4/tcp_rmem
    echo "4096 65536 134217728" > /proc/sys/net/ipv4/tcp_wmem
    echo 5000 > /proc/sys/net/core/netdev_max_backlog
    
    log "Network stack optimized"
}

# PCIe optimizations
optimize_pcie() {
    log "Applying PCIe optimizations..."
    
    # Disable PCIe ASPM for maximum performance
    if [ -f /sys/module/pcie_aspm/parameters/policy ]; then
        echo "performance" > /sys/module/pcie_aspm/parameters/policy
        log "PCIe ASPM set to performance mode"
    fi
    
    # Set PCIe Max Payload Size
    setpci -v -s "*:*.*" CAP_EXP+8.w=5000 2>/dev/null || true
    
    # Enable ARI (Alternative Routing-ID) if supported
    for device in /sys/bus/pci/devices/*/ari_enabled; do
        if [ -f "$device" ]; then
            echo 1 > "$device" 2>/dev/null || true
        fi
    done
}

# Power management settings
configure_power() {
    log "Configuring power management..."
    
    # T30 is a tower server, balance performance with some power saving
    # Disable CPU sleep states beyond C2
    if [ -f /sys/module/intel_idle/parameters/max_cstate ]; then
        echo 2 > /sys/module/intel_idle/parameters/max_cstate
        log "CPU C-states limited to C2"
    fi
    
    # Configure runtime PM
    for device in /sys/bus/pci/devices/*/power/control; do
        echo "on" > "$device" 2>/dev/null || true
    done
    
    # Keep USB devices active
    for usb in /sys/bus/usb/devices/*/power/control; do
        echo "on" > "$usb" 2>/dev/null || true
    done
    
    log "Power management configured for performance"
}

# Apply security mitigations with performance considerations
configure_security() {
    log "Configuring security mitigations..."
    
    # For T30 workloads, keep most mitigations but optimize where possible
    if grep -q "mitigations" /proc/cmdline; then
        log "Security mitigations are enabled"
    else
        log "Warning: Security mitigations may be disabled"
    fi
    
    # Enable IOMMU for better virtualization security
    if ! dmesg | grep -q "IOMMU enabled"; then
        log "Warning: IOMMU not enabled. Add intel_iommu=on to kernel parameters"
    fi
}

# Install performance monitoring tools
install_monitoring() {
    log "Setting up performance monitoring..."
    
    # Create performance monitoring script
    cat > /usr/local/bin/t30-perf-monitor << 'EOF'
#!/bin/bash
# T30 Performance Monitor

while true; do
    clear
    echo "=== Dell T30 Performance Monitor ==="
    echo "Time: $(date)"
    echo
    echo "CPU Performance:"
    grep MHz /proc/cpuinfo | tail -4
    echo
    echo "Temperature:"
    sensors 2>/dev/null | grep -E "Core|Package" || echo "sensors not available"
    echo
    echo "Memory Usage:"
    free -m | grep -E "Mem:|Swap:"
    echo
    echo "Storage I/O:"
    iostat -x 1 2 | tail -n +4 | head -20
    
    sleep 5
done
EOF
    
    chmod +x /usr/local/bin/t30-perf-monitor
    log "Performance monitoring script installed at /usr/local/bin/t30-perf-monitor"
}

# Create optimization report
create_report() {
    REPORT_FILE="/var/log/t30-optimization-report.txt"
    
    {
        echo "Dell PowerEdge T30 Optimization Report"
        echo "Generated: $(date)"
        echo "======================================"
        echo
        echo "System Information:"
        echo "CPU: $CPU_MODEL"
        echo "Cores: $CPU_CORES"
        echo "Memory: ${TOTAL_MEM}GB"
        echo
        echo "Applied Optimizations:"
        echo "- CPU governor: performance"
        echo "- Turbo Boost: enabled"
        echo "- Memory swappiness: 10"
        echo "- ZFS ARC max: $(( TOTAL_MEM / 2 ))GB"
        echo "- I/O schedulers: none (NVMe), mq-deadline (SATA)"
        echo "- Network: BBR congestion control"
        echo "- PCIe ASPM: performance mode"
        echo
        echo "Storage Devices:"
        lsblk -d -o NAME,SIZE,TYPE,MODEL
        echo
        echo "Network Interfaces:"
        ip -br link show
        echo
        echo "Optimization completed successfully!"
    } > "$REPORT_FILE"
    
    log "Optimization report saved to $REPORT_FILE"
}

# Main execution
main() {
    log "Starting Dell PowerEdge T30 hardware optimization..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo "Error: This script must be run as root"
        exit 1
    fi
    
    # Run optimizations
    detect_system
    optimize_cpu
    optimize_memory
    optimize_storage
    optimize_network
    optimize_pcie
    configure_power
    configure_security
    install_monitoring
    create_report
    
    log "Dell PowerEdge T30 optimization completed!"
    log "Reboot recommended to ensure all settings take effect."
}

# Run main function
main "$@"

exit 0
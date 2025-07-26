#!/bin/bash
# Hardware detection script for Z-FORGE ISO boot
# Runs during ISO boot to detect and configure hardware

echo "=== Z-FORGE Hardware Detection ==="
echo "Detecting system hardware..."

# Function to log to both console and file
log() {
    echo "$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> /var/log/zforge-hardware.log
}

# Detect system manufacturer
detect_system() {
    if [ -f /sys/class/dmi/id/sys_vendor ]; then
        VENDOR=$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null)
        MODEL=$(cat /sys/class/dmi/id/product_name 2>/dev/null)
        log "System: $VENDOR $MODEL"
        
        # Check for Dell PowerEdge T30
        if [[ "$VENDOR" == "Dell"* ]] && [[ "$MODEL" == *"T30"* ]]; then
            log "Detected: Dell PowerEdge T30"
            export ZFORGE_SYSTEM="DELL_T30"
            
            # Load T30-specific modules
            modprobe i7core_edac 2>/dev/null || modprobe ie31200_edac 2>/dev/null
            modprobe dell-smbios 2>/dev/null
            modprobe dcdbas 2>/dev/null
        fi
    fi
}

# Detect CPU
detect_cpu() {
    CPU_MODEL=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
    CPU_CORES=$(nproc)
    log "CPU: $CPU_MODEL ($CPU_CORES cores)"
    
    # Intel optimizations
    if [[ "$CPU_MODEL" == *"Intel"* ]]; then
        log "Applying Intel CPU optimizations"
        modprobe intel_pstate 2>/dev/null
        
        # Enable turbo if available
        if [ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
            echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo
        fi
    fi
}

# Detect memory
detect_memory() {
    MEM_TOTAL=$(free -g | awk '/^Mem:/{print $2}')
    log "Memory: ${MEM_TOTAL}GB RAM detected"
    
    # Adjust kernel parameters based on memory
    if [ "$MEM_TOTAL" -ge 32 ]; then
        log "High memory system - optimizing for performance"
        sysctl -w vm.swappiness=10
        sysctl -w vm.vfs_cache_pressure=50
    elif [ "$MEM_TOTAL" -le 8 ]; then
        log "Low memory system - optimizing for efficiency"
        sysctl -w vm.swappiness=60
        sysctl -w vm.vfs_cache_pressure=100
    fi
}

# Detect storage
detect_storage() {
    log "Storage devices:"
    
    # NVMe detection
    if ls /dev/nvme* >/dev/null 2>&1; then
        log "NVMe devices detected"
        modprobe nvme 2>/dev/null
        modprobe nvme_core 2>/dev/null
        
        # Optimize NVMe
        for nvme in /dev/nvme*n1; do
            if [ -b "$nvme" ]; then
                echo none > /sys/block/$(basename $nvme)/queue/scheduler 2>/dev/null
                echo 1024 > /sys/block/$(basename $nvme)/queue/nr_requests 2>/dev/null
            fi
        done
    fi
    
    # SATA detection
    if ls /dev/sd* >/dev/null 2>&1; then
        log "SATA devices detected"
        
        # Optimize SATA
        for disk in /dev/sd?; do
            if [ -b "$disk" ]; then
                echo mq-deadline > /sys/block/$(basename $disk)/queue/scheduler 2>/dev/null
            fi
        done
    fi
}

# Detect network
detect_network() {
    log "Network interfaces:"
    
    # Load common network drivers
    for driver in e1000e igb ixgbe r8169 rtl8139; do
        modprobe $driver 2>/dev/null || true
    done
    
    # List detected interfaces
    ip link show | grep -E "^[0-9]+: " | grep -v "lo:" | while read line; do
        iface=$(echo $line | cut -d: -f2 | xargs)
        log "  Network interface: $iface"
    done
}

# Apply hardware-specific configurations
apply_hardware_config() {
    case "$ZFORGE_SYSTEM" in
        DELL_T30)
            log "Applying Dell T30 specific configuration"
            # T30 specific settings
            echo "options i915 enable_guc=2" > /etc/modprobe.d/i915.conf
            echo "options xhci_hcd quirks=0x40" > /etc/modprobe.d/xhci.conf
            ;;
        *)
            log "Applying generic hardware configuration"
            ;;
    esac
}

# Main execution
main() {
    # Create log directory
    mkdir -p /var/log
    
    log "Starting hardware detection..."
    
    detect_system
    detect_cpu
    detect_memory
    detect_storage
    detect_network
    apply_hardware_config
    
    log "Hardware detection completed"
    
    # Save hardware profile
    cat > /etc/zforge-hardware-profile << EOF
# Z-FORGE Hardware Profile
DETECTED_DATE="$(date)"
SYSTEM="$ZFORGE_SYSTEM"
CPU_MODEL="$CPU_MODEL"
CPU_CORES="$CPU_CORES"
MEMORY_GB="$MEM_TOTAL"
EOF
    
    # Make profile available to installer
    cp /etc/zforge-hardware-profile /tmp/
}

# Run detection
main "$@"
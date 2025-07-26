#!/bin/bash
# Dell PowerEdge T30 Post-Installation Script
# Configures T30-specific settings after Proxmox installation

set -euo pipefail

echo "Starting Dell PowerEdge T30 post-installation configuration..."

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Enable Intel microcode updates
log "Enabling Intel microcode updates..."
if [ -f /sys/devices/system/cpu/microcode/reload ]; then
    echo 1 > /sys/devices/system/cpu/microcode/reload
fi

# Configure CPU governor for performance
log "Setting CPU governor to performance..."
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [ -f "$cpu" ] && echo "performance" > "$cpu"
done

# Enable Intel Turbo Boost
log "Enabling Intel Turbo Boost..."
if [ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
    echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo
fi

# Configure C-states for balanced performance
log "Configuring CPU C-states..."
if [ -f /sys/module/intel_idle/parameters/max_cstate ]; then
    echo 2 > /sys/module/intel_idle/parameters/max_cstate
fi

# Enable IOMMU for virtualization
log "Configuring IOMMU settings..."
if ! grep -q "intel_iommu=on" /etc/default/grub; then
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="\(.*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 intel_iommu=on"/' /etc/default/grub
    update-grub
fi

# Configure memory settings
log "Configuring memory settings..."
# Disable transparent huge pages for better ZFS performance
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag

# Make it persistent
cat > /etc/systemd/system/disable-thp.service << 'EOF'
[Unit]
Description=Disable Transparent Huge Pages
DefaultDependencies=no
After=sysinit.target
Before=basic.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled && echo never > /sys/kernel/mm/transparent_hugepage/defrag'

[Install]
WantedBy=basic.target
EOF

systemctl daemon-reload
systemctl enable disable-thp.service

# Configure SATA link power management
log "Configuring SATA power management..."
for host in /sys/class/scsi_host/host*/link_power_management_policy; do
    [ -f "$host" ] && echo "max_performance" > "$host"
done

# Configure PCIe ASPM
log "Configuring PCIe ASPM..."
if [ -f /sys/module/pcie_aspm/parameters/policy ]; then
    echo "performance" > /sys/module/pcie_aspm/parameters/policy
fi

# Install and configure thermald for Intel thermal management
log "Configuring thermal management..."
if command -v thermald >/dev/null 2>&1; then
    systemctl enable thermald
    systemctl start thermald
fi

# Configure software RAID monitoring if mdadm is installed
if command -v mdadm >/dev/null 2>&1; then
    log "Configuring software RAID monitoring..."
    # Enable RAID monitoring
    sed -i 's/^AUTOCHECK=.*/AUTOCHECK=true/' /etc/default/mdadm 2>/dev/null || true
    systemctl enable mdadm-monitoring.service
fi

# Configure network interfaces for optimal performance
log "Optimizing network interfaces..."
for interface in /sys/class/net/*/device/driver/module/parameters/*; do
    case "$interface" in
        */InterruptThrottleRate)
            echo 0 > "$interface" 2>/dev/null || true
            ;;
        */IntMode)
            echo 2 > "$interface" 2>/dev/null || true
            ;;
    esac
done

# Configure USB settings for T30
log "Configuring USB settings..."
# Enable USB autosuspend for power efficiency (tower server)
for usb in /sys/bus/usb/devices/*/power/autosuspend; do
    [ -f "$usb" ] && echo 2 > "$usb"
done

# Create T30-specific tuning profile
log "Creating T30 tuning profile..."
cat > /etc/sysctl.d/99-dell-t30.conf << 'EOF'
# Dell PowerEdge T30 Optimizations

# Network optimizations
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# VM optimizations for Proxmox
vm.swappiness = 10
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5

# File system optimizations
fs.file-max = 2097152
fs.aio-max-nr = 1048576

# Intel CPU optimizations
kernel.sched_migration_cost_ns = 5000000
kernel.sched_autogroup_enabled = 0
EOF

sysctl -p /etc/sysctl.d/99-dell-t30.conf

# Configure ECC memory reporting if available
log "Configuring ECC memory reporting..."
if lsmod | grep -q edac; then
    # Load EDAC modules for Intel E3 v5
    modprobe i7core_edac 2>/dev/null || modprobe ie31200_edac 2>/dev/null || true
fi

# Create systemd service for T30 optimizations
log "Creating T30 optimization service..."
cat > /etc/systemd/system/dell-t30-optimize.service << 'EOF'
[Unit]
Description=Dell PowerEdge T30 Optimizations
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/t30-optimize.sh

[Install]
WantedBy=multi-user.target
EOF

# Create the optimization script
cat > /usr/local/sbin/t30-optimize.sh << 'EOF'
#!/bin/bash
# Runtime optimizations for Dell T30

# Set CPU performance
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [ -f "$cpu" ] && echo "performance" > "$cpu"
done

# Set SATA link power
for host in /sys/class/scsi_host/host*/link_power_management_policy; do
    [ -f "$host" ] && echo "max_performance" > "$host"
done

# Optimize interrupts for single socket system
# Spread interrupts across all cores
if command -v irqbalance >/dev/null 2>&1; then
    systemctl restart irqbalance
fi
EOF

chmod +x /usr/local/sbin/t30-optimize.sh
systemctl daemon-reload
systemctl enable dell-t30-optimize.service

# Configure basic BMC if available
log "Checking for BMC/IPMI..."
if command -v ipmitool >/dev/null 2>&1; then
    # T30 has basic BMC functionality
    # Enable IPMI over LAN if supported
    ipmitool lan set 1 ipsrc static 2>/dev/null || true
    
    # Set fan mode to optimal
    ipmitool raw 0x30 0x30 0x01 0x00 2>/dev/null || true
fi

# Install T30 monitoring scripts
log "Installing monitoring scripts..."
cat > /usr/local/bin/t30-monitor << 'EOF'
#!/bin/bash
# Dell T30 System Monitor

echo "=== Dell PowerEdge T30 System Status ==="
echo
echo "CPU Information:"
lscpu | grep -E "Model name|CPU MHz|CPU max MHz"
echo
echo "Temperature:"
sensors 2>/dev/null | grep -E "Core|Package"
echo
echo "Memory:"
free -h
echo
if command -v ipmitool >/dev/null 2>&1; then
    echo "BMC Status:"
    ipmitool sdr list 2>/dev/null | grep -E "Temp|Fan" || echo "BMC not available"
fi
echo
echo "Storage:"
df -h | grep -E "^/dev|Filesystem"
if command -v zpool >/dev/null 2>&1; then
    echo
    echo "ZFS Pools:"
    zpool list
fi
EOF

chmod +x /usr/local/bin/t30-monitor

log "Dell PowerEdge T30 post-installation configuration completed!"
log "Note: A reboot is recommended to apply all settings."

# Create completion marker
touch /var/lib/dell-t30-configured

exit 0
#!/bin/bash
# PowerEdge R730xd Post-Installation Script

# Set terminal colors
BOLD=$(tput bold)
NORMAL=$(tput sgr0)
GREEN=$(tput setaf 2)
BLUE=$(tput setaf 4)
RED=$(tput setaf 1)

echo "${BOLD}${BLUE}Dell PowerEdge R730xd Post-Installation Script${NORMAL}"
echo "=================================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "${RED}This script must be run as root!${NORMAL}"
    exit 1
fi

# Function to log actions
log() {
    echo "${BLUE}$1${NORMAL}"
    logger -t r730xd-setup "$1"
}

# Install Dell-specific packages
log "Installing Dell PowerEdge R730xd management packages..."

apt-get update
apt-get install -y ipmitool openipmi lm-sensors \
                   nvme-cli smartmontools ethtool \
                   srvadmin-all srvadmin-storage srvadmin-idrac \
                   megacli megactl megaraid-status

# Configure IDRAC and IPMI
log "Configuring iDRAC/IPMI settings..."

# Enable Serial Over LAN
ipmitool sol set enabled true
ipmitool sol set privilege-level admin
ipmitool sol set force-encryption false
ipmitool sol set baud-rate 115200

# Configure IDRAC network settings (example)
# Uncomment and modify as needed
# ipmitool lan set 1 ipsrc static
# ipmitool lan set 1 ipaddr 192.168.1.120
# ipmitool lan set 1 netmask 255.255.255.0
# ipmitool lan set 1 defgw ipaddr 192.168.1.1

# Optimize CPU settings
log "Configuring CPU performance settings..."

# Set CPU governor to performance
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    if [ -f "$cpu" ]; then
        echo performance > "$cpu"
    fi
done

# Make CPU governor persistent
cat > /etc/systemd/system/cpu-performance.service << 'EOF_CPU'
[Unit]
Description=Set CPU Governor to Performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c "echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF_CPU

systemctl enable cpu-performance.service

# Configure serial console for GRUB
log "Configuring serial console..."

if [ -f /etc/default/grub ]; then
    # Backup original GRUB config
    cp /etc/default/grub /etc/default/grub.bak
    
    # Update GRUB config for serial console
    sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200n8 mitigations=auto,nosmt"/' /etc/default/grub
    sed -i 's/#GRUB_TERMINAL=console/GRUB_TERMINAL="console serial"/' /etc/default/grub
    
    # Add serial command if not already present
    if ! grep -q "GRUB_SERIAL_COMMAND" /etc/default/grub; then
        echo 'GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"' >> /etc/default/grub
    fi
    
    # Update GRUB
    if command -v update-grub &> /dev/null; then
        update-grub
    elif command -v grub-mkconfig &> /dev/null; then
        grub-mkconfig -o /boot/grub/grub.cfg
    fi
fi

# Configure for PERC RAID controller if present
if lspci | grep -i "PERC"; then
    log "PERC RAID controller detected, configuring monitoring..."
    
    # Add monitoring script
    cat > /usr/local/bin/check_raid.sh << 'RAID_SCRIPT'
#!/bin/bash
# Check RAID status
if command -v megacli &> /dev/null; then
    RAID_STATUS=$(megacli -LDInfo -Lall -aALL | grep "State" | awk '{print $3}')
    if [[ "$RAID_STATUS" != "Optimal" ]]; then
        echo "WARNING: RAID status is not optimal: $RAID_STATUS"
        logger -t raid-check "WARNING: RAID status is not optimal: $RAID_STATUS"
        mail -s "RAID Warning on $(hostname)" root <<< "RAID status: $RAID_STATUS"
        exit 1
    fi
    
    # Check for rebuilding arrays
    REBUILD=$(megacli -PDList -aALL | grep "Firmware state" | grep "Rebuild")
    if [ ! -z "$REBUILD" ]; then
        logger -t raid-check "RAID array is rebuilding; monitoring progress"
        PROGRESS=$(megacli -PDRbld -ShowProg -aALL | grep "Rebuilding")
        mail -s "RAID Rebuilding on $(hostname)" root <<< "$PROGRESS"
    fi
else
    echo "megacli not found"
    exit 1
fi
exit 0
RAID_SCRIPT
    chmod +x /usr/local/bin/check_raid.sh
    
    # Add to crontab
    echo "0 * * * * root /usr/local/bin/check_raid.sh" > /etc/cron.d/raid_check
fi

# Optimize for NVMe if present
if lspci | grep -i "Non-Volatile memory controller" || [ -e /dev/nvme0 ]; then
    log "Optimizing for NVMe storage..."
    
    # Create NVMe module configuration
    cat > /etc/modprobe.d/nvme.conf << 'NVME_CONF'
# NVMe parameters for Dell PowerEdge R730xd
options nvme_core io_timeout=4294967295
options nvme_core max_host_mem_size_mb=512
NVME_CONF
    
    # Create udev rules for performance
    cat > /etc/udev/rules.d/60-nvme-r730xd.rules << 'UDEV_RULES'
# Optimize settings for NVMe on PowerEdge R730xd
ACTION=="add|change", KERNEL=="nvme[0-9]n[0-9]", ATTR{queue/scheduler}="none"
ACTION=="add|change", KERNEL=="nvme[0-9]n[0-9]", ATTR{queue/read_ahead_kb}="4096"
ACTION=="add|change", KERNEL=="nvme[0-9]n[0-9]", ATTR{queue/nr_requests}="2048"
ACTION=="add|change", KERNEL=="nvme[0-9]n[0-9]", ATTR{queue/rq_affinity}="2"
UDEV_RULES
    
    # Set up NVMe monitoring
    cat > /usr/local/bin/check_nvme.sh << 'NVME_SCRIPT'
#!/bin/bash
# Check NVMe health
for nvme_dev in $(nvme list | grep "^/dev/nvme" | awk '{print $1}'); do
    # Get health info
    SMART=$(nvme smart-log $nvme_dev)
    CRITICAL=$(echo "$SMART" | grep critical_warning | awk '{print $3}')
    TEMP=$(echo "$SMART" | grep temperature | awk '{print $3}')
    USED=$(echo "$SMART" | grep percentage_used | awk '{print $3}')
    
    # Log status
    logger -t nvme-check "$nvme_dev: Temp=${TEMP}C, Used=${USED}%, Warning=${CRITICAL}"
    
    # Check for problems
    if [ "$CRITICAL" != "0" ]; then
        mail -s "NVMe Warning on $(hostname)" root <<< "Critical warning detected on $nvme_dev"
        exit 1
    fi
    
    if [ "$TEMP" -gt 75 ]; then
        mail -s "NVMe Temperature Warning on $(hostname)" root <<< "High temperature (${TEMP}C) on $nvme_dev"
    fi
    
    if [ "$USED" -gt 85 ]; then
        mail -s "NVMe Usage Warning on $(hostname)" root <<< "High usage (${USED}%) on $nvme_dev"
    fi
done
NVME_SCRIPT
    chmod +x /usr/local/bin/check_nvme.sh
    
    # Add to crontab
    echo "0 */2 * * * root /usr/local/bin/check_nvme.sh" > /etc/cron.d/nvme_check
fi

# Configure hardware monitoring with lm-sensors
log "Setting up hardware monitoring..."

# Auto-detect sensors
yes | sensors-detect

# Set up fan control if supported
if command -v ipmitool &> /dev/null; then
    # Enable manual fan control
    # This is a conservative approach - you may want more advanced fan control
    cat > /usr/local/bin/fan_control.sh << 'FAN_SCRIPT'
#!/bin/bash
# Simple fan control script for PowerEdge R730xd

# Get current CPU temperature (average of all cores)
get_cpu_temp() {
    sensors | grep -i "Core" | grep "+" | awk '{sum+=$3} END {print sum/NR}' | sed 's/+//g' | sed 's/°C//g'
}

# Set fan speed
set_fan_speed() {
    FAN_SPEED=$1
    ipmitool raw 0x30 0x30 0x02 0xff $FAN_SPEED
}

# Enable manual control
enable_manual_control() {
    ipmitool raw 0x30 0x30 0x01 0x00
}

# Disable manual control (return to automatic)
disable_manual_control() {
    ipmitool raw 0x30 0x30 0x01 0x01
}

# Set sensible fan curve
TEMP=$(get_cpu_temp)
if [ -z "$TEMP" ]; then
    # If we can't get temp, return to automatic control
    disable_manual_control
    exit 0
fi

# Fan curve based on CPU temperature
if (( $(echo "$TEMP < 40" | bc -l) )); then
    # Below 40C - quieter operation
    enable_manual_control
    set_fan_speed 0x10
elif (( $(echo "$TEMP < 65" | bc -l) )); then
    # 40-65C - moderate cooling
    enable_manual_control
    set_fan_speed 0x20
elif (( $(echo "$TEMP < 75" | bc -l) )); then
    # 65-75C - increased cooling
    enable_manual_control
    set_fan_speed 0x30
else
    # Above 75C - maximum cooling (automatic control)
    disable_manual_control
fi
FAN_SCRIPT
    chmod +x /usr/local/bin/fan_control.sh
    
    # Set up cron job for fan control
    echo "*/5 * * * * root /usr/local/bin/fan_control.sh" > /etc/cron.d/fan_control
fi

# Set up system tuning parameters
log "Setting up system tuning parameters..."

# Create sysctl configuration
cat > /etc/sysctl.d/r730xd-tuning.conf << 'SYSCTL_CONF'
# Dell PowerEdge R730xd performance tuning

# VM subsystem tuning
vm.swappiness=10
vm.dirty_ratio=10
vm.dirty_background_ratio=5
vm.min_free_kbytes=1048576

# Network tuning for server workload
net.core.somaxconn=4096
net.core.netdev_max_backlog=4000
net.ipv4.tcp_max_syn_backlog=4096
net.ipv4.tcp_fin_timeout=30
net.ipv4.tcp_keepalive_time=300
net.ipv4.tcp_keepalive_intvl=60
net.ipv4.tcp_keepalive_probes=10

# File system and I/O tuning
fs.file-max=1000000
fs.aio-max-nr=1048576
vm.max_map_count=2147483647
SYSCTL_CONF

# Load new sysctl settings
sysctl -p /etc/sysctl.d/r730xd-tuning.conf

# Create custom I/O scheduler setup
cat > /usr/local/bin/setup_io_schedulers.sh << 'IO_SCRIPT'
#!/bin/bash
# Configure optimal I/O schedulers for different device types

# For NVMe devices - use no scheduler
for device in $(lsblk -d -o NAME | grep nvme); do
    if [ -f "/sys/block/$device/queue/scheduler" ]; then
        echo "none" > "/sys/block/$device/queue/scheduler"
        echo "2048" > "/sys/block/$device/queue/read_ahead_kb"
    fi
done

# For SSDs - use mq-deadline
for device in $(lsblk -d -o NAME,ROTA | grep "0$" | awk '{print $1}' | grep -v nvme); do
    if [ -f "/sys/block/$device/queue/scheduler" ]; then
        echo "mq-deadline" > "/sys/block/$device/queue/scheduler"
        echo "256" > "/sys/block/$device/queue/read_ahead_kb"
    fi
done

# For HDDs - use bfq
for device in $(lsblk -d -o NAME,ROTA | grep "1$" | awk '{print $1}'); do
    if [ -f "/sys/block/$device/queue/scheduler" ]; then
        echo "bfq" > "/sys/block/$device/queue/scheduler"
        echo "512" > "/sys/block/$device/queue/read_ahead_kb"
    fi
done
IO_SCRIPT
chmod +x /usr/local/bin/setup_io_schedulers.sh

# Create systemd service to configure I/O schedulers at boot
cat > /etc/systemd/system/io-scheduler.service << 'IO_SERVICE'
[Unit]
Description=Configure I/O Schedulers
After=sysinit.target local-fs.target
DefaultDependencies=no

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup_io_schedulers.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
IO_SERVICE
systemctl enable io-scheduler.service

# Configure Dell System Management
log "Configuring Dell OpenManage System Administrator..."

# Enable and start OMSA services
if command -v srvadmin-services.sh &> /dev/null; then
    srvadmin-services.sh enable
    srvadmin-services.sh start
    
    # Create service to ensure it starts after reboot
    systemctl enable dsm_om_connsvc
fi

# Configure SNMP for monitoring
log "Setting up SNMP monitoring..."
apt-get install -y snmpd snmp libsnmp-dev

# Create SNMP configuration
cat > /etc/snmp/snmpd.conf << 'SNMP_CONF'
# SNMP configuration for Dell PowerEdge R730xd
rocommunity public localhost
# Change 'public' to a more secure community string in production
rocommunity public 127.0.0.1

# System information
syslocation "Datacenter"
syscontact admin@example.com

# Monitor disks, CPU, memory
# This enables basic monitoring of system resources
view systemonly included .1.3.6.1.2.1.1
view systemonly included .1.3.6.1.2.1.25.1
includeAllDisks 10%
SNMP_CONF

# Enable SNMP service
systemctl enable snmpd
systemctl restart snmpd

# Set up SMART monitoring for drives
log "Setting up SMART monitoring for drives..."

apt-get install -y smartmontools

# Configure SMART monitoring
cat > /etc/smartd.conf << 'SMART_CONF'
# Monitor all drives
DEVICESCAN -a -o on -S on -n standby,q -s (S/../.././02|L/../../6/03) -W 4,35,40 -m root

# Report more detailed information for NVMe drives
/dev/nvme0 -a -o on -S on -n standby -s (S/../.././02|L/../../6/03) -W 4,35,45 -m root
SMART_CONF

# Enable SMART monitoring service
systemctl enable smartd
systemctl restart smartd

# Create ZFS performance tuning script
log "Creating ZFS performance tuning script..."

cat > /usr/local/bin/zfs_tune.sh << 'ZFS_SCRIPT'
#!/bin/bash
# ZFS tuning script for PowerEdge R730xd

# Get total system memory
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))

# Set ZFS ARC size based on total memory
# For R730xd, we can allocate more memory to ARC than R420
if [ "$TOTAL_MEM_GB" -ge 128 ]; then
    # For high-memory systems (128GB+)
    ARC_MAX=$((TOTAL_MEM_GB / 2 * 1024 * 1024 * 1024))
elif [ "$TOTAL_MEM_GB" -ge 64 ]; then
    # For medium-memory systems (64-128GB)
    ARC_MAX=$((TOTAL_MEM_GB * 60 / 100 * 1024 * 1024 * 1024))
else
    # For lower-memory systems
    ARC_MAX=$((TOTAL_MEM_GB / 3 * 1024 * 1024 * 1024))
fi

# Create ZFS module parameters
cat > /etc/modprobe.d/zfs.conf << EOL
# ZFS module parameters for PowerEdge R730xd
options zfs zfs_arc_max=${ARC_MAX}
# Enable prefetch for server with good memory
options zfs zfs_prefetch_disable=0
EOL

# Set optimal ZFS parameters for all pools
for pool in $(zpool list -H -o name); do
    # Set basic pool properties
    zfs set compression=lz4 "$pool"
    zfs set atime=off "$pool"
    
    # Set advanced properties for server workload
    zfs set primarycache=all "$pool"
    zfs set recordsize=128K "$pool"
    
    # Special optimization for datasets likely to contain VMs
    if zfs list -r "$pool" | grep -q "/vms"; then
        zfs set recordsize=64K "$pool/vms"
        zfs set logbias=throughput "$pool/vms"
    fi
    
    # Special optimization for datasets likely to contain containers
    if zfs list -r "$pool" | grep -q "/ct"; then
        zfs set compression=zstd-3 "$pool/ct"
        zfs set recordsize=16K "$pool/ct"
    fi
    
    echo "ZFS tuning applied to $pool"
done
ZFS_SCRIPT
chmod +x /usr/local/bin/zfs_tune.sh

# Configure script to run at boot
if ! grep -q "zfs_tune.sh" /etc/rc.local; then
    # Check if rc.local exists and is executable
    if [ ! -f /etc/rc.local ]; then
        cat > /etc/rc.local << 'RC_LOCAL'
#!/bin/bash
exit 0
RC_LOCAL
        chmod +x /etc/rc.local
    fi
    
    # Add ZFS tuning script before exit
    sed -i '/exit 0/i /usr/local/bin/zfs_tune.sh' /etc/rc.local
fi

# Create diagnostics utility
log "Creating system diagnostics utility..."

cat > /usr/local/bin/r730xd-diag.sh << 'DIAG_SCRIPT'
#!/bin/bash
# PowerEdge R730xd Diagnostics Utility

BOLD=$(tput bold)
NORMAL=$(tput sgr0)
GREEN=$(tput setaf 2)
BLUE=$(tput setaf 4)
RED=$(tput setaf 1)
YELLOW=$(tput setaf 3)

echo "${BOLD}${BLUE}Dell PowerEdge R730xd Diagnostics Utility${NORMAL}"
echo "=========================================="
echo ""

# System information
echo "${BOLD}System Information:${NORMAL}"
echo "${BLUE}Hostname:${NORMAL} $(hostname)"
echo "${BLUE}OS:${NORMAL} $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "${BLUE}Kernel:${NORMAL} $(uname -r)"
echo "${BLUE}Uptime:${NORMAL} $(uptime -p)"
echo ""

# Dell specific hardware info
if command -v omreport &> /dev/null; then
    echo "${BOLD}Dell Hardware Information:${NORMAL}"
    echo "${BLUE}System Model:${NORMAL} $(omreport system summary | grep "Model" | cut -d: -f2 | sed 's/^[ \t]*//')"
    echo "${BLUE}Service Tag:${NORMAL} $(omreport system summary | grep "Service Tag" | cut -d: -f2 | sed 's/^[ \t]*//')"
    echo "${BLUE}BIOS Version:${NORMAL} $(omreport system summary | grep "BIOS Version" | cut -d: -f2 | sed 's/^[ \t]*//')"
    echo ""
fi

# CPU information
echo "${BOLD}CPU Information:${NORMAL}"
echo "${BLUE}Model:${NORMAL} $(lscpu | grep 'Model name' | cut -d: -f2 | sed 's/^[ \t]*//')"
echo "${BLUE}Cores/Threads:${NORMAL} $(nproc) Threads, $(lscpu | grep 'Core(s) per socket' | cut -d: -f2 | sed 's/^[ \t]*//') Cores per Socket × $(lscpu | grep 'Socket(s)' | cut -d: -f2 | sed 's/^[ \t]*//') Sockets"
echo "${BLUE}CPU Governor:${NORMAL} $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "N/A")"
echo ""

# Memory information
echo "${BOLD}Memory Information:${NORMAL}"
free -h
echo ""
if command -v omreport &> /dev/null; then
    echo "${BLUE}Memory Details:${NORMAL}"
    omreport chassis memory | grep -E "Size|Speed|Type" | sed 's/^[ \t]*//'
    echo ""
fi

# Storage information
echo "${BOLD}Storage Devices:${NORMAL}"
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN | grep -v ^loop
echo ""

# ZFS information
if command -v zpool &> /dev/null; then
    echo "${BOLD}ZFS Storage:${NORMAL}"
    echo "${BLUE}ZFS Pools:${NORMAL}"
    zpool list
    echo ""
    echo "${BLUE}ZFS Pool Status:${NORMAL}"
    zpool status
    echo ""
    echo "${BLUE}ZFS Dataset Usage:${NORMAL}"
    zfs list
    echo ""
    if [ -f /sys/module/zfs/parameters/zfs_arc_max ]; then
        echo "${BLUE}ZFS ARC:${NORMAL} $(cat /sys/module/zfs/parameters/zfs_arc_max | numfmt --to=iec-i)"
        echo ""
    fi
fi

# RAID information
if command -v megacli &> /dev/null && lspci | grep -q -i "PERC"; then
    echo "${BOLD}RAID Controller Information:${NORMAL}"
    echo "${BLUE}Controller:${NORMAL} $(megacli -AdpAllInfo -aALL | grep "Product Name" | sed 's/^[ \t]*//')"
    echo "${BLUE}Virtual Drives:${NORMAL}"
    megacli -LDInfo -Lall -aALL | grep -E "Size|State|Name" | sed 's/^[ \t]*//'
    echo ""
    echo "${BLUE}Physical Disks:${NORMAL}"
    megacli -PDList -aALL | grep -E "Slot|Firmware state|Foreign State|Media Type|Inquiry Data" | sed 's/^[ \t]*//'
    echo ""
fi

# NVMe information
if command -v nvme &> /dev/null && lspci | grep -q -i "Non-Volatile memory controller"; then
    echo "${BOLD}NVMe Devices:${NORMAL}"
    nvme list
    echo ""
    for nvme_dev in $(ls /dev/nvme?n1 2>/dev/null); do
        echo "${BLUE}${nvme_dev} SMART Information:${NORMAL}"
        nvme smart-log $nvme_dev | grep -E "critical_warning|temperature|percentage_used|data_units"
        echo ""
    done
fi

# Network information
echo "${BOLD}Network Interfaces:${NORMAL}"
ip -br addr
echo ""
echo "${BLUE}Network Details:${NORMAL}"
for iface in $(ip -br link | grep -v ^lo | awk '{print $1}'); do
    if [ -d "/sys/class/net/$iface" ]; then
        speed=$(ethtool $iface 2>/dev/null | grep "Speed" | sed 's/^[ \t]*//')
        driver=$(ethtool -i $iface 2>/dev/null | grep "^driver" | sed 's/^[ \t]*//')
        echo "$iface: $speed, $driver"
    fi
done
echo ""

# iDRAC information
if command -v ipmitool &> /dev/null; then
    echo "${BOLD}iDRAC Information:${NORMAL}"
    echo "${BLUE}Network Configuration:${NORMAL}"
    ipmitool lan print 1 | grep -E "IP Address|MAC Address|Subnet Mask" | sed 's/^[ \t]*//'
    echo ""
    echo "${BLUE}System Temperatures:${NORMAL}"
    ipmitool sensor list | grep -i temp | grep -v "ERR" | sed 's/^[ \t]*//'
    echo ""
    echo "${BLUE}Fan Speeds:${NORMAL}"
    ipmitool sensor list | grep -i fan | grep -v "ERR" | sed 's/^[ \t]*//'
    echo ""
fi

# Proxmox information
if [ -d /etc/pve ]; then
    echo "${BOLD}Proxmox VE Information:${NORMAL}"
    if [ -f /usr/bin/pveversion ]; then
        echo "${BLUE}Version:${NORMAL} $(pveversion)"
    fi
    
    if [ -d /etc/pve/nodes ]; then
        echo "${BLUE}Cluster Nodes:${NORMAL} $(ls /etc/pve/nodes/)"
    fi
    
    if [ -x /usr/bin/qm ]; then
        echo "${BLUE}Virtual Machines:${NORMAL} $(qm list 2>/dev/null | wc -l)"
    fi
    
    if [ -x /usr/bin/pct ]; then
        echo "${BLUE}Containers:${NORMAL} $(pct list 2>/dev/null | wc -l)"
    fi
    echo ""
fi

# System health check
echo "${BOLD}System Health Check:${NORMAL}"

# Check CPU temperature
if command -v sensors &> /dev/null; then
    cpu_temp=$(sensors | grep -i "Package id 0" | awk '{print $4}' | sed 's/+//g' | sed 's/°C//g')
    if [ ! -z "$cpu_temp" ]; then
        if (( $(echo "$cpu_temp < 70" | bc -l) )); then
            echo "${GREEN}✓ CPU Temperature: ${cpu_temp}°C (Good)${NORMAL}"
        else
            echo "${RED}✗ CPU Temperature: ${cpu_temp}°C (High)${NORMAL}"
        fi
    fi
fi

# Check RAID status
if command -v megacli &> /dev/null; then
    raid_status=$(megacli -LDInfo -Lall -aALL | grep "State" | awk '{print $3}')
    if [ "$raid_status" == "Optimal" ]; then
        echo "${GREEN}✓ RAID Status: Optimal${NORMAL}"
    else
        echo "${RED}✗ RAID Status: $raid_status${NORMAL}"
    fi
fi

# Check ZFS pool health
if command -v zpool &> /dev/null; then
    pool_status=$(zpool status | grep -E "state:" | head -1 | awk '{print $2}')
    if [ "$pool_status" == "ONLINE" ]; then
        echo "${GREEN}✓ ZFS Pool Status: Online${NORMAL}"
    else
        echo "${RED}✗ ZFS Pool Status: $pool_status${NORMAL}"
    fi
fi

# Check disk space
root_usage=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//g')
if [ "$root_usage" -lt 80 ]; then
    echo "${GREEN}✓ Root Disk Usage: ${root_usage}%${NORMAL}"
else
    echo "${RED}✗ Root Disk Usage: ${root_usage}% (High)${NORMAL}"
fi

# Check memory usage
mem_free_percent=$(free | grep Mem | awk '{print $7/$2 * 100.0}' | cut -d. -f1)
if [ "$mem_free_percent" -gt 15 ]; then
    echo "${GREEN}✓ Memory Usage: ${mem_free_percent}% free${NORMAL}"
else
    echo "${RED}✗ Low Memory: Only ${mem_free_percent}% free${NORMAL}"
fi

echo ""
echo "${BOLD}${BLUE}Diagnostics Complete${NORMAL}"
echo "For more detailed diagnostics, check the system logs or run specific hardware tests."
echo "Log files are located in /var/log/ and Dell hardware logs can be accessed via omreport."
DIAG_SCRIPT
chmod +x /usr/local/bin/r730xd-diag.sh

# Create a desktop shortcut for diagnostics
if [ -d /root/Desktop ]; then
    cat > /root/Desktop/r730xd-diagnostics.desktop << 'DESKTOP_SHORTCUT'
[Desktop Entry]
Type=Application
Version=1.0
Name=R730xd Diagnostics
Comment=Run system diagnostics for Dell PowerEdge R730xd
Exec=x-terminal-emulator -e "/usr/local/bin/r730xd-diag.sh; read -p 'Press Enter to close...'" 
Icon=utilities-terminal
Terminal=false
Categories=System;
DESKTOP_SHORTCUT
    chmod +x /root/Desktop/r730xd-diagnostics.desktop
fi

# Final system configuration
log "Performing final configuration tasks..."

# Update all packages one last time
apt-get update
apt-get upgrade -y

# Ensure system stability by setting appropriate swappiness
echo "vm.swappiness=10" > /etc/sysctl.d/99-swappiness.conf
sysctl -p /etc/sysctl.d/99-swappiness.conf

# Display completion message
echo "${GREEN}${BOLD}PowerEdge R730xd post-installation completed!${NORMAL}"
echo ""
echo "The following optimizations have been applied:"
echo "- Dell OpenManage tools installed"
echo "- IPMI/iDRAC configured for remote management"
echo "- CPU performance optimized"
echo "- NVMe storage tuning (if applicable)"
echo "- RAID monitoring configured (if applicable)"
echo "- ZFS performance tuning"
echo "- System parameters optimized for server workloads"
echo "- Hardware monitoring services enabled"
echo ""
echo "A diagnostic tool has been installed at: /usr/local/bin/r730xd-diag.sh"
echo ""
echo "${BOLD}${BLUE}System ready for Proxmox VE operation!${NORMAL}"

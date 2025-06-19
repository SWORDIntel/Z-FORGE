#!/bin/bash
# PowerEdge R420 Diagnostics and Performance Tuning Tool

# Text formatting
BOLD=$(tput bold)
NORMAL=$(tput sgr0)
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
BLUE=$(tput setaf 4)

echo "${BOLD}${BLUE}Dell PowerEdge R420 Diagnostics Tool${NORMAL}"
echo "==========================================="
echo ""

# Basic system information
echo "${BOLD}System Information:${NORMAL}"
echo "${BLUE}Hostname:${NORMAL} $(hostname)"
echo "${BLUE}OS:${NORMAL} $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "${BLUE}Kernel:${NORMAL} $(uname -r)"
echo "${BLUE}Uptime:${NORMAL} $(uptime -p)"
echo ""

# CPU information
echo "${BOLD}CPU Information:${NORMAL}"
echo "${BLUE}Model:${NORMAL} $(lscpu | grep 'Model name' | cut -d':' -f2 | sed 's/^[ \t]*//')"
echo "${BLUE}Architecture:${NORMAL} $(lscpu | grep 'Architecture' | cut -d':' -f2 | sed 's/^[ \t]*//')"
echo "${BLUE}Cores/Threads:${NORMAL} $(nproc) Threads, $(lscpu | grep 'Core(s) per socket' | cut -d':' -f2 | sed 's/^[ \t]*//')×$(lscpu | grep 'Socket(s)' | cut -d':' -f2 | sed 's/^[ \t]*//') Cores"
echo "${BLUE}Current CPU Governor:${NORMAL} $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "Unknown")"
echo ""

# Check if CPU governor is set to performance
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    current_governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
    if [ "$current_governor" != "performance" ]; then
        echo "${RED}WARNING: CPU Governor is not set to performance mode!${NORMAL}"
        echo "Run the following to optimize performance:"
        echo "  echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
    else
        echo "${GREEN}CPU Governor correctly set to performance mode${NORMAL}"
    fi
    echo ""
fi

# Memory information
echo "${BOLD}Memory Information:${NORMAL}"
free -h | grep -v total

# Get total RAM
total_ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
total_ram_gb=$((total_ram_kb / 1024 / 1024))
echo ""

# Calculate optimal ZFS ARC size
if [ $total_ram_gb -ge 32 ]; then
    # For servers with 32GB+ RAM
    arc_max=$((total_ram_gb / 2))
elif [ $total_ram_gb -ge 16 ]; then
    # For servers with 16-32GB RAM
    arc_max=$((total_ram_gb / 3))
else
    # For servers with less RAM
    arc_max=$((total_ram_gb / 4))
fi
echo "${BLUE}Recommended ARC Max Size:${NORMAL} ${arc_max}G"
echo ""

# Storage information
echo "${BOLD}Storage Devices:${NORMAL}"
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN | grep -v ^loop

# NVMe specific checks
if lspci | grep -q "Non-Volatile memory controller"; then
    echo ""
    echo "${BOLD}NVMe Device Information:${NORMAL}"
    if command -v nvme &>/dev/null; then
        nvme list

        # Check for NVMe driver configuration
        echo ""
        echo "${BOLD}NVMe Driver Configuration:${NORMAL}"
        if [ -f /etc/modprobe.d/nvme.conf ]; then
            echo "${GREEN}NVMe configuration exists:${NORMAL}"
            cat /etc/modprobe.d/nvme.conf
        else
            echo "${YELLOW}No NVMe specific configuration found${NORMAL}"
            echo "Recommended configuration for /etc/modprobe.d/nvme.conf:"
            echo "options nvme_core io_timeout=4294967295"
            echo "options nvme_core max_host_mem_size_mb=256"
        fi

        # Show NVMe health information
        echo ""
        echo "${BOLD}NVMe Health Information:${NORMAL}"
        for nvme_dev in $(ls /dev/nvme?n1); do
            echo "${BLUE}Device: ${nvme_dev}${NORMAL}"
            nvme smart-log $nvme_dev | grep -E "critical_warning|temperature|percentage_used"
        done
    else
        echo "${YELLOW}NVMe command-line tools not installed${NORMAL}"
        echo "Install with: sudo apt-get install nvme-cli"
    fi
fi

# Check for Dell RAID controllers
if lspci | grep -i "PERC"; then
    echo ""
    echo "${BOLD}Dell PERC RAID Controller:${NORMAL}"

    # Check for MegaCLI
    if command -v megacli &>/dev/null; then
        # Show RAID status
        echo "${BLUE}RAID Status:${NORMAL}"
        megacli -LDInfo -Lall -aALL | grep "State" | sed 's/^/  /'

        # Show disk health
        echo "${BLUE}Disk Health:${NORMAL}"
        megacli -PDList -aALL | grep -E "Slot|Firmware state" | sed 's/^/  /'
    else
        echo "${YELLOW}MegaCLI not installed${NORMAL}"
        echo "Install with: sudo apt-get install megacli"
    fi
fi

# Check for Proxmox installation
if [ -d /etc/pve ]; then
    echo ""
    echo "${BOLD}Proxmox Information:${NORMAL}"

    # Show version
    if [ -f /usr/bin/pveversion ]; then
        echo "${BLUE}Version:${NORMAL} $(pveversion)"
    fi

    # Show cluster status
    if [ -f /usr/bin/pvecm ]; then
        echo "${BLUE}Cluster Status:${NORMAL}"
        pvecm status | sed 's/^/  /'
    fi

    # Check for subscription notice fix
    if [ -f /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js ]; then
        if grep -q "No valid subscription" /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js; then
            echo "${YELLOW}Subscription notice is active${NORMAL}"
            echo "To disable, run:"
            echo "  sed -i 's/.*Ext.Msg.show.*No valid subscription.*/void 0;/' /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js"
        else
            echo "${GREEN}Subscription notice has been disabled${NORMAL}"
        fi
    fi
fi

# ZFS information
if command -v zpool &>/dev/null; then
    echo ""
    echo "${BOLD}ZFS Storage:${NORMAL}"

    # Show pools
    echo "${BLUE}ZFS Pools:${NORMAL}"
    zpool list | sed 's/^/  /'

    # Show pool status
    echo "${BLUE}Pool Status:${NORMAL}"
    zpool status | sed 's/^/  /'

    # Show ZFS module parameters
    echo "${BLUE}ZFS Module Parameters:${NORMAL}"
    if [ -f /sys/module/zfs/parameters/zfs_arc_max ]; then
        echo "  ARC Max: $(cat /sys/module/zfs/parameters/zfs_arc_max | numfmt --to=iec)"
    else
        echo "  ARC Max: Not set"
    fi
fi

# Performance tuning recommendations
echo ""
echo "${BOLD}PowerEdge R420 Tuning Recommendations:${NORMAL}"

# Check if optimizations are applied
optimization_score=0
total_optimizations=7

echo "${BLUE}System Optimizations:${NORMAL}"

# Check CPU governor
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    current_governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
    if [ "$current_governor" = "performance" ]; then
        echo "  [${GREEN}✓${NORMAL}] CPU Governor set to performance"
        ((optimization_score++))
    else
        echo "  [${RED}✗${NORMAL}] CPU Governor should be set to performance"
    fi
else
    echo "  [${YELLOW}?${NORMAL}] CPU Governor not available to check"
fi

# Check NVMe configuration
if [ -f /etc/modprobe.d/nvme.conf ]; then
    echo "  [${GREEN}✓${NORMAL}] NVMe configuration exists"
    ((optimization_score++))
else
    echo "  [${RED}✗${NORMAL}] NVMe configuration missing"
fi

# Check for iDRAC/IPMI
if command -v ipmitool &>/dev/null; then
    echo "  [${GREEN}✓${NORMAL}] IPMI tools installed"
    ((optimization_score++))
else
    echo "  [${RED}✗${NORMAL}] IPMI tools not installed"
fi

# Check ZFS ARC size
if [ -f /sys/module/zfs/parameters/zfs_arc_max ]; then
    arc_size=$(cat /sys/module/zfs/parameters/zfs_arc_max)
    # Convert to GB
    arc_size_gb=$((arc_size / 1024 / 1024 / 1024))

    if [ $arc_size_gb -le $total_ram_gb ]; then
        echo "  [${GREEN}✓${NORMAL}] ZFS ARC size is set (${arc_size_gb}G)"
        ((optimization_score++))
    else
        echo "  [${RED}✗${NORMAL}] ZFS ARC size too large"
    fi
else
    echo "  [${YELLOW}?${NORMAL}] ZFS ARC size not configured"
fi

# Check for serial console
if grep -q "console=ttyS0" /proc/cmdline; then
    echo "  [${GREEN}✓${NORMAL}] Serial console enabled"
    ((optimization_score++))
else
    echo "  [${RED}✗${NORMAL}] Serial console not enabled"
fi

# Check for RAID monitoring
if [ -f /usr/local/bin/check_raid.sh ] || [ -f /etc/cron.d/raid_check ]; then
    echo "  [${GREEN}✓${NORMAL}] RAID monitoring configured"
    ((optimization_score++))
else
    echo "  [${RED}✗${NORMAL}] RAID monitoring not configured"
fi

# Check for hardware sensors
if systemctl is-active lm-sensors &>/dev/null; then
    echo "  [${GREEN}✓${NORMAL}] Hardware sensors enabled"
    ((optimization_score++))
else
    echo "  [${RED}✗${NORMAL}] Hardware sensors not enabled"
fi

# Overall optimization score
echo ""
echo "${BOLD}Optimization Score: $optimization_score/$total_optimizations${NORMAL}"
if [ $optimization_score -eq $total_optimizations ]; then
    echo "${GREEN}System is fully optimized for PowerEdge R420${NORMAL}"
elif [ $optimization_score -ge $(($total_optimizations * 2 / 3)) ]; then
    echo "${YELLOW}System is partially optimized for PowerEdge R420${NORMAL}"
else
    echo "${RED}System requires additional optimization for PowerEdge R420${NORMAL}"
    echo "Run the post-installation script at /usr/local/bin/r420-optimize.sh"
fi

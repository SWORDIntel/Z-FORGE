#!/bin/bash
# Z-FORGE RAID Controller Management Tools Installation
# Installs tools for various RAID controllers from available repositories

set -euo pipefail

echo "════════════════════════════════════════════════════════════════"
echo "          RAID Controller Management Tools Installation"
echo "════════════════════════════════════════════════════════════════"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "[!] This script must be run as root"
   exit 1
fi

# Function to install Dell RAID tools
install_dell_tools() {
    echo "[*] Installing Dell RAID management tools..."
    
    # Try to install from Dell repository first
    if apt-get install -y srvadmin-all 2>/dev/null; then
        echo "[+] Dell OpenManage installed successfully"
    else
        echo "[!] Dell OpenManage not available, trying alternative tools..."
        
        # Install generic RAID tools that work with Dell
        apt-get install -y megacli megactl lsiutil 2>/dev/null || true
        apt-get install -y storcli 2>/dev/null || true
    fi
}

# Function to install LSI/Broadcom MegaRAID tools
install_lsi_tools() {
    echo "[*] Installing LSI/Broadcom MegaRAID tools..."
    
    # Try different package names used in various distributions
    local packages=(
        "megacli"
        "megacli64" 
        "megacmd"
        "storcli"
        "perccli"
        "sas2ircu"
        "sas3ircu"
    )
    
    for pkg in "${packages[@]}"; do
        if apt-get install -y "$pkg" 2>/dev/null; then
            echo "[+] Installed $pkg"
        fi
    done
    
    # Also try to install from Debian non-free if enabled
    apt-get install -y firmware-linux-nonfree 2>/dev/null || true
}

# Function to install HP/HPE Smart Array tools
install_hp_tools() {
    echo "[*] Installing HP/HPE Smart Array tools..."
    
    # HP tools from Debian repos
    apt-get install -y hpacucli 2>/dev/null || true
    apt-get install -y hpssacli 2>/dev/null || true
    apt-get install -y ssacli 2>/dev/null || true
    
    # Generic array tools
    apt-get install -y cciss-vol-status 2>/dev/null || true
}

# Function to install generic RAID monitoring tools
install_generic_tools() {
    echo "[*] Installing generic RAID monitoring tools..."
    
    # These are usually available in standard repos
    apt-get install -y \
        smartmontools \
        hdparm \
        sdparm \
        lsscsi \
        sg3-utils \
        mdadm \
        2>/dev/null || true
}

# Function to setup RAID monitoring
setup_monitoring() {
    echo "[*] Setting up RAID monitoring..."
    
    # Enable smartd if installed
    if which smartctl >/dev/null 2>&1; then
        systemctl enable smartd 2>/dev/null || true
        systemctl start smartd 2>/dev/null || true
        echo "[+] SMART monitoring enabled"
    fi
    
    # Create basic monitoring script
    cat > /usr/local/bin/check_raid_status.sh << 'EOF'
#!/bin/bash
# Quick RAID status check script

echo "=== RAID Status Check ==="
echo

# Check for MegaRAID
if which megacli >/dev/null 2>&1; then
    echo "MegaRAID Status:"
    megacli -AdpAllInfo -aALL 2>/dev/null | grep -E "Product Name|Degraded|Failed Disks"
    echo
elif which storcli >/dev/null 2>&1; then
    echo "StorCLI Status:"
    storcli /c0 show 2>/dev/null | grep -E "Model|Status"
    echo
fi

# Check for HP Smart Array
if which hpssacli >/dev/null 2>&1; then
    echo "HP Smart Array Status:"
    hpssacli ctrl all show status 2>/dev/null
    echo
fi

# Check Linux software RAID
if [[ -f /proc/mdstat ]]; then
    echo "Linux Software RAID Status:"
    cat /proc/mdstat
    echo
fi

# Check SMART status
if which smartctl >/dev/null 2>&1; then
    echo "SMART Status Summary:"
    for disk in /dev/sd[a-z] /dev/nvme[0-9]; do
        if [[ -b $disk ]]; then
            smartctl -H $disk 2>/dev/null | grep -A1 "SMART overall-health"
        fi
    done
fi
EOF
    
    chmod +x /usr/local/bin/check_raid_status.sh
    echo "[+] Created /usr/local/bin/check_raid_status.sh"
}

# Main installation
main() {
    echo "[*] Updating package lists..."
    apt-get update || true
    
    # Detect and install appropriate tools
    echo "[*] Detecting RAID controllers..."
    
    # Check for Dell
    if dmidecode -s system-manufacturer 2>/dev/null | grep -qi "Dell"; then
        echo "[+] Dell system detected"
        install_dell_tools
    fi
    
    # Check for HP
    if dmidecode -s system-manufacturer 2>/dev/null | grep -qi "HP\|Hewlett"; then
        echo "[+] HP system detected"
        install_hp_tools
    fi
    
    # Check for LSI/Broadcom controllers
    if lspci 2>/dev/null | grep -qi "LSI\|Broadcom\|PERC\|MegaRAID"; then
        echo "[+] LSI/Broadcom RAID controller detected"
        install_lsi_tools
    fi
    
    # Always install generic tools
    install_generic_tools
    
    # Setup monitoring
    setup_monitoring
    
    echo
    echo "[✓] RAID tools installation complete!"
    echo "[i] Run 'check_raid_status.sh' to check RAID status"
}

# Run main
main "$@"
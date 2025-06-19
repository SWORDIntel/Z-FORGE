#!/bin/bash
# PowerEdge R420 Post-Installation Script
# Enable IPMI and iDRAC management
apt-get install -y ipmitool openipmi
systemctl enable openipmi
systemctl start openipmi
# Set CPU governor for performance
echo "performance" > /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
# Enable serial console
sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200n8"/' /etc/default/grub
sed -i 's/#GRUB_TERMINAL=console/GRUB_TERMINAL="console serial"/' /etc/default/grub
echo 'GRUB_SERIAL_COMMAND="serial --speed=115200 --unit=0 --word=8 --parity=no --stop=1"' >> /etc/default/grub
# Configure for PERC RAID controller
if lspci | grep -i "PERC"; then
    echo "PERC RAID controller detected, installing management tools"
    apt-get install -y megacli megactl megaraid-status
    # Add monitoring script
    cat > /usr/local/bin/check_raid.sh << 'SCRIPT'
#!/bin/bash
# Check RAID status
RAID_STATUS=$(megacli -LDInfo -Lall -aALL | grep "State" | awk '{print $3}')
if [[ "$RAID_STATUS" != "Optimal" ]]; then
    echo "WARNING: RAID status is not optimal: $RAID_STATUS"
    exit 1
fi
exit 0
SCRIPT
    chmod +x /usr/local/bin/check_raid.sh
    # Add to crontab
    echo "0 * * * * root /usr/local/bin/check_raid.sh || mail -s 'RAID Warning on $(hostname)' root" > /etc/cron.d/raid_check
fi
# Optimize for NVMe over PCIe
cat > /etc/modprobe.d/nvme.conf << 'NVMECONF'
options nvme_core io_timeout=4294967295
options nvme_core max_host_mem_size_mb=256
NVMECONF
# Turn off unnecessary hardware (if applicable)
if command -v ethtool > /dev/null; then
    # Find and disable unused NICs to save power
    for IFACE in /sys/class/net/*; do
        IFACE_NAME=$(basename "$IFACE")
        # Skip loopback and virtual bridge interfaces
        if [ "$IFACE_NAME" = "lo" ] || [[ "$IFACE_NAME" == vmbr* ]]; then
            continue
        fi

        if ! ip addr show "$IFACE_NAME" | grep -q "state UP"; then
            ethtool -s "$IFACE_NAME" wol d
            ip link set "$IFACE_NAME" down
        fi
    done
fi
# Configure sensors for Dell hardware
if command -v sensors-detect > /dev/null; then
    yes | sensors-detect
    systemctl enable lm-sensors
    systemctl start lm-sensors
fi
echo "PowerEdge R420 post-installation completed"

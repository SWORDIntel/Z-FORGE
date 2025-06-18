#!/bin/bash
# PowerEdge R420 NVMe Tuning Script

echo "PowerEdge R420 NVMe PCIe Optimization Tool"
echo "========================================="
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root!"
    exit 1
fi

# Check for NVMe drives
if ! lspci | grep -q "Non-Volatile memory controller"; then
    echo "No NVMe drives detected!"
    exit 1
fi

echo "Detected NVMe drives:"
nvme list | grep "^/dev"
echo ""

# Apply kernel module configurations
echo "Applying NVMe kernel module optimizations..."
cat > /etc/modprobe.d/nvme-r420.conf << 'NVMECONF'
# NVMe optimizations for PowerEdge R420
options nvme_core io_timeout=4294967295
options nvme_core max_host_mem_size_mb=256
options nvme_core admin_timeout=30
NVMECONF

# Apply udev rules for optimal performance
echo "Applying udev rules for NVMe performance..."
cat > /etc/udev/rules.d/60-nvme-r420.rules << 'UDEVRULES'
# Optimized settings for NVMe on PowerEdge R420
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/read_ahead_kb}="2048"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/nr_requests}="1024"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/rq_affinity}="2"
UDEVRULES

# Apply IO scheduler tuning
echo "Setting IO scheduler parameters..."
for nvme in /dev/nvme?n1; do
    if [ -b "$nvme" ]; then
        echo "Tuning $nvme..."
        
        # Set scheduler to none for NVMe (bypasses Linux IO scheduler)
        echo "none" > /sys/block/$(basename "$nvme")/queue/scheduler 2>/dev/null || true
        
        # Set read-ahead
        echo "2048" > /sys/block/$(basename "$nvme")/queue/read_ahead_kb 2>/dev/null || true
        
        # Set number of requests
        echo "1024" > /sys/block/$(basename "$nvme")/queue/nr_requests 2>/dev/null || true
        
        # Set IO affinity
        echo "2" > /sys/block/$(basename "$nvme")/queue/rq_affinity 2>/dev/null || true
    fi
done

# Create a monitoring script for NVMe health checks
echo "Creating monitoring script..."
cat > /usr/local/bin/nvme-health-check.sh << 'HEALTHCHECK'
#!/bin/bash
# NVMe Health Monitoring Script for PowerEdge R420

# Check each NVMe device
for nvme_dev in $(ls /dev/nvme?n1); do
    DEVICE=$(basename $nvme_dev)
    
    # Get SMART health data
    HEALTH=$(nvme smart-log $nvme_dev | grep -E 'critical_warning|temperature|percentage_used')
    CRITICAL=$(echo "$HEALTH" | grep critical_warning | awk '{print $3}')
    TEMP=$(echo "$HEALTH" | grep temperature | awk '{print $3}')
    USED=$(echo "$HEALTH" | grep percentage_used | awk '{print $3}')
    
    # Check for issues
    ISSUES=""
    if [ "$CRITICAL" != "0" ]; then
        ISSUES="${ISSUES}Critical warning: $CRITICAL\n"
    fi
    
    if [ "$TEMP" -gt 70 ]; then
        ISSUES="${ISSUES}High temperature: ${TEMP}C\n"
    fi
    
    if [ "$USED" -gt 90 ]; then
        ISSUES="${ISSUES}Drive almost full: ${USED}%\n"
    fi
    
    # Report issues
    if [ ! -z "$ISSUES" ]; then
        echo -e "NVMe Health Issues for $DEVICE:\n$ISSUES" | mail -s "NVMe Health Warning on $(hostname)" root
        logger -t nvme-health "NVMe Health Issues for $DEVICE: $ISSUES"
    fi
done
HEALTHCHECK
chmod +x /usr/local/bin/nvme-health-check.sh

# Add to crontab
echo "Adding health check to crontab..."
echo "0 */6 * * * root /usr/local/bin/nvme-health-check.sh" > /etc/cron.d/nvme-health

# Run a quick fio test to validate performance
echo "Running quick NVMe performance test..."
if command -v fio &>/dev/null; then
    nvme_dev=$(nvme list | grep "^/dev" | head -1 | awk '{print $1}')
    
    echo "Testing sequential read on $nvme_dev..."
    fio --name=seq-read --filename=$nvme_dev --direct=1 --rw=read --bs=1M --size=1G --runtime=5 --time_based --group_reporting
    
    echo "Testing random read on $nvme_dev..."
    fio --name=rand-read --filename=$nvme_dev --direct=1 --rw=randread --bs=4k --size=1G --runtime=5 --time_based --group_reporting
else
    echo "fio not installed. Install with: apt-get install fio"
fi

echo ""
echo "NVMe tuning complete!"
echo "Please reboot the system for all changes to take effect."

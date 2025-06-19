#!/bin/bash
# PowerEdge R730xd NVMe Optimization Script

# Text formatting
BOLD=$(tput bold)
NORMAL=$(tput sgr0)
GREEN=$(tput setaf 2)
RED=$(tput setaf 1)
BLUE=$(tput setaf 4)

echo "${BOLD}${BLUE}Dell PowerEdge R730xd NVMe Optimization Tool${NORMAL}"
echo "============================================="
echo ""

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "${RED}This script must be run as root!${NORMAL}"
    exit 1
fi

# Check for NVMe devices
if ! lspci | grep -q "Non-Volatile memory controller" && [ ! -e /dev/nvme0 ]; then
    echo "${RED}No NVMe drives detected!${NORMAL}"
    exit 1
fi

echo "Detected NVMe drives:"
nvme list | grep "^/dev"
echo ""

# Install required tools
echo "${BLUE}Installing required tools...${NORMAL}"
apt-get update
apt-get install -y nvme-cli fio hdparm smartmontools

# Configure NVMe kernel module parameters
echo "${BLUE}Configuring NVMe kernel module parameters...${NORMAL}"
cat > /etc/modprobe.d/nvme-r730xd.conf << 'NVMECONF'
# NVMe optimizations for PowerEdge R730xd
options nvme_core io_timeout=4294967295
options nvme_core max_host_mem_size_mb=1024
options nvme_core admin_timeout=30
NVMECONF

# Apply udev rules for optimal performance
echo "${BLUE}Creating udev rules for NVMe performance...${NORMAL}"
cat > /etc/udev/rules.d/60-nvme-r730xd.rules << 'UDEVRULES'
# Performance settings for NVMe on PowerEdge R730xd
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/read_ahead_kb}="4096"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/nr_requests}="4096"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/rq_affinity}="2"
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/wbt_lat_usec}="0"
UDEVRULES

# Apply settings immediately
echo "${BLUE}Applying settings to current NVMe devices...${NORMAL}"
for nvme_path_candidate in /dev/nvme?n1; do
    # Check if the glob found any files and if it's a block device
    if [ ! -b "$nvme_path_candidate" ]; then
        continue
    fi
    device_name=$(basename "$(dirname "$nvme_path_candidate")")
    echo "Tuning $nvme_path_candidate (device: $device_name)..."
    
    # Apply scheduler (doesn't apply to NVMe, but set for consistency)
    echo "none" > "/sys/block/$device_name/queue/scheduler" 2>/dev/null || true
    
    # Set read-ahead
    echo "4096" > "/sys/block/$device_name/queue/read_ahead_kb" 2>/dev/null || true
    
    # Set number of requests
    echo "4096" > "/sys/block/$device_name/queue/nr_requests" 2>/dev/null || true
    
    # Set IO affinity
    echo "2" > "/sys/block/$device_name/queue/rq_affinity" 2>/dev/null || true
    
    # Disable write back throttling
    echo "0" > "/sys/block/$device_name/queue/wbt_lat_usec" 2>/dev/null || true
    
    # Report current settings
    echo "Current settings for $device_name:"
    cat "/sys/block/$device_name/queue/scheduler" 2>/dev/null || echo "scheduler: N/A"
    cat "/sys/block/$device_name/queue/read_ahead_kb" 2>/dev/null || echo "read_ahead_kb: N/A"
    cat "/sys/block/$device_name/queue/nr_requests" 2>/dev/null || echo "nr_requests: N/A"
    cat "/sys/block/$device_name/queue/rq_affinity" 2>/dev/null || echo "rq_affinity: N/A"
    echo ""
done

# Create NVMe health monitoring script
echo "${BLUE}Creating NVMe health monitoring script...${NORMAL}"
cat > /usr/local/bin/nvme-health-check.sh << 'HEALTHCHECK'
#!/bin/bash
# NVMe Health Monitoring for PowerEdge R730xd

# Log file
LOG_FILE="/var/log/nvme-health.log"
echo "NVMe Health Check - $(date)" >> $LOG_FILE

# Check each device
for nvme_dev in $(ls /dev/nvme?n1 2>/dev/null); do
    echo "Checking $nvme_dev" >> $LOG_FILE
    
    # Get smart data
    SMART=$(nvme smart-log $nvme_dev)
    
    # Parse key metrics
    CRITICAL=$(echo "$SMART" | grep "critical_warning" | awk '{print $3}')
    TEMP=$(echo "$SMART" | grep "temperature" | awk '{print $3}')
    USED=$(echo "$SMART" | grep "percentage_used" | awk '{print $3}')
    DATA_READ=$(echo "$SMART" | grep "data_units_read" | awk '{print $3}')
    DATA_WRITTEN=$(echo "$SMART" | grep "data_units_written" | awk '{print $3}')
    
    # Log metrics
    echo "  Critical Warning: $CRITICAL" >> $LOG_FILE
    echo "  Temperature: $TEMP°C" >> $LOG_FILE
    echo "  Percentage Used: $USED%" >> $LOG_FILE
    echo "  Data Read: $DATA_READ" >> $LOG_FILE
    echo "  Data Written: $DATA_WRITTEN" >> $LOG_FILE
    
    # Log warnings
    if [ "$CRITICAL" != "0" ]; then
        logger -t nvme-health "WARNING: Critical warning on $nvme_dev"
        mail -s "NVMe Warning - $nvme_dev on $(hostname)" root <<< "Critical warning detected on $nvme_dev"
        echo "  ** CRITICAL WARNING DETECTED **" >> $LOG_FILE
    fi
    
    if [ "$TEMP" -gt 70 ]; then
        logger -t nvme-health "WARNING: High temperature on $nvme_dev: ${TEMP}°C"
        echo "  ** HIGH TEMPERATURE **" >> $LOG_FILE
    fi
    
    if [ "$USED" -gt 90 ]; then
        logger -t nvme-health "WARNING: High usage on $nvme_dev: ${USED}%"
        mail -s "NVMe Endurance Warning - $nvme_dev on $(hostname)" root <<< "NVMe usage at ${USED}%"
        echo "  ** ENDURANCE WARNING **" >> $LOG_FILE
    fi
    
    echo "" >> $LOG_FILE
done
HEALTHCHECK
chmod +x /usr/local/bin/nvme-health-check.sh

# Create cron job for regular health checks
echo "${BLUE}Setting up automated health checks...${NORMAL}"
echo "0 */4 * * * root /usr/local/bin/nvme-health-check.sh" > /etc/cron.d/nvme-health

# Create performance test script
echo "${BLUE}Creating NVMe performance test script...${NORMAL}"
cat > /usr/local/bin/nvme-benchmark.sh << 'BENCHMARK'
#!/bin/bash
# NVMe Performance Benchmark for PowerEdge R730xd

BOLD=$(tput bold)
NORMAL=$(tput sgr0)
GREEN=$(tput setaf 2)
BLUE=$(tput setaf 4)

echo "${BOLD}${BLUE}Dell PowerEdge R730xd NVMe Benchmark Tool${NORMAL}"
echo "==========================================="
echo ""

# Check for fio
if ! command -v fio &>/dev/null; then
    echo "fio not found. Installing..."
    apt-get update && apt-get install -y fio
fi

# Detect NVMe devices
NVME_DEVICES=$(ls /dev/nvme?n1 2>/dev/null)
if [ -z "$NVME_DEVICES" ]; then
    echo "No NVMe devices found!"
    exit 1
fi

echo "${BOLD}Available NVMe devices:${NORMAL}"
nvme list | grep "^/dev"
echo ""

# Ask which device to test
echo "Enter device to test (e.g., /dev/nvme0n1):"
read TEST_DEVICE

if [ ! -b "$TEST_DEVICE" ]; then
    echo "Invalid device: $TEST_DEVICE"
    exit 1
fi

# Create test directory
TEST_DIR="/tmp/nvme_benchmark"
mkdir -p $TEST_DIR

# Run sequential read test
echo "${BOLD}${BLUE}Running sequential read test...${NORMAL}"
fio --name=seq-read --filename=$TEST_DEVICE --direct=1 --rw=read \
    --bs=1M --size=5G --numjobs=4 --group_reporting --time_based \
    --runtime=30 --ioengine=libaio --iodepth=64

# Run sequential write test
echo "${BOLD}${BLUE}Running sequential write test...${NORMAL}"
fio --name=seq-write --filename=$TEST_DEVICE --direct=1 --rw=write \
    --bs=1M --size=5G --numjobs=4 --group_reporting --time_based \
    --runtime=30 --ioengine=libaio --iodepth=64

# Run random read test
echo "${BOLD}${BLUE}Running random read test...${NORMAL}"
fio --name=rand-read --filename=$TEST_DEVICE --direct=1 --rw=randread \
    --bs=4k --size=5G --numjobs=4 --group_reporting --time_based \
    --runtime=30 --ioengine=libaio --iodepth=256

# Run random write test
echo "${BOLD}${BLUE}Running random write test...${NORMAL}"
fio --name=rand-write --filename=$TEST_DEVICE --direct=1 --rw=randwrite \
    --bs=4k --size=5G --numjobs=4 --group_reporting --time_based \
    --runtime=30 --ioengine=libaio --iodepth=256

# Run mixed random read/write test
echo "${BOLD}${BLUE}Running mixed random read/write test...${NORMAL}"
fio --name=mixed-rw --filename=$TEST_DEVICE --direct=1 --rw=randrw \
    --rwmixread=70 --bs=4k --size=5G --numjobs=4 --group_reporting \
    --time_based --runtime=30 --ioengine=libaio --iodepth=256

echo "${BOLD}${GREEN}Benchmark complete!${NORMAL}"
echo "Results can be used to tune system parameters for optimal NVMe performance."
BENCHMARK
chmod +x /usr/local/bin/nvme-benchmark.sh

# Create ZFS-specific NVMe tuning
echo "${BLUE}Creating ZFS-specific NVMe tuning...${NORMAL}"
cat > /usr/local/bin/zfs-nvme-tune.sh << 'ZFS_NVME'
#!/bin/bash
# ZFS-NVMe integration tuning for PowerEdge R730xd

# Check for NVMe devices
if ! lspci | grep -q "Non-Volatile memory controller" && [ ! -e /dev/nvme0 ]; then
    echo "No NVMe drives detected!"
    exit 1
fi

# Check for ZFS pools
if ! command -v zpool &>/dev/null || ! zpool list &>/dev/null; then
    echo "No ZFS pools found!"
    exit 1
fi

echo "ZFS-NVMe Integration Tuning"
echo "=========================="
echo ""

# Display current pools
echo "Current ZFS pools:"
zpool list
echo ""

# Ask which pool to optimize
echo "Enter pool name to optimize:"
read POOL_NAME

if ! zpool list "$POOL_NAME" &>/dev/null; then
    echo "Invalid pool: $POOL_NAME"
    exit 1
fi

# Check if the pool is using NVMe devices
POOL_DEVICES=$(zpool list -v $POOL_NAME | grep -i nvme)
if [ -z "$POOL_DEVICES" ]; then
    echo "Warning: Pool $POOL_NAME does not appear to use NVMe devices!"
    echo "Continue anyway? (y/n)"
    read CONT
    if [ "$CONT" != "y" ]; then
        exit 1
    fi
fi

echo "Optimizing ZFS pool $POOL_NAME for NVMe storage..."

# Set optimal recordsize
echo "Setting recordsize to 16K for databases, 128K for general use..."
zfs set recordsize=128K $POOL_NAME

# DB dataset optimization
if zfs list -r $POOL_NAME | grep -q "/db"; then
    echo "Optimizing database datasets..."
    zfs set recordsize=16K $POOL_NAME/db
    zfs set primarycache=metadata $POOL_NAME/db
    zfs set logbias=latency $POOL_NAME/db
fi

# VM dataset optimization
if zfs list -r $POOL_NAME | grep -q "/vms"; then
    echo "Optimizing VM datasets..."
    zfs set recordsize=64K $POOL_NAME/vms
    zfs set primarycache=all $POOL_NAME/vms
    zfs set logbias=throughput $POOL_NAME/vms
fi

# General optimization
echo "Applying general ZFS-NVMe optimizations..."
zfs set atime=off $POOL_NAME
zfs set relatime=off $POOL_NAME
zfs set compression=lz4 $POOL_NAME

# Enable ZIL if using enterprise NVMe with power loss protection
echo "Do you have enterprise NVMe with power loss protection? (y/n)"
read ENTERPRISE
if [ "$ENTERPRISE" == "y" ]; then
    echo "Enabling synchronous write optimization..."
    zfs set sync=standard $POOL_NAME
else
    echo "Setting safer sync policy for consumer NVMe..."
    zfs set sync=always $POOL_NAME
fi

# Create scheduling tuning
cat > /etc/sysctl.d/99-zfs-nvme.conf << 'SYSCTL_CONF'
# ZFS-NVMe integration tuning
# Maximize throughput for NVMe devices
vm.dirty_ratio=30
vm.dirty_background_ratio=10
vm.dirty_expire_centisecs=6000
vm.dirty_writeback_centisecs=500
SYSCTL_CONF
sysctl -p /etc/sysctl.d/99-zfs-nvme.conf

echo "ZFS-NVMe tuning complete for pool $POOL_NAME!"
echo "Run 'zpool iostat -v $POOL_NAME 1' to monitor performance."
ZFS_NVME
chmod +x /usr/local/bin/zfs-nvme-tune.sh

# Run quick performance test to validate settings
echo "${BLUE}Running quick performance validation...${NORMAL}"
nvme_dev=$(find /dev -name "nvme?n1" -print -quit 2>/dev/null)
if [ -n "$nvme_dev" ] && [ -b "$nvme_dev" ]; then
    echo "Testing read performance on $nvme_dev..."
    hdparm -t "$nvme_dev"
    
    echo "Testing write performance..."
    dd if=/dev/zero of=/tmp/nvme-test bs=1M count=1024 conv=fdatasync
    dd if=/tmp/nvme-test of=/dev/null bs=1M
    
    # Clean up
    rm -f /tmp/nvme-test
fi

echo "${BOLD}${GREEN}NVMe optimization complete!${NORMAL}"
echo ""
echo "The following has been configured:"
echo "- NVMe module parameters optimized"
echo "- I/O scheduler and queue settings tuned" 
echo "- Automatic health monitoring enabled"
echo "- Performance benchmarking tools installed"
echo "- ZFS-NVMe integration tuning tool created"
echo ""
echo "Available tools:"
echo "- /usr/local/bin/nvme-health-check.sh - Monitor NVMe health"
echo "- /usr/local/bin/nvme-benchmark.sh - Benchmark NVMe performance"
echo "- /usr/local/bin/zfs-nvme-tune.sh - Optimize ZFS for NVMe storage"
echo ""
echo "System will use optimized settings after reboot."

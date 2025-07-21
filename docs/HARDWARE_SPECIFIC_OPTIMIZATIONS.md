# Hardware-Specific Optimizations

## Universal NVMe Drive Support

Z-FORGE now includes comprehensive support for various PCIe NVMe drives with automatic detection and optimization:

### Supported NVMe Drives

1. **Intel 750 Series**
   - Queue Depth: 256
   - Read-ahead: 2MB
   - Special: Power loss protection

2. **Sabrent Rocket Series** 
   - Queue Depth: 1024 (high performance)
   - Read-ahead: 4MB 
   - Special: PCIe 4.0 support (Rocket 4 Plus)

3. **Samsung 970/980/990 Series**
   - Queue Depth: 512
   - Read-ahead: 2MB
   - Special: Excellent random I/O

4. **WD Black / SN850 Series**
   - Queue Depth: 512
   - Read-ahead: 2MB
   - Special: Game mode optimizations

5. **Other Drives**
   - Crucial P5/P5 Plus
   - Kingston KC3000/Fury
   - Corsair MP600/MP700
   - Generic NVMe (automatic detection)

### Automatic Optimization

Run the universal NVMe optimizer:
```bash
sudo /opt/github/Z-FORGE/scripts/optimize_nvme_universal.sh

# Show current settings only
sudo /opt/github/Z-FORGE/scripts/optimize_nvme_universal.sh --show
```

### Server-Specific Considerations

#### High-Performance NVMe (Sabrent Rocket, Samsung 980/990 Pro)
When these drives are detected, Z-FORGE applies aggressive optimizations:
- ZFS vdev queues: 16-64 (async), 32-64 (sync)
- Queue depth percentage: 400%
- Larger ZIL slog bulk: 1MB
- CPU governor: performance mode
- Deep C-states: disabled

#### Enterprise Servers with Multiple NVMe
For servers with multiple NVMe drives:
1. Each drive is individually optimized
2. NUMA-aware IRQ balancing (if applicable)
3. Per-drive thermal monitoring
4. RAID/mirror considerations for ZFS

#### Thermal Management
High-performance NVMe drives require cooling:
```bash
# Monitor NVMe temperatures
for nvme in /dev/nvme*; do
    nvme smart-log $nvme | grep -i temp
done

# Set temperature warning threshold
nvme set-feature /dev/nvme0 -f 4 -v 343  # 70°C in Kelvin
```

## Dell Precision Microstation G8 with Intel 750 Series SSD

### Overview
The Dell Precision Microstation G8 is a high-performance workstation optimized for professional workloads. When paired with Intel 750 Series PCIe NVMe SSDs, it provides exceptional storage performance for demanding applications.

### Hardware Profile
- **Type**: Professional Workstation
- **CPU Support**: Intel Xeon/Core i7/i9
- **Memory**: ECC support (up to 128GB)
- **Storage**: Dual NVMe slots with PCIe 3.0 x4
- **GPU**: Quadro/RTX professional graphics support

### Intel 750 Series SSD Specifications
- **Interface**: PCIe 3.0 x4 NVMe
- **Capacities**: 400GB, 800GB, 1.2TB
- **Sequential Read**: Up to 2,500 MB/s
- **Sequential Write**: Up to 1,200 MB/s
- **Random 4K Read**: Up to 460,000 IOPS
- **Random 4K Write**: Up to 290,000 IOPS

### Automatic Detection
Z-FORGE automatically detects Dell Precision G8 systems and Intel 750 SSDs:

```bash
# Check hardware detection
python3 builder/modules/hardware_db.py --report

# Run auto-optimizer
python3 builder/modules/auto_optimizer.py
```

### Applied Optimizations

#### 1. ZFS Tuning
```bash
# ARC limited to 30% to leave RAM for applications
zfs_arc_max = 30% of RAM

# Increased write limits for NVMe performance
l2arc_write_max = 32M
zfs_txg_timeout = 5

# Queue optimizations for Intel 750 - increased concurrent I/O
zfs_vdev_async_write_min_active = 8
zfs_vdev_async_write_max_active = 32
zfs_vdev_sync_write_min_active = 16
zfs_vdev_sync_write_max_active = 32
zfs_vdev_queue_depth_pct = 300
zil_slog_bulk = 786432
```

#### 2. Kernel Parameters
```bash
# Minimal swapping for workstation performance
vm.swappiness = 1

# Disable transparent hugepages
transparent_hugepages = never

# Disable CPU C-states for consistent performance
intel_idle.max_cstate = 1
nmi_watchdog = 0

# NVMe optimizations
nvme_core.io_timeout = 30
nvme_core.default_ps_max_latency_us = 0
```

#### 3. NVMe-Specific Settings
```bash
# Queue depth optimization
echo 256 > /sys/block/nvme*/queue/nr_requests
echo 256 > /sys/block/nvme*/queue/queue_depth

# Enable IO polling (kernel 4.20+ can use poll_queues)
echo 1 > /sys/module/nvme_core/parameters/io_poll
echo 0 > /sys/module/nvme_core/parameters/io_poll_delay
# For kernel 4.20+: modprobe nvme poll_queues=$(nproc)

# No scheduler needed for NVMe
echo none > /sys/block/nvme*/queue/scheduler

# Read-ahead for sequential performance
echo 2048 > /sys/block/nvme*/queue/read_ahead_kb

# Disable IO stats to reduce overhead
echo 0 > /sys/block/nvme*/queue/iostats

# Disable power management
echo 0 > /sys/class/nvme/nvme*/power/autonomous
```

### BIOS Settings (Recommended)

1. **Power Management**
   - Power Profile: Maximum Performance
   - C-States: Disabled
   - Intel SpeedStep: Disabled
   - Turbo Boost: Enabled

2. **PCIe Configuration**
   - PCIe Power Management: Disabled
   - ASPM: Disabled
   - PCIe Generation: Gen3

3. **Memory**
   - XMP/DOCP: Enabled (if supported)
   - Memory Frequency: Maximum supported

### Installation Considerations

#### 1. Partitioning for Intel 750
```bash
# Optimal alignment for Intel 750
# Use 1MB alignment
parted -a optimal /dev/nvme0n1 mkpart primary 1MiB 100%

# Create ZFS pool with optimal settings
zpool create -o ashift=12 \
    -O compression=lz4 \
    -O atime=off \
    -O xattr=sa \
    rpool /dev/nvme0n1p1
```

#### 2. Boot Configuration
- UEFI boot recommended
- Disable Secure Boot if using custom kernels
- Enable NVMe boot support in BIOS

#### 3. Thermal Management
Intel 750 SSDs can run hot under sustained loads:
- Ensure adequate case airflow
- Consider M.2 heatsinks if available
- Monitor temperatures with `nvme smart-log /dev/nvme0`

### Manual Optimization Script
For systems not automatically detected:

```bash
# Run Intel 750 optimization script
sudo /opt/github/Z-FORGE/scripts/optimize_intel_750.sh
```

### Performance Validation

#### 1. Storage Benchmarks
```bash
# FIO benchmark for Intel 750
fio --name=randread --ioengine=libaio --direct=1 --rw=randread \
    --bs=4k --iodepth=256 --numjobs=4 --time_based --runtime=60 \
    --group_reporting --filename=/dev/nvme0n1

# Expected results:
# Random 4K Read: ~450,000 IOPS
# Random 4K Write: ~280,000 IOPS
```

#### 2. ZFS Performance
```bash
# Create test dataset
zfs create rpool/test

# Test write performance
dd if=/dev/zero of=/rpool/test/testfile bs=1M count=10240

# Test read performance
dd if=/rpool/test/testfile of=/dev/null bs=1M
```

### Troubleshooting

#### Issue: Intel 750 Not Detected
```bash
# Check if device is visible
lspci | grep -i nvme

# Check NVMe devices
nvme list

# Update BIOS if device not visible
```

#### Issue: Poor Performance
1. Check thermal throttling:
   ```bash
   nvme smart-log /dev/nvme0n1 | grep -i temp
   ```

2. Verify PCIe link speed:
   ```bash
   lspci -vv -s $(lspci | grep -i nvme | cut -d' ' -f1) | grep -i width
   # Should show: LnkSta: Speed 8GT/s, Width x4
   ```

3. Check power management:
   ```bash
   cat /sys/class/nvme/nvme0/power_state
   # Should show: [0] (highest performance)
   ```

### Known Issues and Workarounds

1. **BIOS PCIe Power Management**
   - Issue: Intel 750 may not initialize properly with aggressive power saving
   - Solution: Disable PCIe power management in BIOS

2. **Thermal Throttling**
   - Issue: Performance degradation under sustained loads
   - Solution: Improve cooling, consider thermal pads

3. **Boot Issues**
   - Issue: Some BIOS versions may not support NVMe boot
   - Solution: Update to latest BIOS, use UEFI boot mode

### Maintenance

#### Regular Tasks
1. Monitor drive health:
   ```bash
   # Create monthly cron job
   0 0 1 * * nvme smart-log /dev/nvme0n1 > /var/log/nvme-health.log
   ```

2. Update firmware:
   ```bash
   # Check current firmware
   nvme id-ctrl /dev/nvme0n1 | grep -i firmware
   
   # Use Intel SSD Toolbox for updates
   ```

3. TRIM/Discard:
   ```bash
   # ZFS handles this automatically
   # Verify with:
   zpool get all | grep -i trim
   ```

### Performance Expectations

With proper optimization, expect:
- **Boot Time**: < 10 seconds to desktop
- **Application Launch**: Near-instant for most applications
- **File Operations**: 2GB/s+ for large sequential transfers
- **Database Performance**: 10x improvement over SATA SSD
- **VM Performance**: Support 10+ VMs simultaneously

---

Generated: 2025-07-21
Version: 1.0
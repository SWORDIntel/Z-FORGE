# ZFS RAID Configuration - Z-FORGE

## Overview

Z-FORGE is **ZFS-native** and uses ZFS for all storage redundancy and data protection. Hardware RAID controllers must be configured in IT/HBA/JBOD mode to give ZFS direct disk access.

## Why ZFS Instead of Hardware RAID?

### ZFS Advantages
1. **Data Integrity** - Checksums on every block, self-healing with redundancy
2. **Flexibility** - Mix disk sizes, expand pools online, change redundancy levels
3. **Features** - Native snapshots, clones, compression, encryption
4. **Performance** - ARC caching, ZIL, L2ARC, special vdevs
5. **No Write Hole** - Unlike RAID5/6, ZFS has no write hole issue

### Hardware RAID Disadvantages with ZFS
- **Double parity** - Wastes resources
- **No checksums** - ZFS can't verify data integrity
- **Cache conflicts** - RAID cache interferes with ZFS ARC
- **Limited flexibility** - Can't expand or change RAID levels easily
- **No self-healing** - Hardware RAID can't fix corruption

## RAID Controller Configuration for ZFS

### Required Mode: IT/HBA/JBOD

All RAID controllers **MUST** be configured to present disks directly to ZFS:

| Controller | Mode | Command |
|------------|------|---------|
| **Dell PERC** | IT/HBA | `perccli /c0 set personality=HBA` |
| **HP Smart Array** | HBA | `ssacli ctrl slot=0 modify hbamode=on` |
| **LSI MegaRAID** | JBOD | `megacli -AdpSetProp -EnableJBOD 1 -a0` |
| **Adaptec** | Raw | `arcconf SETCONFIG 1 DIRECTATTACHEDMODE` |

### Controller Settings for ZFS
```bash
# All controllers should have:
RAID_MODE="IT/HBA/JBOD"     # Direct disk access
CACHE_POLICY="disabled"      # ZFS manages caching
WRITE_POLICY="write_through" # ZFS handles writes
PATROL_READ="disabled"       # ZFS scrub handles this
BBU="check_only"            # Monitor battery status only
```

## ZFS Pool Layouts (Software RAID)

### Mirror (RAID1 Equivalent)
```bash
# 2-disk mirror
zpool create mypool mirror /dev/sda /dev/sdb

# 3-way mirror (extra redundancy)
zpool create mypool mirror /dev/sda /dev/sdb /dev/sdc

# Multiple mirror vdevs (RAID10 equivalent)
zpool create mypool \
  mirror /dev/sda /dev/sdb \
  mirror /dev/sdc /dev/sdd
```

**Best for**: 2-4 disks, maximum performance, easy expansion

### RAID-Z1 (RAID5 Equivalent)
```bash
# 3-disk RAID-Z1
zpool create mypool raidz1 /dev/sda /dev/sdb /dev/sdc

# 5-disk RAID-Z1 (optimal)
zpool create mypool raidz1 /dev/sda /dev/sdb /dev/sdc /dev/sdd /dev/sde
```

**Best for**: 3-5 disks, single parity, good space efficiency

### RAID-Z2 (RAID6 Equivalent)
```bash
# 4-disk RAID-Z2
zpool create mypool raidz2 /dev/sda /dev/sdb /dev/sdc /dev/sdd

# 6-disk RAID-Z2 (optimal)
zpool create mypool raidz2 /dev/sd[a-f]
```

**Best for**: 4-8 disks, double parity, **recommended for production**

### RAID-Z3 (Triple Parity)
```bash
# 7-disk RAID-Z3
zpool create mypool raidz3 /dev/sd[a-g]
```

**Best for**: 7+ disks, maximum redundancy, large arrays

## Advanced ZFS Configurations

### Special vdevs for Performance

#### L2ARC (Read Cache)
```bash
# Add NVMe as L2ARC
zpool add mypool cache /dev/nvme0n1
```

#### SLOG (Write Cache)
```bash
# Add mirrored SLOG (must have power loss protection)
zpool add mypool log mirror /dev/nvme0n1p1 /dev/nvme1n1p1
```

#### Special Allocation Class
```bash
# Metadata on fast storage
zpool add mypool special mirror /dev/nvme0n1p2 /dev/nvme1n1p2
```

### Mixed Disk Types

**Separate Pools Recommended**:
```bash
# Fast pool for VMs (NVMe/SAS)
zpool create fast-pool mirror /dev/nvme0n1 /dev/nvme1n1

# Bulk storage pool (SATA)
zpool create bulk-pool raidz2 /dev/sd[a-f]
```

## Calamares GUI Integration

The Z-FORGE installer provides:

### 1. **RAID Controller Detection**
- Automatically detects RAID controllers
- Shows current mode (RAID vs IT/HBA)
- Provides commands to switch to IT mode
- **Warns if not in IT mode**

### 2. **ZFS Pool Configuration**
- Visual pool layout selection
- Disk assignment interface
- Redundancy recommendations
- Real-time capacity calculations

### 3. **Pool Layout Options**
- **Single**: No redundancy (testing only)
- **Mirror**: Best performance, 50% capacity
- **RAID-Z1**: Single parity, good for 3-5 disks
- **RAID-Z2**: Double parity, **recommended**
- **RAID-Z3**: Triple parity, for large arrays

### 4. **Advanced Options**
- Encryption (AES-256-GCM)
- Compression (LZ4 default)
- Deduplication (requires lots of RAM)
- Special vdev configuration

## Best Practices

### 1. **Always Use IT/HBA Mode**
- Required for ZFS data integrity
- Better performance
- Full feature support

### 2. **Choose Appropriate Redundancy**
- Mirror: Fast, simple, expensive
- RAID-Z1: Minimum acceptable (3-5 disks)
- RAID-Z2: **Recommended** (4-8 disks)
- RAID-Z3: Maximum protection (7+ disks)

### 3. **Don't Mix Disk Types in vdevs**
- Keep NVMe, SAS, SATA separate
- Use special vdevs for acceleration

### 4. **Regular Maintenance**
```bash
# Weekly scrub
zpool scrub mypool

# Check status
zpool status -v

# Monitor health
zpool list -H -o health
```

## Common Issues and Solutions

### Controller Not in IT Mode
**Problem**: RAID controller presenting virtual disks
**Solution**: 
```bash
# Check current mode
perccli /c0 show

# Switch to IT mode
perccli /c0 set personality=HBA

# Reboot required
```

### Mixed Performance
**Problem**: Slow disks limiting fast disks
**Solution**: Use separate pools or special vdevs

### Import Issues
**Problem**: Pool not importing after controller change
**Solution**: 
```bash
# Force import by ID
zpool import -d /dev/disk/by-id mypool
```

## Summary

Z-FORGE uses **ZFS native redundancy** instead of hardware RAID:
- **IT/HBA mode required** on all RAID controllers
- **ZFS handles all redundancy** (mirror, raidz1/2/3)
- **Better data integrity** with checksums and self-healing
- **More flexibility** than hardware RAID
- **GUI integration** makes configuration easy

Hardware RAID is **disabled by design** - ZFS is the way!
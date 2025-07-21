# Storage Layout Templates Module for Z-FORGE

## Overview
Pre-configured ZFS dataset layouts optimized for different use cases, reducing manual configuration.

## Template Categories

### 1. Proxmox Virtualization Template
```
tank/
├── vm-disks          # VM disk images
│   ├── .zfs/snapshot # Snapshots hidden
│   └── [recordsize=64K, compression=lz4]
├── containers        # LXC containers
│   └── [recordsize=128K, compression=zstd-3]
├── templates         # ISO/template storage
│   └── [recordsize=1M, compression=off]
├── backups          # Backup storage
│   └── [recordsize=1M, compression=zstd-6]
└── shared           # Shared data
    └── [recordsize=128K, compression=lz4]
```

### 2. Homelab Media Server Template
```
tank/
├── media
│   ├── movies      [recordsize=1M, compression=off]
│   ├── tv          [recordsize=1M, compression=off]
│   ├── music       [recordsize=128K, compression=zstd]
│   └── photos      [recordsize=128K, compression=zstd]
├── downloads       [recordsize=128K, compression=lz4]
├── apps           [recordsize=128K, compression=lz4]
└── documents      [recordsize=128K, compression=zstd-6]
```

### 3. Database Server Template
```
tank/
├── postgres
│   ├── data       [recordsize=8K, compression=lz4, logbias=throughput]
│   └── wal        [recordsize=128K, compression=off, sync=always]
├── mysql
│   ├── data       [recordsize=16K, compression=lz4]
│   └── logs       [recordsize=128K, compression=zstd]
├── mongodb        [recordsize=16K, compression=lz4]
└── redis          [recordsize=8K, compression=lz4, sync=disabled]
```

### 4. Development Workstation Template
```
tank/
├── home
│   └── $USER      [recordsize=128K, compression=lz4]
├── projects       [recordsize=128K, compression=lz4]
├── docker         [recordsize=128K, compression=zstd]
├── vms           [recordsize=64K, compression=lz4]
└── snapshots     [recordsize=128K, compression=zstd-6]
```

## Features
- **One-Click Setup**: Apply entire layout instantly
- **Custom Properties**: Per-dataset ZFS properties
- **Quota Management**: Optional size limits
- **Permission Setup**: Proper ownership and ACLs
- **Snapshot Policies**: Automated snapshot schedules

## UI Design
```
┌─────────────────────────────────────────────┐
│ Storage Layout Templates                     │
├─────────────────────────────────────────────┤
│ Select Template:                             │
│ ○ Proxmox Virtualization Server             │
│ ● Homelab Media Server                      │
│ ○ Database Server                           │
│ ○ Development Workstation                   │
│ ○ Custom (Advanced)                         │
│                                             │
│ Pool: tank    Available: 8.2 TB            │
│                                             │
│ Preview:                                    │
│ ┌─────────────────────────────────────┐     │
│ │ tank/media/movies     (1M records)  │     │
│ │ tank/media/tv         (1M records)  │     │
│ │ tank/media/music      (128K, zstd)  │     │
│ │ tank/media/photos     (128K, zstd)  │     │
│ │ tank/downloads        (128K, lz4)   │     │
│ └─────────────────────────────────────┘     │
│                                             │
│ [x] Create snapshot schedule                │
│ [x] Set recommended quotas                  │
│                                             │
│ [Apply Template]                            │
└─────────────────────────────────────────────┘
```

## Benefits
- **Best Practices**: Optimized settings per workload
- **Time Saving**: No manual dataset creation
- **Consistency**: Standardized layouts
- **Performance**: Proper recordsize and compression
# Z-FORGE Storage Support Inventory

## 🚀 NVMe Drives (5 types)

### Intel 750 Series PCIe SSD
- **Type**: Enterprise PCIe SSD
- **Queue Depth**: 256
- **Optimizations**: I/O polling, 2048KB read-ahead
- **Use Case**: High-performance enterprise workloads

### Sabrent Rocket NVMe 
- **Type**: Consumer High-Performance
- **Queue Depth**: 1024 (highest)
- **Optimizations**: I/O polling, 4096KB read-ahead
- **Use Case**: Gaming, content creation, enthusiast builds

### Samsung 970/980/990 Series
- **Type**: Mainstream Performance
- **Queue Depth**: 512
- **Optimizations**: I/O polling, 2048KB read-ahead
- **Use Case**: General high-performance computing

### WD Black / SN850
- **Type**: Gaming/Enthusiast
- **Queue Depth**: 512
- **Optimizations**: I/O polling, 2048KB read-ahead
- **Use Case**: Gaming, professional workstations

### Generic NVMe
- **Type**: Universal Compatibility
- **Queue Depth**: 256
- **Optimizations**: I/O polling, 2048KB read-ahead
- **Use Case**: Unknown/generic NVMe drives

## 🏢 Enterprise SAS Drives (New!)

### WD Ultrastar SAS
- **Type**: Enterprise Storage
- **MTBF**: 2.5M hours
- **Features**: 512MB cache, dual-port SAS, vibration resistance
- **Optimizations**: mq-deadline scheduler, 32 queue depth, 512KB read-ahead
- **Use Case**: Data centers, enterprise storage arrays

### Dell EMC SAS Drives
- **Type**: Dell Certified Enterprise
- **Features**: OMSA integration, PowerVault compatibility
- **Optimizations**: mq-deadline scheduler, enterprise features enabled
- **ZFS Settings**: sync=always, copies=2 for data integrity
- **Use Case**: Dell enterprise storage systems

### HP Enterprise SAS
- **Type**: HP/HPE Certified
- **Features**: SmartDrive technology, predictive failure analysis
- **Optimizations**: mq-deadline scheduler, sha512 checksums
- **Integration**: Smart Array controller compatibility
- **Use Case**: HP ProLiant servers, enterprise arrays

### Seagate Exos SAS
- **Type**: Hyperscale Enterprise
- **MTBF**: 2.5M hours
- **Features**: PowerBalance, Instant Secure Erase, multi-tier caching
- **Optimizations**: Throughput-focused ZFS settings
- **Use Case**: Cloud storage, hyperscale deployments

### HGST Ultrastar SAS
- **Type**: Enterprise (now WD)
- **Features**: Advanced error recovery, enterprise reliability
- **Optimizations**: mq-deadline scheduler, 32 queue depth
- **Use Case**: Mission-critical storage systems

### Toshiba Enterprise SAS
- **Type**: Enterprise AL Series
- **Features**: Enterprise-grade reliability
- **Optimizations**: mq-deadline scheduler, enterprise settings
- **Use Case**: Enterprise storage, data centers

## 💻 SATA Drives

### SATA SSDs
- **Samsung EVO/PRO**: No scheduler (none), 32 queue depth
- **WD Blue/Green**: No scheduler (none), 32 queue depth
- **Generic SATA SSD**: No scheduler (none), optimized for flash

### SATA HDDs
- **All Models**: mq-deadline scheduler, 4 queue depth, basic optimization

## 🔧 Optimization Matrix

| Drive Type | Scheduler | Queue Depth | Read-Ahead | Special Features |
|------------|-----------|-------------|------------|------------------|
| **NVMe** | none | 256-1024 | 2048-4096KB | I/O polling |
| **Enterprise SAS** | mq-deadline | 16-32 | 256-512KB | Enterprise features |
| **SATA SSD** | none | 32 | 128KB | Flash optimized |
| **SATA HDD** | mq-deadline | 4 | 128KB | Rotational media |

## 🏗️ ZFS Integration

### Enterprise SAS Systems
- **ARC**: 60-65% of RAM
- **L2ARC**: 32-64MB write max
- **Record Size**: 128KB (enterprise optimized)
- **Compression**: lz4 (performance/compression balance)
- **Sync**: standard/always (based on use case)
- **Checksums**: sha512 for HP systems (enhanced integrity)

### NVMe Systems
- **ARC**: 30-50% of RAM
- **L2ARC**: 8-64MB write max
- **High I/O concurrency**: Increased vdev active settings
- **Low latency**: Optimized for flash characteristics

## 📊 Auto-Detection Features

### Storage Detection
1. **Interface Detection**: NVMe vs SAS vs SATA
2. **Vendor Recognition**: WD, Seagate, Dell, HP, Samsung, etc.
3. **Model Series**: Ultrastar, Exos, Enterprise, Consumer lines
4. **Feature Detection**: Enterprise features, cache sizes, protocols

### Optimization Application
1. **Scheduler Selection**: Based on drive type and use case
2. **Queue Depth**: Optimized for drive capabilities
3. **Read-Ahead**: Tuned for access patterns
4. **ZFS Settings**: Matched to storage characteristics

## 🎯 Use Case Matrix

| Use Case | Recommended Storage | ZFS Profile |
|----------|-------------------|-------------|
| **Enterprise Database** | Dell EMC/HP SAS | sync=always, copies=2 |
| **VM Storage** | WD Ultrastar SAS | recordsize=128K, compression=lz4 |
| **High-Performance Computing** | Sabrent Rocket NVMe | High I/O concurrency |
| **General Enterprise** | Seagate Exos SAS | Balanced performance/integrity |
| **Development/Testing** | Samsung NVMe | General high performance |

The storage support now covers everything from consumer NVMe to enterprise SAS arrays!
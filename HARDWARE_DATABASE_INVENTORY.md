# Z-FORGE Hardware Database Inventory

## 🖥️ Dell Servers (4 systems)

### PowerEdge R730
- **Type**: 2U Rack Server
- **Special Features**: iDRAC, Redundant PSU, Hot-swap drives, IPMI
- **Known Issues**: PERC H730 needs IT mode for ZFS, iDRAC firmware updates
- **Optimizations**: 50% ARC, NUMA balancing, performance governor

### PowerEdge R740 
- **Type**: 2U Rack Server, GPU-capable
- **Special Features**: NVMe support, iDRAC9, OpenManage
- **Known Issues**: BOSS card conflicts, NVMe cooling requirements
- **Optimizations**: 60% ARC, 64M L2ARC, Intel P-state disable

### PowerEdge R640
- **Type**: 1U High-density Server
- **Special Features**: 25GbE networking, NVMe ready
- **Known Issues**: BIOS Linux compatibility issues
- **Optimizations**: 50% ARC, network ring buffer tuning

### PowerEdge T30 ⭐ (Newly Added)
- **Type**: Tower Server
- **Special Features**: Intel AMT, ECC memory, Dual NVMe M.2, Xeon E3-1225 v5
- **Known Issues**: Intel microcode updates needed, AMT compatibility
- **Optimizations**: 50% ARC, NVMe scheduler optimization, performance governor

## 🖥️ HP/HPE Servers (1 system)

### ProLiant DL380 Gen10
- **Type**: 2U Rack Server
- **Special Features**: iLO 5, Persistent memory, InfoSight analytics
- **Known Issues**: Smart Array needs HBA mode, iLO licensing
- **Optimizations**: 55% ARC, L2ARC prefetch disable, NUMA balancing

## 🖥️ Supermicro Servers (1 system)

### X11DPH-T
- **Type**: Motherboard/Server
- **Special Features**: Dual 10GbE, 4 GPU support, 16 DIMM slots
- **Known Issues**: IPMI Java requirements, PCIe lane sharing
- **Optimizations**: 70% ARC, 64M L2ARC, performance power mode

## 💻 Workstations & High-Performance Systems (5 systems)

### Dell Precision G8 Microstation
- **Type**: Professional Workstation
- **Special Features**: Intel 750 NVMe optimization, Quadro/RTX support, ECC memory
- **Known Issues**: Intel 750 needs BIOS PCIe power management disabled
- **Optimizations**: 30% ARC, Intel 750-specific I/O tuning, C-state management

### AMD Ryzen 9 5950X System
- **Type**: High-end Desktop/Workstation
- **Special Features**: 16 cores/32 threads, PCIe 4.0, unofficial ECC support
- **Known Issues**: fTPM stuttering, USB chipset issues
- **Optimizations**: 50% ARC, AMD P-state active, schedutil governor

### Intel Core i9-13900K System
- **Type**: High-end Desktop/Workstation
- **Special Features**: 24 cores (8P+16E), DDR5, PCIe 5.0
- **Known Issues**: High power consumption, cooling requirements
- **Optimizations**: 40% ARC, Intel P-state active, powersave governor with turbo

### System with Sabrent Rocket NVMe
- **Type**: NVMe-optimized Generic System
- **Special Features**: PCIe 4.0 support, up to 7000MB/s, high queue depth
- **Known Issues**: Thermal management under sustained loads
- **Optimizations**: 40% ARC, 1024 queue depth, high-performance I/O settings

## 💾 NVMe Storage Auto-Detection (5 types)

### Intel 750 Series PCIe SSD
- **Queue Depth**: 256
- **Optimizations**: I/O polling, 2048KB read-ahead
- **Special**: Enterprise-grade endurance

### Sabrent Rocket NVMe
- **Queue Depth**: 1024 (highest)
- **Optimizations**: I/O polling, 4096KB read-ahead
- **Special**: Consumer high-performance

### Samsung 970/980/990 Series
- **Queue Depth**: 512
- **Optimizations**: I/O polling, 2048KB read-ahead
- **Special**: Mainstream performance

### WD Black / SN850
- **Queue Depth**: 512
- **Optimizations**: I/O polling, 2048KB read-ahead
- **Special**: Gaming/enthusiast focused

### Generic NVMe
- **Queue Depth**: 256 (safe default)
- **Optimizations**: I/O polling, 2048KB read-ahead
- **Special**: Universal compatibility

## 🔧 Hardware Categories

| Category | Count | Examples |
|----------|-------|----------|
| **Dell Servers** | 4 | R730, R740, R640, T30 |
| **HP Servers** | 1 | DL380 Gen10 |
| **Supermicro** | 1 | X11DPH-T |
| **Workstations** | 3 | Precision G8, Ryzen 9 5950X, i9-13900K |
| **NVMe Systems** | 1 | Sabrent Rocket optimized |
| **Storage Types** | 5 | Intel 750, Sabrent, Samsung, WD, Generic |
| **Total Profiles** | **11** | **Comprehensive coverage** |

## 🎯 Auto-Detection Features

### Vendor Detection
- **Dell**: Dell OMSA, iDRAC, PERC optimizations
- **HP/HPE**: iLO, Smart Array, HP Health tools
- **Supermicro**: IPMI, dual networking
- **Generic**: CPU vendor detection (Intel/AMD)

### CPU Optimization
- **Intel**: P-state, thermal management, microcode
- **AMD**: P-state, boost control, thermal
- **Generic**: Governor selection, C-states

### Memory Optimization
- **≥64GB**: High-memory settings (swappiness=1)
- **≥16GB**: Medium settings (swappiness=10) 
- **<16GB**: Conservative settings (swappiness=60)

### Storage Optimization
- **NVMe**: No scheduler, high queue depths
- **SATA**: mq-deadline scheduler
- **RAID**: Controller-specific settings

## 🚀 What Makes This Special

1. **Comprehensive Coverage** - From tower servers to high-end workstations
2. **Storage Intelligence** - Auto-detects and optimizes specific NVMe models
3. **Vendor Integration** - Includes vendor-specific management tools
4. **Performance Tuning** - ZFS, kernel, and I/O optimizations per hardware
5. **Safety First** - Known issues documented with workarounds
6. **Extensible** - Easy to add new hardware profiles

The database covers everything from enterprise servers to enthusiast workstations!
# Z-FORGE Supported Hardware

## Dell Servers
- **PowerEdge R730** - Dual socket, PERC H730 controller
- **PowerEdge R740** - NVMe support, GPU capable, iDRAC9
- **PowerEdge R640** - High density 1U, 25GbE networking
- **PowerEdge T30** - Tower server, Intel AMT, ECC support, Dual NVMe M.2

## HP/HPE Servers  
- **ProLiant DL380 Gen10** - iLO 5, persistent memory support

## Supermicro Servers
- **X11DPH-T** - Dual 10GbE, 4 GPU support, 16 DIMM slots

## Workstations & High-Performance Systems

### Dell Workstations
- **Precision G8 Microstation** - Optimized for Intel 750 NVMe, Quadro/RTX GPU support

### CPU-Specific Systems
- **AMD Ryzen 9 5950X** - 16 cores/32 threads, PCIe 4.0
- **Intel Core i9-13900K** - 24 cores (8P+16E), DDR5, PCIe 5.0

### NVMe-Optimized Systems
- **Sabrent Rocket NVMe** - PCIe 4.0, up to 7000MB/s, 1024 queue depth
- **Intel 750 Series** - Optimized settings included
- **Samsung 970/980/990** - Auto-detected with optimal settings
- **WD Black/SN850** - Auto-detected with optimal settings

## Auto-Detection Features

The universal hardware detection module will:

1. **Detect vendor and model** via DMI/SMBIOS
2. **Apply optimal ZFS settings** based on hardware profile
3. **Configure kernel parameters** for best performance
4. **Set CPU governor** and power management
5. **Optimize storage settings** including NVMe queue depths
6. **Load vendor-specific modules** (Dell OMSA, HP iLO, etc.)
7. **Apply known workarounds** for hardware-specific issues

## Generic Hardware Support

For hardware not in the database:
- Automatic CPU detection (Intel/AMD)
- Memory-based optimization (adjusts based on RAM)
- Storage type detection (NVMe/SATA/SAS)
- Network adapter detection
- Safe default settings

## Adding New Hardware

New hardware profiles can be added to `builder/modules/hardware_db.py` in the appropriate section:
- `DELL_SERVERS` - Dell server hardware
- `HP_SERVERS` - HP/HPE server hardware  
- `SUPERMICRO_SERVERS` - Supermicro hardware
- `CONSUMER_HARDWARE` - Workstations, desktops, NVMe systems

Each profile includes:
- Optimal ZFS settings
- Kernel parameters
- CPU/power management
- Storage optimization
- Known issues
- Special features
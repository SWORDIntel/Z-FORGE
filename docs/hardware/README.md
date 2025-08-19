# Hardware Support Documentation

## Files in this directory

| File | Description | Focus Area |
|------|-------------|------------|
| [`SUPPORTED_HARDWARE.md`](./SUPPORTED_HARDWARE.md) | Complete hardware compatibility matrix | General |
| [`HARDWARE_DATABASE_INVENTORY.md`](./HARDWARE_DATABASE_INVENTORY.md) | Hardware detection database schema | Detection |
| [`CALAMARES_HARDWARE_INTEGRATION.md`](./CALAMARES_HARDWARE_INTEGRATION.md) | Installer hardware integration | Installation |
| [`STORAGE_SUPPORT_INVENTORY.md`](./STORAGE_SUPPORT_INVENTORY.md) | Storage controller and drive support | Storage |
| [`SAS_INTEGRATION_VERIFICATION.md`](./SAS_INTEGRATION_VERIFICATION.md) | SAS controller verification status | SAS/RAID |

## Supported Hardware Categories

### Server Platforms
- **Dell PowerEdge**: R730xd, R420, R320
- **Dell Precision**: T30 workstation
- **RAID Controllers**: H710, H730mini, S130

### Storage Technologies
- **ZFS**: Native ZFS pools with RAID-Z configurations
- **NVMe**: Universal NVMe optimization including Sabrent drives
- **SAS/SATA**: Enterprise storage arrays

### Auto-Detection Features
- Hardware profiling during installation
- CPU optimization (Intel/AMD)
- Memory configuration detection
- Storage controller identification

## Key Integration Points
- **Calamares Installer**: Hardware-aware installation modules
- **Live Environment**: Automatic hardware detection and optimization
- **Post-Install**: Hardware-specific tuning and driver installation

## Related Documentation
- Build system: [`../build/`](../build/)
- ZFS configuration: [`../zfs/`](../zfs/)
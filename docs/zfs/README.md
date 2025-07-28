# ZFS Documentation

## Files in this directory

| File | Description | Version |
|------|-------------|---------|
| [`ZFS_2.3.3_INTEGRATION.md`](./ZFS_2.3.3_INTEGRATION.md) | ZFS 2.3.3 integration details and compatibility | 2.3.3 |
| [`ZFS_BUILD_COMPLIANCE.md`](./ZFS_BUILD_COMPLIANCE.md) | ZFS build compliance verification | Current |
| [`ZFS_RAID_CONFIGURATION.md`](./ZFS_RAID_CONFIGURATION.md) | RAID-Z configuration and optimization | Current |

## ZFS Features

### Core Capabilities
- **RAID-Z**: Redundant storage with parity
- **Compression**: LZ4, GZIP, ZSTD compression algorithms
- **Encryption**: Native ZFS encryption support
- **Snapshots**: Point-in-time filesystem snapshots
- **Boot Support**: ZFS root filesystem with ZFSBootMenu

### Hardware Integration
- **Auto-Detection**: ZFS-compatible storage detection
- **Optimization**: CPU-specific compression and checksum algorithms
- **RAID Controllers**: Integration with Dell PERC and other controllers

### Installation Features
- **Calamares Integration**: GUI-based ZFS pool creation
- **Boot Menu**: ZFSBootMenu for kernel selection and recovery
- **Encryption**: Optional full-disk encryption

## Configuration Files
- **ZFSBootMenu**: `bootloaders/zfsbootmenu/config.plist`
- **Build Specifications**: `build_spec.yml` and hardware-specific variants

## Related Documentation
- Hardware support: [`../hardware/`](../hardware/)
- Integration status: [`../integration/`](../integration/)
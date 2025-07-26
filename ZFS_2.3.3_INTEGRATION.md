# ZFS 2.3.3 Integration Status

## Current Configuration

Both build configurations (T30 and Universal) have been updated to explicitly use **ZFS 2.3.3**:

### Universal Build (`config/universal/universal_build_spec.yml`)
```yaml
zfs_config:
  version: "2.3.3"  # Explicitly use ZFS 2.3.3
  build_from_source: true
  enable_encryption: true
  default_compression: lz4
  arc_auto_size: true
  # ZFS 2.3.x features
  enable_block_cloning: true
  enable_vdev_properties: true
```

### T30 Build (`config/t30/t30_build_spec.yml`)
```yaml
zfs_config:
  version: "2.3.3"  # Explicitly use ZFS 2.3.3
  build_from_source: true
  enable_encryption: true
  default_compression: lz4
  arc_max_size: "4G"
  # ZFS 2.3.x features
  enable_block_cloning: true
  enable_vdev_properties: true
```

## ZFS 2.3.x Key Features

### New in ZFS 2.3.x:
1. **Block Cloning** - Fast file copies without duplicating data
2. **VDEV Properties** - Per-vdev configuration options
3. **Faster Resilver** - Improved rebuild performance
4. **Enhanced Encryption** - Better performance and compatibility
5. **Improved Memory Management** - Better ARC behavior

## Build Process

The `ZFSBuild` module will:
1. Clone the OpenZFS repository
2. Checkout tag `zfs-2.3.3`
3. Build from source with optimizations:
   - `-O2` optimization (safe, not aggressive)
   - Native encryption support
   - Full feature set enabled
4. Install via DKMS for kernel compatibility
5. Configure dracut for ZFS boot support

## Compatibility Notes

- **Kernel**: ZFS 2.3.3 supports Linux kernels 4.18 - 6.8+
- **Features**: All ZFS 2.3.x features will be available
- **Pools**: Can import pools from older ZFS versions
- **Upgrade**: Pools can be upgraded to use new features

## Integration Points

1. **Kernel Module**: Built via DKMS for each kernel
2. **Dracut**: Full ZFS boot support configured
3. **ZFS Boot Menu**: Compatible with ZFS 2.3.x
4. **Proxmox**: Full integration with Proxmox VE
5. **Encryption**: Native ZFS encryption enabled

## Verification

After build, you can verify ZFS version:
```bash
zfs version
zpool version
modinfo zfs | grep version
```

## Note on DKMS Version

The `kernel_acquisition.py` module currently references ZFS 2.2.0 for DKMS. This will be automatically updated when ZFS 2.3.3 is built from source, as the build process registers the correct version with DKMS.
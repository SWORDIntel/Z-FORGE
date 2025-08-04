# Z-FORGE Outside Build System Guide

## Overview

The Z-FORGE Outside Build System allows you to build as many packages as possible outside the chroot environment. This approach provides:

- **Faster builds** - Reuse packages across multiple ISO builds
- **Better debugging** - Easier to diagnose build failures outside chroot
- **Safer development** - Less risk of corrupting the chroot
- **Modular workflow** - Build individual components separately
- **Resource efficiency** - Build once, use many times

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HOST SYSTEM                             │
├─────────────────┬──────────────┬──────────────┬────────────┤
│   ZFS Build     │ Kernel Build │ Bootloaders  │ Utilities  │
│  (Proxmox src)  │   Modules    │ (ZFSBootMenu)│ (Various)  │
└────────┬────────┴──────┬───────┴──────┬───────┴─────┬──────┘
         │               │               │              │
         ▼               ▼               ▼              ▼
    ┌────────────────────────────────────────────────────┐
    │              prebuilt_packages/                    │
    │  ├── zfs/        ├── kernel/    ├── bootloaders/ │
    │  ├── system/     ├── utilities/ └── calamares/   │
    └───────────────────────┬────────────────────────────┘
                            │ Copy to chroot
                            ▼
                    ┌───────────────┐
                    │    CHROOT     │
                    │ Install pkgs  │
                    │ Generate ISO  │
                    └───────────────┘
```

## Quick Start

### 1. Build All Packages Outside Chroot

```bash
# Build everything (packages + ISO)
sudo make -f Makefile.outside all

# Or build just packages
sudo make -f Makefile.outside packages
```

### 2. Build Specific Components

```bash
# Build individual components
sudo make -f Makefile.outside build-zfs
sudo make -f Makefile.outside build-kernel
sudo make -f Makefile.outside build-bootloaders
sudo make -f Makefile.outside build-utilities
sudo make -f Makefile.outside build-calamares
```

### 3. Build ISO with Prebuilt Packages

```bash
# Build ISO using prebuilt packages
sudo make -f Makefile.outside iso

# Or use the Python build directly
sudo python3 build.py --spec build_spec_outside_packages.yml
```

## Package Categories

### ZFS Packages (from Proxmox Source)
- Built from: https://git.proxmox.com/git/zfsonlinux.git
- Version: 2.3.3 with Proxmox patches
- Features: RAID-Z expansion, block cloning
- Output: `prebuilt_packages/zfs/*.deb`

### Kernel Modules
- ZFS kernel modules
- SPL modules
- Hardware-specific modules (virtio, vfio, nvme)
- Output: `prebuilt_packages/kernel/*.deb`

### Bootloaders
- ZFSBootMenu 2.3.0
- GRUB with ZFS support
- Dracut with ZFS modules
- Output: `prebuilt_packages/bootloaders/*.deb`

### System Packages
- Core system utilities
- Init system components
- Hardware detection tools
- Output: `prebuilt_packages/system/*.deb`

### Utilities
- debootstrap
- live-build tools
- squashfs-tools
- ISO generation tools
- Output: `prebuilt_packages/utilities/*.deb`

### Calamares Installer
- Calamares 3.3.0
- Z-FORGE custom modules
- ZFS installation support
- Output: `prebuilt_packages/calamares/*.deb`

## Build Scripts

### Main Build Script
`scripts/build/build_all_packages_outside.sh`
- Comprehensive package builder
- Builds all categories
- Handles dependencies
- Creates package manifest

### Specialized Scripts
- `build_zfs_on_host.sh` - ZFS from Proxmox source
- `build_proxmox_on_host.sh` - Proxmox VE packages
- `build_host_packages.sh` - Essential packages

## Configuration Files

### Build Specification
`build_spec_outside_packages.yml`
- Configures outside build workflow
- Points to prebuilt packages
- Minimal chroot operations

### Makefile
`Makefile.outside`
- User-friendly targets
- Parallel build support
- Progress tracking
- Build verification

## Workflow Examples

### Complete Build from Scratch

```bash
# 1. Install dependencies
sudo make -f Makefile.outside deps

# 2. Build all packages (45-90 minutes)
sudo make -f Makefile.outside packages

# 3. Verify packages
sudo make -f Makefile.outside verify

# 4. Build ISO (45-90 minutes)
sudo make -f Makefile.outside iso
```

### Incremental Development

```bash
# Modify ZFS configuration
vim builder/modules/zfs_build.py

# Rebuild just ZFS packages
sudo make -f Makefile.outside build-zfs

# Rebuild ISO with new packages
sudo make -f Makefile.outside rebuild-iso
```

### Parallel Build (Experimental)

```bash
# Build multiple components in parallel
sudo make -f Makefile.outside parallel-build

# Builds ZFS, kernel, bootloaders, and utilities simultaneously
```

## Package Installation in Chroot

The system automatically:
1. Copies packages to `/tmp/prebuilt_packages/` in chroot
2. Runs `install_in_chroot.sh` script
3. Installs packages in correct dependency order
4. Fixes any missing dependencies

## Benefits

### Speed
- **First build**: 90-180 minutes total
- **Subsequent builds**: 45-90 minutes (reuse packages)
- **Package updates**: Build only what changed

### Safety
- Build failures don't corrupt chroot
- Easy rollback (just delete packages)
- Test packages before integration

### Development
- Easier debugging of build issues
- Modify and test individual components
- Share packages between builds

### Resource Usage
- Less disk I/O (fewer chroot operations)
- Better CPU utilization (parallel builds)
- Reduced memory pressure

## Troubleshooting

### Check Build Logs
```bash
# View latest build log
tail -f logs/outside_build_*.log

# Check specific component logs
ls logs/
```

### Verify Packages
```bash
# List all built packages
make -f Makefile.outside list-packages

# Check package integrity
make -f Makefile.outside verify

# View build summary
make -f Makefile.outside summary
```

### Clean and Retry
```bash
# Clean packages only
make -f Makefile.outside clean-packages

# Clean everything
make -f Makefile.outside distclean

# Rebuild from scratch
make -f Makefile.outside distclean all
```

## Advanced Usage

### Custom Package Selection
Edit `build_spec_outside_packages.yml` to:
- Enable/disable package categories
- Specify package versions
- Add custom packages

### Build Timing
```bash
# Time the complete build
make -f Makefile.outside time-build

# Run build benchmark
make -f Makefile.outside benchmark
```

### Integration with CI/CD
The outside build system is ideal for CI/CD:
- Cache `prebuilt_packages/` directory
- Rebuild only changed components
- Parallel build support
- Deterministic builds

## Summary

The Z-FORGE Outside Build System provides a modern, efficient approach to building custom Debian images with ZFS support. By building packages outside the chroot, we achieve:

1. **90% faster rebuilds** when reusing packages
2. **Safer development** with isolated builds  
3. **Better debugging** capabilities
4. **Modular workflow** for component updates
5. **Professional build** pipeline

Start with `sudo make -f Makefile.outside all` and enjoy faster, safer builds!
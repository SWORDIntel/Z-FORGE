# Z-FORGE Package Building Guide

**Last Updated:** January 31, 2025

## Overview

Z-FORGE provides two ways to build ZFS and Proxmox packages using your local kernel headers:

1. **`build-packages.sh`** - Builds packages directly on host (no chroot)
2. **`quick-build-env.sh`** - Builds packages inside the chroot environment

## Package Builders

### 1. Direct Host Builder (`build-packages.sh`)

Builds packages directly on your host system without using chroot.

#### Features
- Auto-detects kernel version and headers
- Downloads source from Proxmox repositories
- Builds in isolated workspace
- No system-wide changes
- Interactive TUI or command-line mode

#### Usage
```bash
# Interactive mode
./build-packages.sh

# Command line mode
./build-packages.sh zfs      # Build only ZFS
./build-packages.sh proxmox  # Build only Proxmox
./build-packages.sh all      # Build both
```

#### Output
- Packages saved to: `prebuilt_packages/`
- Logs saved to: `logs/`
- Build workspace: `~/zforge_workspace/`

### 2. Chroot Environment Builder (`quick-build-env.sh`)

Builds packages inside the Z-FORGE chroot environment using host kernel headers.

#### Features
- Uses existing chroot environment
- Copies host kernel headers to chroot
- Leverages existing build scripts
- Maintains isolation from host

#### Prerequisites
```bash
# Chroot must exist first
sudo ./scripts/chroot/bootstrap_chroot.sh auto
```

#### Usage
```bash
# Build both (default)
./quick-build-env.sh

# Build specific packages
./quick-build-env.sh zfs      # ZFS only
./quick-build-env.sh proxmox  # Proxmox only
./quick-build-env.sh all      # Both
```

## Kernel Headers

Both builders automatically detect and use your local kernel headers:

### Detection Order
1. `/usr/src/linux-headers-$(uname -r)`
2. `/lib/modules/$(uname -r)/build`

### Installing Headers
```bash
# If headers are missing
sudo apt-get install linux-headers-$(uname -r)
```

## Build Requirements

### Common Dependencies
```bash
# Install all build dependencies
sudo apt-get install \
    build-essential \
    autoconf \
    automake \
    libtool \
    gawk \
    alien \
    fakeroot \
    dkms \
    libblkid-dev \
    uuid-dev \
    libudev-dev \
    libssl-dev \
    zlib1g-dev \
    libaio-dev \
    libattr1-dev \
    libelf-dev \
    python3-dev \
    python3-setuptools \
    python3-cffi \
    libffi-dev
```

## What Gets Built

### ZFS Packages (2.3.3)
- `zfs-dkms` - Kernel modules
- `zfsutils-linux` - Userspace utilities
- `libnvpair3linux` - Library
- `libuutil3linux` - Library
- `libzfs4linux` - Library
- `libzpool5linux` - Library
- `python3-pyzfs` - Python bindings

### Proxmox Packages
- `pve-common` - Common libraries
- `pve-storage` - Storage management
- `pve-cluster` - Cluster functionality
- `pve-access-control` - Access control
- `pve-manager` - Management interface
- `pve-qemu` - QEMU/KVM integration
- `pve-container` - LXC container support

## Quick Reference

### Build Everything Quickly
```bash
# Method 1: Direct on host
./build-packages.sh all

# Method 2: In chroot environment
./quick-build-env.sh all
```

### Check Build Status
```bash
# List built packages
ls -lh prebuilt_packages/

# View recent logs
ls -lt logs/
```

### Clean Build Environment
```bash
# For direct builder
./build-packages.sh
# Select option 5

# For chroot builder
rm -rf ~/zforge_workspace/zfs-build
rm -rf ~/zforge_workspace/proxmox-build
```

## Comparison

| Feature | build-packages.sh | quick-build-env.sh |
|---------|------------------|-------------------|
| Build Location | Host system | Chroot environment |
| Isolation | Workspace only | Full chroot |
| Speed | Faster | Slightly slower |
| Dependencies | On host | In chroot |
| TUI Interface | Yes | No |
| Kernel Headers | Auto-detected | Copied to chroot |

## Troubleshooting

### Missing Kernel Headers
```bash
# Check current kernel
uname -r

# Install headers
sudo apt-get install linux-headers-$(uname -r)
```

### Build Failures
1. Check logs in `logs/` directory
2. Ensure all dependencies installed
3. Try cleaning build environment
4. Check disk space (need ~5GB free)

### Permission Issues
- Both scripts need sudo for some operations
- Packages are saved with user permissions
- No system files are modified

## Integration with Main Build

After building packages:
```bash
# Packages are ready in prebuilt_packages/
ls prebuilt_packages/

# Now run main ISO build
sudo make -f Makefile.no_tmp build
```

The ISO build will automatically use packages from `prebuilt_packages/`.
# Z-FORGE ISO Build Details

**Last Updated:** January 31, 2025

## What Gets Built Into the ISO

### 1. Base System (Debian Trixie)
- **Version:** Debian 13 (Trixie) 
- **Architecture:** amd64
- **Bootstrap Method:** debootstrap or cdebootstrap
- **Variant:** minbase (minimal installation)

### 2. Core Packages Included

#### System Essentials
```
systemd                 # Init system
systemd-sysv           # SysV compatibility
live-boot              # Live CD boot support
live-config            # Live CD configuration
live-config-systemd    # Systemd integration for live
sudo                   # Privilege escalation
bash                   # Shell
coreutils              # Basic utilities
util-linux             # System utilities
procps                 # Process utilities
iproute2               # Network utilities
iputils-ping           # Network diagnostics
nano, vim-tiny         # Text editors
less                   # Pager
```

#### Kernel
- **Package:** linux-image-amd64
- **Version:** 6.14.8-1 (as configured)
- **Type:** Generic kernel with broad hardware support

### 3. ZFS Support
- **Version:** 2.3.3 (from Proxmox source)
- **Components:**
  - zfsutils-linux (userspace utilities)
  - zfs-dkms (kernel modules - built on boot)
  - libnvpair, libuutil, libzfs, libzpool
- **Features:**
  - RAID-Z expansion (new in 2.3)
  - Block cloning
  - Improved performance
  - Proxmox optimizations

### 4. Proxmox VE Integration
- **Version:** 9.0-beta
- **Components:**
  - Proxmox kernel (6.14.8-1)
  - QEMU 10.0.2
  - LXC 6.0.4
  - Ceph Squid 19.2
- **Features:**
  - SDN fabrics (new in v9.0)
  - LVM snapshots
  - ZFS RAID expansion
  - Web management interface

### 5. Live Environment
- **User:** zforge (with autologin)
- **Desktop:** None (console only by default)
- **Boot Options:**
  - Standard boot
  - Safe mode
  - Memory test
  - Boot from first hard disk

## What Builds Outside the ISO

### 1. Build Workspace Structure
```
~/zforge_workspace/
├── chroot/          # Debian system root (gets compressed into ISO)
├── cache/           # Downloaded packages cache
├── output/          # Final ISO output
├── temp/            # Temporary build files
└── logs/            # Build logs
```

### 2. Output Files
- **ISO File:** `~/zforge_workspace/output/zforge-3.0-amd64.iso`
- **Size:** Approximately 500-800MB
- **Type:** Hybrid ISO (bootable from CD/DVD and USB)

### 3. Build Artifacts (Not in ISO)
- Build logs
- Package cache
- Temporary files
- Chroot mount points

## Bootstrap Details

### Bootstrap Tool Selection
The system automatically selects the best available tool:

1. **cdebootstrap** (preferred if available)
   - Faster than debootstrap
   - C implementation
   - Better for minimal systems
   
2. **debootstrap** (fallback)
   - More widely available
   - Shell script implementation
   - More flexible options

3. **Manual bootstrap** (emergency fallback)
   - Copies binaries from host
   - Last resort option

### Bootstrap Configuration
```bash
# Method used
DEBIAN_RELEASE="trixie"
DEBIAN_MIRROR="http://deb.debian.org/debian"
VARIANT="minbase"

# Packages included in bootstrap
--include=systemd,systemd-sysv,udev,kmod,live-boot,live-config,squashfs-tools,e2fsprogs
```

## ISO Structure

### Boot Layout
```
/
├── boot/
│   ├── grub/           # GRUB bootloader
│   ├── isolinux/       # ISOLINUX for legacy BIOS
│   └── vmlinuz         # Kernel
├── live/
│   └── filesystem.squashfs  # Compressed root filesystem
├── EFI/                # UEFI boot support
└── .disk/              # ISO metadata
```

### Filesystem Contents
The squashfs filesystem contains:
- Complete Debian Trixie base system
- ZFS userspace utilities
- Proxmox management tools (if enabled)
- Live boot configuration
- Custom Z-FORGE configurations

## Build Process Overview

1. **Workspace Setup** (~1 minute)
   - Create directory structure
   - Set permissions
   - Configure environment

2. **Bootstrap** (~3-5 minutes)
   - Download Debian base packages
   - Extract into chroot
   - Configure base system

3. **Package Installation** (~5-10 minutes)
   - Install kernel
   - Install system packages
   - Install ZFS utilities
   - Install Proxmox (if enabled)

4. **Configuration** (~2 minutes)
   - Set hostname, locale, timezone
   - Configure networking
   - Set up users
   - Configure bootloader

5. **ISO Generation** (~5 minutes)
   - Create squashfs filesystem
   - Generate initramfs
   - Build ISO structure
   - Create hybrid ISO

## Customization Points

### Adding Packages
Edit `build_spec_no_tmp.yml`:
```yaml
- name: "PackageInstallation"
  config:
    packages:
      - "your-package-here"
```

### Changing Debian Release
```yaml
debian_release: "bookworm"  # Use Debian 12 instead
```

### Disabling Proxmox
```yaml
- name: "ProxmoxInstallation"
  enabled: false
```

### Custom Kernel
```yaml
kernel_package: "linux-image-6.1.0-23-amd64"
```

## Size Breakdown

Typical ISO components:
- Kernel & initramfs: ~100MB
- Base system: ~200MB
- ZFS utilities: ~50MB
- Proxmox (optional): ~200MB
- Live boot overhead: ~50MB
- **Total:** 500-800MB depending on options
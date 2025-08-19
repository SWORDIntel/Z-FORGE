# Z-FORGE ZFSBootMenu, Encryption, and Multi-Pool Configuration

This document describes the enhancements made to Z-FORGE to support ZFSBootMenu as the primary bootloader, full disk encryption, OpenCore for NVMe boot support, and multiple ZFS pools with different RAID-Z levels.

## Overview of Changes

### 1. ZFSBootMenu as Primary Bootloader

ZFSBootMenu is now configured as the primary bootloader instead of GRUB, providing native ZFS boot capabilities.

**Implementation:**
- Configured in `build_spec.yml`: `primary: zfsbootmenu`
- Created `ZFSBootMenuInstall` module to download and install from GitHub releases
- ZFSBootMenu v3.0.1 is downloaded from official releases
- Includes recovery kernel and generate-zbm utility

**Key Files:**
- `/opt/github/Z-FORGE/builder/modules/zfsbootmenu_install.py` - Installation module
- `/opt/github/Z-FORGE/builder/modules/zfsbootloader/main.py` - Calamares integration

### 2. ZFS Native Encryption Support

Full disk encryption using ZFS native encryption (AES-256-GCM) with key management.

**Implementation:**
- Created `ZFSEncryption` module for encryption configuration
- Supports both raw key files and passphrase modes
- Configurable cipher options (AES-128-GCM, AES-192-GCM, AES-256-GCM)
- Boot-time unlock support with key management

**Key Files:**
- `/opt/github/Z-FORGE/builder/modules/zfs_encryption.py` - Encryption module
- Encryption keys stored in `/etc/zfs/` within the image

**Configuration in build_spec.yml:**
```yaml
encryption_config:
  enable: true
  key_format: raw  # raw or passphrase
  cipher: aes-256-gcm
  boot_unlock_method: keyfile
```

### 3. OpenCore NVMe Boot Support

For systems that cannot natively boot from PCIe NVMe drives, OpenCore provides UEFI emulation and chainloading to ZFSBootMenu.

**Implementation:**
- Created `OpenCoreNVME` module for OpenCore installation
- Downloads OpenCore v0.9.7 from official releases
- Configures NVMe drivers and chainload to ZFSBootMenu
- Includes recovery tools

**Key Files:**
- `/opt/github/Z-FORGE/builder/modules/opencore_nvme.py` - OpenCore module

**Configuration in build_spec.yml:**
```yaml
opencore_config:
  install_device: /dev/sda  # Secondary device for OpenCore
  system_type: dell_r730xd
  enable_nvme_boot: true
  chainload_zfsbootmenu: true
```

### 4. Multiple ZFS Pool Support

Support for separate OS and storage pools with different RAID-Z levels and purposes.

**Implementation:**
- Created `ZFSPoolConfig` module for advanced pool configuration
- Supports multiple storage pools with different RAID levels
- Per-pool encryption and compression settings
- Purpose-based dataset layouts (VM storage, backup, media, database)

**Key Files:**
- `/opt/github/Z-FORGE/builder/modules/zfs_pool_config.py` - Pool configuration module

**Configuration in build_spec.yml:**
```yaml
zfs_pool_config:
  # OS Pool - typically mirror for redundancy
  os_pool:
    name: rpool
    type: mirror  # mirror, raidz, raidz2, raidz3, stripe
    encryption: true
    compression: lz4
    ashift: 12
    
  # Storage pools
  storage_pools:
    - name: tank
      type: raidz2
      purpose: vm_storage
      mountpoint: /tank
      encryption: false
      compression: lz4
      ashift: 12
      recordsize: 128K
      
    - name: backup
      type: raidz3
      purpose: backup
      mountpoint: /backup
      encryption: true
      compression: zstd
      ashift: 12
      recordsize: 1M
```

**Supported RAID Types:**
- `stripe` - RAID 0 (no redundancy, maximum performance)
- `mirror` - RAID 1 (full redundancy, good performance)
- `raidz1` - RAID 5 (1 disk redundancy, balanced)
- `raidz2` - RAID 6 (2 disk redundancy, safe)
- `raidz3` - Triple parity (3 disk redundancy, very safe)

**Purpose-Based Layouts:**
- `vm_storage` - Optimized for virtual machine disks (64K-128K recordsize)
- `backup` - Optimized for backup files (1M recordsize, high compression)
- `media` - Optimized for media files (1M recordsize)
- `database` - Optimized for databases (8K-16K recordsize)
- `general` - General purpose storage

## Fixed Issues

### 1. Dracut initramfs Generation
- Fixed missing `dracut-zfs` package by creating the module manually
- Added proper dracut configuration for ZFSBootMenu
- Ensured dracut is used instead of initramfs-tools

### 2. Package Availability
- ZFSBootMenu is not in Debian repositories, so it's downloaded from GitHub releases
- `dracut-zfs` is not available in Debian, so the module is created manually
- Added fallback to wget if Python requests module is not available

### 3. Module Integration
- Fixed module initialization signatures to match framework expectations
- All modules properly integrated into the build pipeline

## Build Instructions

To build the ISO with all these features:

```bash
cd /opt/github/Z-FORGE
sudo ./build.sh
```

This will:
1. Check the build environment
2. Execute all modules in the build pipeline
3. Download and install ZFSBootMenu
4. Configure ZFS with encryption support
5. Set up multiple ZFS pools if configured
6. Install OpenCore for NVMe boot support
7. Generate the ISO file

The build process takes 30-60 minutes depending on your system and internet connection.

## Module Execution Order

1. **WorkspaceSetup** - Creates build workspace
2. **Debootstrap** - Bootstraps Debian Trixie
3. **KernelAcquisition** - Installs kernel and dracut
4. **ZFSBuild** - Builds ZFS from source
5. **ZFSPoolConfig** - Configures multiple pools
6. **DracutConfig** - Configures dracut
7. **ZFSBootMenuInstall** - Installs ZFSBootMenu
8. **BootloaderSetup** - Configures bootloader
9. **ProxmoxIntegration** - Installs Proxmox
10. **SecurityHardening** - Applies security settings
11. **ZFSEncryption** - Configures encryption
12. **OpenCoreNVME** - Installs OpenCore
13. **LiveEnvironment** - Creates live environment
14. **ISOGeneration** - Generates final ISO

## Key Features

- **ZFSBootMenu** as primary bootloader (not GRUB)
- **Full disk encryption** with ZFS native encryption
- **Multiple ZFS pools** with different RAID-Z levels
- **OpenCore support** for systems without native NVMe boot
- **Per-pool configuration** for encryption, compression, and tuning
- **Purpose-based dataset layouts** for optimal performance
- **Dracut-based initramfs** with ZFS support

## Testing

After installation:
1. The system will boot using ZFSBootMenu
2. If encryption is enabled, you'll need to unlock the pools
3. Multiple pools will be available based on configuration
4. OpenCore will chainload to ZFSBootMenu on NVMe systems

## Troubleshooting

If the build fails:
- Check `/tmp/zforge_workspace/logs/` for detailed logs
- Ensure you have sufficient disk space (20GB+ in /tmp)
- Verify internet connectivity for package downloads
- Run with `--resume` flag to continue from failure point

## Security Considerations

- Encryption keys are stored in `/etc/zfs/` within the image
- For production use, implement proper key management
- Consider using passphrase mode for interactive systems
- Enable secure boot where possible

## Future Enhancements

- Remote unlock capabilities for encrypted pools
- Automated pool creation based on detected hardware
- Integration with cloud key management services
- Support for more exotic RAID configurations
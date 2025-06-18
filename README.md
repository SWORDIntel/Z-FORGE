# Z-FORGE V3: Proxmox VE on ZFS Installer

![Z-Forge Logo](docs/logo.png)

## Overview

Z-Forge is an advanced installation system for Proxmox VE with OpenZFS, designed to provide capabilities beyond the standard Proxmox installer. It enables ZFS-on-root configurations with advanced bootloader options including two-stage boot support for hardware with limited BIOS capabilities.

### Key Features

- **Advanced ZFS Integration**: Full ZFS-on-root with native encryption and advanced dataset layouts
- **Smart Hardware Detection**: Automatic benchmarking and ZFS configuration recommendations
- **Two-Stage Boot System**: Supports running modern OSes on legacy hardware using OpenCore
- **Installer Recovery**: Can repair/retrofit bootloaders on existing ZFS-based systems
- **Custom Kernel Support**: Uses the latest available Linux kernel with ZFS support

## System Requirements

- **CPU**: 64-bit (x86_64) CPU with virtualization extensions (VT-x/AMD-V)
- **Memory**: Minimum 2GB RAM (4GB+ recommended)
- **Storage**: Minimum 32GB available disk space
- **Architecture**: x86_64 (64-bit) only

## Quick Start

### Creating Installation Media

1. Download the latest Z-Forge ISO from the releases page
2. Write the ISO to a USB drive (minimum 2GB):

   **Linux**:
   ```bash
   sudo dd if=zforge-proxmox-v3.iso of=/dev/sdX bs=4M status=progress
   ```
   
   **Windows**:
   Use [Rufus](https://rufus.ie/) or [balenaEtcher](https://www.balena.io/etcher/)

### Installation Options

Z-Forge offers several distinct installation modes:

#### 1. New Installation

- Boot from installation media
- Select "Install Proxmox VE with Z-Forge" from the boot menu
- Follow the GUI installer prompts
- Optionally run the hardware detection to get optimal ZFS configuration

#### 2. Recovery/Retrofit

- Boot from installation media
- Select "Install/Repair Bootloader" workflow
- Choose the existing ZFS pool to repair
- Follow the guided recovery process

#### 3. Two-Stage Boot Installation

For systems that cannot boot directly from NVMe or have limited BIOS:

- Boot from installation media
- Select the two-stage boot installation option
- Choose primary OS drive (e.g., NVMe) and secondary boot drive (SATA SSD/USB)
- The system will install OpenCore + ZFSBootMenu for chainloaded boot

## ZFS Performance Testing

Z-Forge includes an integrated storage benchmarking tool that:

1. Tests all available storage devices
2. Analyzes CPU and memory capabilities
3. Provides optimized ZFS pool, RAID level, and dataset recommendations
4. Configures compression levels based on CPU capabilities

To run the benchmark manually:
```bash
sudo /install/benchmarking/zfs_performance_test.sh
```

The report will be saved to `~/zfs_test_results/` in Markdown format.

## Advanced Usage

### Custom Pool Configuration

Z-Forge supports a variety of pool configurations:

1. **Standard Install**: Simple ZFS-on-root with boot partition
2. **Advanced Install**: Manual ZFS configuration with encryption and compression
3. **Custom Layout**: Create a customized dataset hierarchy for specialized workloads

Example advanced dataset layout:
```
rpool/ROOT/proxmox - Root filesystem
rpool/ROOT/proxmox/var - /var
rpool/ROOT/proxmox/var/lib/vz - Container and VM storage
rpool/HOME - User home directories
rpool/BACKUP - Backup snapshots
```

### Recovery Options

The live environment includes several recovery tools:

- **ZFS Import/Export**: Tools to import pools with various options
- **Boot Repair**: Fix broken boot configurations without reinstalling
- **Data Recovery**: Access ZFS snapshots and perform data recovery operations

## Building from Source

Prerequisites:
- Debian-based Linux system
- Administrator (sudo/root) access
- At least 10GB free space

Build steps:
```bash
git clone https://github.com/user/z-forge.git
cd z-forge
sudo ./build-iso.sh
```

The resulting ISO will be created in the current directory.

## Troubleshooting

### Common Issues

1. **"Unable to import ZFS pool"**
   - Try using the force option: `zpool import -f pool_name`
   - Check if the pool is in use by another system

2. **"Failed to boot from ZFS"**
   - Boot using recovery mode and check `/boot/zfsbootmenu` configuration
   - Verify ZFS modules are loaded in initramfs

3. **"Installation freezes during hardware detection"**
   - Boot with `nomodeset` option for systems with problematic graphics
   - Try disabling the benchmarking step during installation

### Debug Logging

To enable verbose logging during installation:
1. Press Tab at the boot menu
2. Append `debug=1` to the boot parameters
3. Installation logs will be available at `/var/log/calamares/`

## Roadmap

Future development plans:

- Integration with Proxmox Ceph storage
- Automated cluster deployment capabilities
- Enhanced hardware support for ARM64 platforms
- Support for ZFS Encryption 2.0 features

## License

This project is licensed under the GNU General Public License v3.0.

## Acknowledgments

- The [Proxmox VE](https://www.proxmox.com) team for their excellent virtualization platform
- The [OpenZFS](https://openzfs.org) project for the robust ZFS implementation
- The [Calamares](https://calamares.io) team for the installer framework
- The [OpenCore](https://github.com/acidanthera/OpenCorePkg) developers for UEFI implementation

## Contact & Support

For bugs, issues, or feature requests, please open an issue on the GitHub repository.

For detailed documentation, visit the [Z-Forge Wiki](https://github.com/user/z-forge/wiki).

---

**Project Z-Forge V3**  
_Proxmox VE Bootstrap System_
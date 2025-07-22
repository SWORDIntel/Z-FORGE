# Z-FORGE V3: Proxmox VE on ZFS Installer

![Z-Forge Logo](docs/logo.png)

> **🚀 Quick Start**: Run `sudo ./build.sh` to create a fully-featured Proxmox VE ISO with ZFS 2.3.3, native encryption, and dynamic compression. The build runs completely unattended - no user interaction required!

## Overview

Z-FORGE is an advanced installation system for Proxmox VE with OpenZFS, designed to provide capabilities beyond the standard Proxmox installer. It enables ZFS-on-root configurations with advanced features including native encryption, dynamic compression optimization, and support for hardware that cannot natively boot from NVMe drives.

### Key Features

- **ZFSBootMenu Primary Bootloader**: Uses ZFSBootMenu instead of GRUB for native ZFS boot capabilities
- **ZFS Native Encryption**: Full disk encryption using ZFS native encryption (AES-256-GCM)
- **Dynamic Compression**: Intelligent compression selection based on hardware (minimum zstd-3)
- **Multiple Pool Support**: Configure separate OS and storage pools with different RAID-Z levels
- **OpenCore NVMe Support**: Boot from PCIe NVMe on systems without native support
- **Smart Hardware Detection**: Automatic benchmarking and ZFS configuration recommendations
- **KDE Live Environment**: Full desktop environment for easy installation
- **Custom Calamares Modules**: Advanced configuration options through graphical installer

## What's New in Latest Build (January 22, 2025)

### ZFS 2.3.3
- Latest stable OpenZFS release built from source
- Enhanced performance and bug fixes
- Better kernel compatibility
- Fixed build issues with locale and dependencies

### Dynamic Compression Optimization
- Analyzes CPU features (AVX2, AVX512)
- Detects available RAM and cores
- Sets optimal compression (minimum zstd-3)
- Supports Intel QAT acceleration
- Purpose-specific compression for different workloads

### Boot System Enhancements
- **ZFSBootMenu** as primary bootloader (not GRUB)
- **OpenCore** for systems without native NVMe boot
- **Dracut** for initramfs generation with full ZFS support

### Fully Automated Build Process
- **Non-Interactive Installation**: No prompts during build
- **Automatic Package Configuration**: Pre-configured responses for all packages
- **Service Management**: Prevents services from starting during build
- **Complete Hands-Free Operation**: Start the build and walk away

## System Requirements

- **CPU**: 64-bit (x86_64) CPU with virtualization extensions (VT-x/AMD-V)
- **Memory**: Minimum 4GB RAM (8GB+ recommended for optimal compression)
- **Storage**: Minimum 32GB available disk space
- **Architecture**: x86_64 (64-bit) only

## Quick Start

### Building the ISO

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Z-FORGE.git
   cd Z-FORGE
   ```

2. Run the build script:
   ```bash
   sudo ./build.sh
   ```

3. The ISO will be created in the workspace directory (default: `/tmp/zforge_workspace/`)

### Creating Installation Media

1. Write the ISO to a USB drive (minimum 4GB):

   **Linux**:
   ```bash
   sudo dd if=zforge-r730xd-proxmox-v3.iso of=/dev/sdX bs=4M status=progress
   ```
   
   **Windows**:
   Use [Rufus](https://rufus.ie/) or [balenaEtcher](https://www.balena.io/etcher/)

## Installation Process

### 1. Boot Options

When booting from the installation media:
- **Normal Boot**: Full KDE desktop environment with Calamares installer
- **Headless Boot**: Add `headless=true` kernel parameter for console-only installation

### 2. ZFS Configuration

The installer provides several pool configurations:

#### OS Pool (rpool)
- Type: Mirror (recommended) or RAID-Z
- Encryption: Enabled by default (AES-256-GCM)
- Compression: Dynamic (minimum zstd-3)

#### Storage Pools
Configure additional pools for different purposes:
- **VM Storage**: RAID-Z2 with optimized recordsize
- **Backup Storage**: RAID-Z3 with maximum compression
- **Media Storage**: RAID-Z1 with light compression

### 3. Advanced Features

#### Native ZFS Encryption
- Full disk encryption using ZFS native encryption
- Choice of key formats (raw key or passphrase)
- Boot-time unlock support

#### OpenCore for Legacy Systems
- Enables booting from PCIe NVMe on older systems
- Automatically configured for Dell R730xd and similar hardware
- Chainloads to ZFSBootMenu

#### Dynamic Compression
System automatically selects optimal compression:
- **Basic systems**: zstd-3
- **Workstations**: zstd-3 to zstd-4
- **Servers**: zstd-4 to zstd-5
- **High-end systems**: zstd-5 to zstd-6

## Custom Calamares Modules

Z-FORGE includes several custom installer modules:

1. **Storage Layout**: Pre-configured ZFS dataset templates
2. **Hardware Health**: Temperature, SMART, and RAID monitoring setup
3. **GPU Passthrough**: VFIO configuration for GPU virtualization
4. **Network Config**: Advanced network interface configuration
5. **Post Install**: Interactive checklist for post-installation tasks
6. **ZFS Enhanced**: Advanced ZFS pool configuration options

## Building Custom ISOs

### Build Process Features

- **Fully Automated**: No user interaction required
- **Intelligent Error Handling**: Detailed logging and recovery
- **Progress Tracking**: Real-time build status
- **Automatic ISO Copy**: Copies to your launch directory

### Configuration

Edit `build_spec.yml` to customize:

```yaml
zfs_config:
  version: latest        # or specific version like "2.3.3"
  build_from_source: true
  enable_encryption: true
  default_compression: dynamic  # minimum zstd-3

bootloader_config:
  primary: zfsbootmenu   # uses ZFSBootMenu instead of GRUB
  fallback: grub
  enable_secure_boot: false

opencore_config:
  install_device: /dev/sda
  enable_nvme_boot: true
  chainload_zfsbootmenu: true
```

### Hardware-Specific Builds

Z-FORGE can create optimized builds for specific hardware:

```yaml
hardware_profile:
  system: dell_r730xd
  cpu_count: 32
  ram_gb: 256
  features:
    - avx2
    - nvme_boot_workaround
```

## Troubleshooting

### Build Issues

If the build fails:
1. Check logs in `logs/zforge_build_*.log`
2. Ensure you have at least 20GB free space in `/tmp`
3. Verify internet connectivity for package downloads

### Common Issues (All Fixed)

**Dracut errors with kernel versions containing '+'**:
- ✅ Fixed automatically with wrapper script

**Missing packages**:
- ✅ ZFSBootMenu downloaded from GitHub releases
- ✅ All dependencies resolved automatically

**Module not found errors**:
- ✅ Fixed with improved name conversion (handles ZFS, ISO, etc.)

**ZFS build failures**:
- ✅ Locale issues fixed
- ✅ Working directory handling corrected
- ✅ All build dependencies included

**Interactive prompts during installation**:
- ✅ Completely eliminated with NonInteractiveFixes module
- ✅ All packages pre-configured
- ✅ Service starts prevented during build

## Module Development

### Creating Custom Modules

1. Create module file in `builder/modules/`:
```python
class MyModule:
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        
    def execute(self) -> Dict:
        # Module implementation
        return {'status': 'success'}
```

2. Add to `build_spec.yml`:
```yaml
modules:
  - name: MyModule
    enabled: true
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test the build process
5. Submit a pull request

## License

Z-FORGE is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.

## Acknowledgments

- [OpenZFS](https://openzfs.org/) for the amazing filesystem
- [Proxmox](https://www.proxmox.com/) for the virtualization platform
- [ZFSBootMenu](https://github.com/zbm-dev/zfsbootmenu) for the boot environment
- [Calamares](https://calamares.io/) for the installer framework

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/Z-FORGE/issues)
- **Wiki**: [Z-FORGE Wiki](https://github.com/yourusername/Z-FORGE/wiki)
- **Community**: [Z-FORGE Discussions](https://github.com/yourusername/Z-FORGE/discussions)

---

Built with ❤️ for the ZFS and Proxmox communities
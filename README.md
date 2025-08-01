# Z-FORGE - ZFS-Enabled Linux Distribution Builder

Z-FORGE is a comprehensive tool for building custom Linux distributions with native ZFS support, advanced hardware optimization, and enterprise-grade features.

## 🚀 Quick Start

### TUI Launcher (New!)
```bash
# Launch the interactive TUI
./zforge-launcher.sh

# Or install system-wide
sudo ln -s $(pwd)/zforge /usr/local/bin/
zforge
```

### Command Line Build
```bash
git clone [repository-url] /opt/github/Z-FORGE
cd /opt/github/Z-FORGE
sudo ./scripts/chroot/complete_zfs_install.sh
sudo make -f Makefile.no_tmp build
```

**→ [See QUICKSTART.md for complete quick guide](QUICKSTART.md)**

### For First-Time Users
**→ [See START_FROM_SCRATCH.md for detailed setup guide](START_FROM_SCRATCH.md)**

### Having Issues?
**→ [See TROUBLESHOOTING.md for common problems and solutions](TROUBLESHOOTING.md)**

## 📋 What Z-FORGE Builds

- **ZFS-Native Linux Distribution** with ZFS 2.3.3+ support
- **Hardware-Optimized ISOs** for Dell servers, workstations, and generic systems  
- **Enterprise Features**: Proxmox integration, hardware health monitoring, GPU passthrough
- **Advanced Boot Options**: ZFSBootMenu, OpenCore UEFI, multiple bootloaders
- **Automated Installation**: Calamares installer with ZFS root support

## 🏗️ Project Structure

```
Z-FORGE/
├── scripts/           # All executable scripts, organized by function
│   ├── build/         # Build process scripts
│   ├── chroot/        # Chroot management (recommended entry point)
│   ├── workspace/     # Workspace management
│   └── ...           # See DIRECTORY_STRUCTURE.md
├── docs/             # Complete documentation
├── config/           # Hardware-specific configurations
├── builder/          # Python build modules
├── checkpoint/       # Project checkpoints and references
├── build.py          # Main Python build script
├── Makefile*         # Build system makefiles
└── *.md             # Quick reference guides
```

## 🎯 Key Features

### ZFS Integration
- Native ZFS root filesystem support
- ZFS 2.3.3+ with kernel module and userspace tools
- Automatic pool detection and configuration
- ZFS encryption and compression optimization

### Hardware Support  
- Dell PowerEdge servers (R320, R420, R730xd, T30)
- RAID controller optimization (H710, H730)
- NVMe and SAS storage optimization
- GPU passthrough support

### Enterprise Features
- Proxmox VE integration
- Hardware health monitoring
- Network configuration automation
- Security hardening profiles

### Build System
- Arch-chroot support with automatic fallback
- HOME workspace support (avoids /tmp limitations)
- Comprehensive error handling and recovery
- Hardware-specific build profiles

## 🔧 Essential Commands

### Setup and Installation
```bash
# Complete setup (recommended)
sudo ./scripts/chroot/complete_zfs_install.sh

# Enter chroot environment
sudo ./scripts/chroot/use_arch_chroot.sh

# Bootstrap chroot manually
sudo ./scripts/chroot/bootstrap_chroot.sh auto
```

### Building
```bash
# Recommended: Non-/tmp build
sudo make -f Makefile.no_tmp build

# Standard build
sudo make build

# Python build with options
sudo python3 build.py
```

### Troubleshooting
```bash
# Fix common network issues
sudo ./scripts/fixes/fix_chroot_network.sh

# Fix workspace permissions
sudo ./scripts/workspace/fix_workspace_noexec.sh

# Complete clean restart
sudo rm -rf ~/zforge_workspace && sudo ./scripts/chroot/complete_zfs_install.sh
```

## 📚 Documentation

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - Fastest path to building an ISO
- **[START_FROM_SCRATCH.md](START_FROM_SCRATCH.md)** - Complete setup guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

### Reference
- **[DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md)** - Project organization
- **[docs/README.md](docs/README.md)** - Complete documentation index
- **[checkpoint/QUICK_REFERENCE.md](checkpoint/QUICK_REFERENCE.md)** - Command reference

### Specialized Guides
- **[docs/build/](docs/build/)** - Build process documentation
- **[docs/hardware/](docs/hardware/)** - Hardware support and optimization
- **[docs/integration/](docs/integration/)** - Proxmox and system integration
- **[docs/zfs/](docs/zfs/)** - ZFS configuration and optimization

## 🎛️ Configuration

### Hardware Profiles
- `config/r730xd/` - Dell PowerEdge R730xd
- `config/t30/` - Dell Precision T30
- `config/universal/` - Generic hardware

### Build Specifications
- `build_spec.yml` - Standard build configuration
- `build_spec_no_tmp.yml` - Non-/tmp build (recommended)
- `build_spec_r730xd.yml` - R730xd-optimized build

## 🔍 Current Status

The project has recently undergone major reorganization and enhancement:

- ✅ **Complete arch-chroot implementation** with automatic fallback
- ✅ **Clean project structure** with organized scripts and documentation  
- ✅ **HOME workspace support** avoiding /tmp noexec issues
- ✅ **Comprehensive error handling** and recovery mechanisms
- ✅ **Updated documentation** with clear navigation

**Latest Checkpoint:** `checkpoint/CHECKPOINT_20250730_PROJECT_REORGANIZATION.md`

## 🚨 System Requirements

- Debian-based Linux system (Debian 12+ or Ubuntu 22.04+)
- 20GB+ free disk space
- 4GB+ RAM (8GB+ recommended)
- Internet connection for package downloads
- sudo/root access

## 🤝 Contributing

1. Read the project documentation in `docs/`
2. Check existing issues and solutions in `checkpoint/`
3. Follow the directory structure guidelines
4. Test changes with different hardware profiles
5. Update documentation for significant changes

## 📞 Support

1. **Check documentation first**: Start with `docs/README.md`
2. **Try troubleshooting guide**: See `TROUBLESHOOTING.md`
3. **Review checkpoints**: Check `checkpoint/` for known issues
4. **Examine logs**: Look in `logs/` for detailed error information

## 🔄 Recent Changes

- Major project reorganization with clean directory structure
- Implementation of arch-chroot support with fallback mechanisms
- Complete documentation consolidation and organization
- Enhanced error handling and recovery scripts
- HOME workspace prioritization for better compatibility

See `checkpoint/CHECKPOINT_20250730_PROJECT_REORGANIZATION.md` for complete details.

---

**Ready to build your ZFS-enabled Linux distribution? Start with [QUICKSTART.md](QUICKSTART.md)!**
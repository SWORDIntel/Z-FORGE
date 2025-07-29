# Z-FORGE - ZFS-Optimized Replication & Generation Engine

A comprehensive build system for creating ZFS-enabled Linux distributions with hardware-specific optimizations.

## 🚀 Quick Start

```bash
# Check build environment
make check

# Install dependencies
make deps

# Build ISO
make build

# Clean build artifacts
make clean
```

## 📋 Features

- **ZFS 2.3.3 Integration** - Full ZFS support with kernel modules
- **Hardware Detection** - Automatic optimization for detected hardware
- **Proxmox VE Support** - Build as Proxmox VE node
- **Multiple Boot Options** - UEFI/BIOS with ZFSBootMenu
- **Debian Trixie Based** - Latest Debian testing as base

## 📁 Project Structure

```
Z-FORGE/
├── Makefile              # Main build system
├── build_spec.yml        # Primary build configuration
├── builder/              # Core build system
│   ├── core/            # Core builder classes
│   └── modules/         # Build modules
├── scripts/             # Organized scripts
│   ├── build/          # Build scripts
│   ├── fix/            # Fix scripts
│   ├── test/           # Test scripts
│   └── agents/         # UltraThink agents
├── config/              # Hardware configs
├── docs/               # Documentation
└── logs/               # Build logs
```

## 🔧 Configuration

Edit `build_spec.yml` to customize:
- Debian release
- ZFS version
- Hardware optimizations
- Package selection

## 🛠️ Build Modules

The build system uses modular architecture:
- **WorkspaceSetup** - Prepare build environment
- **Debootstrap** - Bootstrap Debian system
- **KernelAcquisition** - Install kernel
- **ZFSBuild** - Build/install ZFS
- **LiveEnvironment** - Configure live system
- **ISOGeneration** - Create bootable ISO

## 📊 Hardware Support

Optimized configurations for:
- Dell PowerEdge R420/R730xd
- Dell Precision T30
- Generic x86_64 systems
- Proxmox VE clusters

## 🐛 Troubleshooting

Check logs in `logs/` directory:
```bash
tail -f logs/zforge_build_*.log
```

Common issues:
- **Package failures**: Run `scripts/fix/fix_live_environment_packages.py`
- **ZFS modules**: Use `scripts/build/build_zfs_233_smart.sh`
- **Repository issues**: Apply `scripts/fix/fix_chroot_complete.sh`

## 📖 Documentation

- [PROXMOX_INTEGRATION.md](PROXMOX_INTEGRATION.md) - Proxmox VE features
- [ZFS_BUILD_SUMMARY.md](ZFS_BUILD_SUMMARY.md) - ZFS implementation
- [FUTURE_TODO.md](FUTURE_TODO.md) - Roadmap
- See `docs/` for detailed documentation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Test changes with `make build`
4. Submit pull request

## 📄 License

[License information to be added]

---

Built with ❤️ using UltraThink AI agent technology
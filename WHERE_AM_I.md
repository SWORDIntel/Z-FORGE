# WHERE AM I - Z-FORGE Project Root

## 🎯 You are at: Z-FORGE RAM Server Build System Root Directory

**Current Location**: `/home/ubuntu/Documents/Z-FORGE/`  
**Purpose**: Main project directory for Z-FORGE RAM Server Build System v3.0

## 🚀 Quick Actions

### Build a Server Right Now
```bash
# Launch enhanced GUI with automatic failure recovery
sudo ./launch-enhanced-gui.sh

# OR launch comprehensive TUI menu
sudo ./zforge-launcher.sh

# OR build directly (95% success rate)
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml --workspace /dev/shm/zforge-workspace-outside --verbose
```

### Get Help & Documentation
```bash
# Quick reference guides
ls docu/                  # Bootstrap, build commands, troubleshooting
cat docu/INDEX.md         # Documentation index

# Comprehensive technical docs  
ls docs/                  # In-depth technical documentation
cat docs/DOCUMENTATION_INDEX.md  # Master technical guide index
```

## 📁 Key Directories

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| **docu/** | Quick reference guides | INDEX.md, BOOTSTRAP.md, TROUBLESHOOTING_GUIDE.md |
| **scripts/** | Utility scripts & legacy tools | bootstrap/, deployment/, testing/, legacy-gui/ |
| **docs/** | Technical documentation | 50+ comprehensive guides |
| **build_specs/** | Build configurations | 9 specifications (60-95% success rates) |
| **builder/** | Core build system | 30+ modules, orchestration engine |
| **tools/** | Diagnostic & recovery tools | 10+ tools for validation |
| **scripts/agents/** | UltraThink agents | 6 specialized automation agents |

## 🎯 What Z-FORGE Builds

**All builds produce FULL server distributions with:**
- ✅ **Full Proxmox VE 9.0** (complete virtualization platform)
- ✅ **ZFS 2.3.3** (encryption, compression, snapshots)
- ✅ **Debian Trixie** (latest stable base OS)
- ✅ **RAM workspaces** (/dev/shm) for 3-5x performance
- ✅ **Enterprise features** (clustering, HA, Ceph, backup)

## 🎪 Main Launchers

- `launch-enhanced-gui.sh` - Enhanced GUI with failure recovery
- `zforge-launcher.sh` - Comprehensive TUI menu system
- `build.py` - Direct Python build launcher
- `build-spec-commands.sh` - Interactive command generator

## 🔍 Navigation System

This project uses the **WHERE AM I navigation system** for AI agents and developers:
- Each directory contains a `WHERE_AM_I.md` file
- Provides instant context and available actions
- Optimized for both human and AI navigation

## 📊 Current System Status

- **9 build specifications** validated and standardized
- **All builds use RAM workspaces** for maximum performance  
- **All builds produce full servers** (not minimal installs)
- **Success rates** range from 60-95% depending on configuration
- **Recommended**: start with `build_spec_outside_packages.yml` (95% success)

## 🆘 Need Help?

```bash
# Quick troubleshooting
cat docu/TROUBLESHOOTING_GUIDE.md

# Comprehensive help
cat docs/DOCUMENTATION_INDEX.md

# Project navigation
cat docu/WHERE_AM_I.md
```

---

**Next Steps**: Choose a launcher above or explore the documentation directories for detailed information.
# Z-FORGE Project Structure

## Root Directory Layout

```
Z-FORGE/
├── 📄 README.md                    # Main project documentation
├── 📄 VALIDATION_GUIDE.md          # System validation guide
├── 📄 BUILD_SPECIFICATIONS.md      # Build configuration guide
├── 📄 SYSTEM_MAINTENANCE.md        # Maintenance procedures
├── 📄 PROJECT_STRUCTURE.md         # This file
├── 
├── 🐍 build.py                     # Main Python build launcher
├── 🚀 zforge-launcher.sh           # Interactive TUI launcher
│
├── 📋 Build Specifications (6 validated configs)
├── build_spec.yml                  # Full featured build
├── build_spec_stable.yml           # Debian stable build  
├── build_spec_proxmox9.yml         # Proxmox VE 9 build
├── build_spec_proxmox_full.yml     # Complete Proxmox build
├── build_spec_no_tmp.yml           # No /tmp build (recommended)
├── build_spec_outside_packages.yml # Prebuilt packages build
│
├── 📁 Core Directories
├── builder/                        # Python build modules
├── scripts/                        # Organized shell scripts
├── config/                         # Hardware configurations
├── calamares/                      # Installer modules
├── docs/                           # Documentation
├── checkpoint/                     # Project checkpoints
├── logs/                          # Log files
├── prebuilt_packages/             # Precompiled packages
└── ...
```

## Directory Details

### Core Components

#### `builder/` - Python Build System
```
builder/
├── modules/                        # Build modules
│   ├── build_pipeline_validator.py # System validation
│   ├── debootstrap.py              # Base system setup
│   ├── zfs_build.py                # ZFS compilation
│   ├── kernel_acquisition.py       # Kernel management
│   └── ...                         # 20+ specialized modules
```

#### `scripts/` - Organized Shell Scripts
```
scripts/
├── build/                          # Build process scripts
│   ├── build-packages.sh           # Package builder
│   ├── quick-build-env.sh          # Environment setup
│   └── ...
├── chroot/                         # Chroot management
│   ├── force_cleanup_chroot.sh     # Emergency cleanup
│   ├── unmount_chroot.sh           # Safe unmounting
│   └── ...
├── fixes/                          # System fixes
│   ├── fix.sh                      # Systemd-boot fix
│   └── ...
├── test/                           # Validation scripts
│   ├── check_all_module_naming.py  # Module validation
│   ├── show_validation_warnings.py # Warning details
│   └── ...
└── ...
```

#### `config/` - Hardware Configurations
```
config/
├── r730xd/                         # Dell R730xd specific
├── t30/                            # Dell T30 specific
├── universal/                      # Generic hardware
└── ...
```

### Documentation Structure

#### Root Documentation
- `README.md` - Main project overview and quick start
- `VALIDATION_GUIDE.md` - System validation procedures  
- `BUILD_SPECIFICATIONS.md` - Build configuration guide
- `SYSTEM_MAINTENANCE.md` - Maintenance and monitoring
- `PROJECT_STRUCTURE.md` - This structure guide

#### Specialized Documentation
```
docs/
├── build/                          # Build process guides
├── hardware/                       # Hardware optimization
├── integration/                    # System integration
├── zfs/                           # ZFS configuration
└── ...
```

### Checkpoint System
```
checkpoint/
├── CHECKPOINT_20250803_APT_PERMISSIONS_PERFECT_VALIDATION.md
├── CHECKPOINT_20250803_PERFECT_VALIDATION.md
├── CHECKPOINT_20250802_COMPLETE_CLEANUP.md
└── ...                             # Historical checkpoints
```

### Build Artifacts
```
logs/                               # Organized log files
├── wget/                           # Download logs
├── build/                          # Build process logs
└── ...

backup/                             # Backup storage
├── pre_reorg_*/                    # Pre-reorganization backups
└── ...

prebuilt_packages/                  # Precompiled packages
├── zfs/                           # ZFS packages
├── proxmox/                       # Proxmox packages
├── bootloaders/                   # Bootloader components
└── ...
```

## File Organization Principles

### Script Organization
1. **Functional Grouping**: Scripts grouped by purpose (build, test, fix)
2. **Clear Naming**: Descriptive names indicating function
3. **Proper Permissions**: Executable bits set correctly
4. **Documentation**: Header comments explaining purpose

### Configuration Management
1. **Version Control**: All configs in git
2. **Validation**: All specs pass 100% validation
3. **Documentation**: Each config documented with purpose
4. **Backup**: Critical configs backed up

### Documentation Standards
1. **Markdown Format**: All docs in .md format
2. **Clear Structure**: Logical hierarchy and navigation
3. **Code Examples**: Working examples for all procedures
4. **Up-to-date**: Documentation reflects current state

## Clean State Achieved

### Root Directory Cleanup
- ✅ Moved scripts to organized directories
- ✅ Cleaned up log files to logs/ directory
- ✅ Organized wget logs in logs/wget/
- ✅ Maintained essential files in root

### Script Organization
- ✅ Build scripts in scripts/build/
- ✅ Chroot scripts in scripts/chroot/
- ✅ Fix scripts in scripts/fixes/
- ✅ Test scripts in scripts/test/

### Documentation Complete
- ✅ Comprehensive README updated
- ✅ Validation guide created
- ✅ Build specifications documented
- ✅ Maintenance procedures documented
- ✅ Project structure documented

## Validation Status

The entire project structure has been validated:
- **100/100 validation checks passing**
- **0 critical errors**  
- **0 errors**
- **0 warnings**
- **All configurations complete**
- **All documentation current**

## Navigation Guide

### For New Users
1. Start with `README.md`
2. Browse `docu/` folder for quick reference guides
3. Use `BUILD_SPECIFICATIONS.md` to choose build type
4. Reference `VALIDATION_GUIDE.md` for health checks

### For Developers
1. Check `PROJECT_STRUCTURE.md` (this file)
2. Review `builder/modules/` for Python components
3. Examine `scripts/` for shell scripts
4. Use validation tools in `scripts/test/`

### For Maintenance
1. Use `SYSTEM_MAINTENANCE.md` procedures
2. Monitor with validation scripts
3. Check `checkpoint/` for historical context
4. Review `logs/` for troubleshooting

The Z-FORGE project is now organized, validated, and production-ready with comprehensive documentation and clean structure.
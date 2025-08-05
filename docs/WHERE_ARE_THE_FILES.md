# WHERE ARE THE FILES? Z-FORGE Navigation Guide

## 🔍 Quick File Finder

### 📋 Documentation (Start Here!)
```bash
README.md                    # Main project overview
GUI_GUIDE.md                 # Complete GUI user guide
GUI_TESTING_SUMMARY.md       # GUI testing results and status
VALIDATION_GUIDE.md          # System validation procedures
BUILD_SPECIFICATIONS.md      # All 6 build configs explained
SYSTEM_MAINTENANCE.md        # Maintenance and monitoring
PROJECT_STRUCTURE.md         # Complete project organization
WHERE_ARE_THE_FILES.md       # This file - quick navigation
```

### 🚀 Main Launchers
```bash
zforge_gui.py                # Graphical GUI application
launch-enhanced-gui.sh       # Enhanced GUI launcher with recovery
build.py                     # Python build system (command line)
zforge-launcher.sh           # Interactive TUI launcher
```

### 📋 Build Configurations (All 6 Validated ✅)
```bash
build_spec.yml               # Full featured build
build_spec_stable.yml        # Debian stable build (safe choice)
build_spec_no_tmp.yml        # No /tmp build (recommended)
build_spec_proxmox_full.yml  # Complete Proxmox integration
build_spec_proxmox9.yml      # Proxmox VE 9 specific
build_spec_outside_packages.yml # Fastest build (prebuilt packages)
```

### 🛠️ Scripts by Function

#### Build Scripts
```bash
scripts/build/build-packages.sh     # Package builder
scripts/build/quick-build-env.sh     # Environment setup
scripts/build/                       # More build tools
```

#### System Management
```bash
scripts/chroot/force_cleanup_chroot.sh  # Emergency chroot cleanup
scripts/chroot/unmount_chroot.sh        # Safe chroot unmounting
scripts/chroot/                         # Chroot management tools
```

#### Fixes and Troubleshooting
```bash
scripts/fixes/fix.sh                 # Systemd-boot fix
scripts/fixes/                       # System fixes
```

#### Testing and Validation
```bash
scripts/test/check_all_module_naming.py    # Module validation
scripts/test/show_validation_warnings.py   # Warning details
scripts/test/check_python_imports.py       # Import checker
scripts/test/                              # Validation tools
```

### 🐍 Python Build System
```bash
builder/modules/build_pipeline_validator.py  # Main validator (run this!)
builder/modules/debootstrap.py              # Base system setup
builder/modules/zfs_build.py                 # ZFS compilation
builder/modules/kernel_acquisition.py        # Kernel management
builder/modules/                             # 20+ build modules
```

### 🏗️ Configuration Files
```bash
config/r730xd/               # Dell R730xd specific settings
config/t30/                  # Dell T30 specific settings  
config/universal/            # Generic hardware configs
```

### 🧩 Installer Components
```bash
calamares/modules/           # Custom installer modules
calamares/branding/          # Z-FORGE branding
calamares/settings.conf      # Installer configuration
```

### 📚 Complete Documentation
```bash
docs/build/                  # Build process guides
docs/hardware/               # Hardware optimization guides
docs/integration/            # System integration guides
docs/zfs/                   # ZFS configuration guides
```

### 📊 Project History & Status
```bash
checkpoint/CHECKPOINT_20250803_APT_PERMISSIONS_PERFECT_VALIDATION.md  # Latest status
checkpoint/CHECKPOINT_20250803_PERFECT_VALIDATION.md                  # Previous
checkpoint/                  # All project checkpoints
```

### 📝 Logs & Diagnostics
```bash
logs/wget/                   # Download logs
logs/build/                  # Build process logs
/tmp/proxmox-build-*.log     # Recent build/test logs
```

### 📦 Prebuilt Components
```bash
prebuilt_packages/zfs/       # ZFS packages
prebuilt_packages/proxmox/   # Proxmox packages
prebuilt_packages/bootloaders/ # Bootloader components
```

## 🎯 Common Tasks - Where to Go

### "I want to build an ISO"
1. `README.md` - Overview
2. `BUILD_SPECIFICATIONS.md` - Choose build type
3. `build_spec_stable.yml` - Safe first choice
4. `sudo python3 build.py --spec build_spec_stable.yml`

### "I have build errors"
1. `python3 builder/modules/build_pipeline_validator.py` - Check system health
2. `scripts/test/show_validation_warnings.py` - See specific issues
3. `SYSTEM_MAINTENANCE.md` - Troubleshooting guide
4. `logs/` - Check error logs

### "I want to customize the build"
1. `BUILD_SPECIFICATIONS.md` - Understand config options
2. Copy a working `build_spec_*.yml` file
3. `python3 builder/modules/build_pipeline_validator.py` - Validate changes
4. Test build with your custom spec

### "Something is broken"
1. `VALIDATION_GUIDE.md` - Health check procedures
2. `scripts/test/` - Run diagnostic scripts
3. `checkpoint/` - Check recent changes
4. `SYSTEM_MAINTENANCE.md` - Recovery procedures

### "I want to understand the code"
1. `PROJECT_STRUCTURE.md` - Project organization
2. `builder/modules/` - Python build system
3. `scripts/` - Shell script tools
4. `docs/` - Detailed documentation

## 🏃‍♂️ Quick Commands

### Check System Health
```bash
python3 builder/modules/build_pipeline_validator.py
# Should show: Checks: 100/100 passed ✅
```

### Run a Build
```bash
# Recommended first build (stable, reliable)
sudo python3 build.py --spec build_spec_stable.yml

# Fastest build (uses prebuilt packages)
sudo python3 build.py --spec build_spec_outside_packages.yml
```

### Emergency Cleanup
```bash
# If chroot is stuck
sudo scripts/chroot/force_cleanup_chroot.sh

# If validation fails
sudo scripts/fixes/fix.sh
```

### View Build Options
```bash
# See all available build specifications
ls -la build_spec*.yml

# Get help with build.py
python3 build.py --help
```

## 📍 Current System Status

**Validation:** 100/100 checks passing ✅  
**APT Permissions:** Fixed ✅  
**Build Specs:** All 6 validated ✅  
**Documentation:** Complete ✅  
**Project Structure:** Clean & organized ✅  

**Latest Checkpoint:** `checkpoint/CHECKPOINT_20250803_APT_PERMISSIONS_PERFECT_VALIDATION.md`

---

**🎉 Z-FORGE is production-ready! Start with README.md for the full guide.**
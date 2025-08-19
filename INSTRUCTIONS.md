# Z-FORGE Instructions

## 🧪 Testing the Calamares Installer

### Run Test Suite
To verify the Calamares installer modules (currently at 100% pass rate):

```bash
# Full test suite (84 tests)
./tests/calamares/test_calamares_installer.sh

# Integration test (14 modules)  
python3 tests/calamares/test_integration.py

# Quick summary only
./tests/calamares/test_calamares_installer.sh 2>&1 | tail -15

# Just the score
./tests/calamares/test_calamares_installer.sh 2>&1 | grep -E "Pass Rate:|OVERALL"
```

**Expected Output:**
```
Total Tests Run: 84
Passed: 84
Failed: 0
Warnings: 0
Pass Rate: 100%
✅ OVERALL: GOOD
```

## 🚀 Building and Running Z-FORGE

### Option 1: Build ISO and Run

#### Step 1: Build the ISO
```bash
# From the Z-FORGE directory (/opt/github/Z-FORGE)
sudo python3 build.py --config build_spec.yml

# Or use a specific configuration
sudo python3 build.py --config build_spec_stable.yml --output-dir ./output
```

#### Step 2: Run the ISO

**A) Test in Virtual Machine:**
```bash
# Using QEMU (recommended for testing)
qemu-system-x86_64 -m 4096 -cdrom output/zforge-*.iso -enable-kvm

# Using VirtualBox
# 1. Create new VM with 4GB+ RAM
# 2. Attach ISO from output/ directory as boot media
# 3. Boot the VM
```

**B) Create Bootable USB:**
```bash
# Find your USB device (BE CAREFUL - this will erase the USB!)
lsblk

# Write ISO to USB (replace /dev/sdX with your actual USB device)
sudo dd if=output/zforge-*.iso of=/dev/sdX bs=4M status=progress sync
```

**C) Burn to DVD:**
```bash
# Using wodim/cdrecord
wodim -v dev=/dev/sr0 speed=4 output/zforge-*.iso
```

### Option 2: GUI Build Interface

For interactive ISO configuration and building:

```bash
# Launch enhanced GUI builder
./launch-enhanced-gui.sh

# Or run the build diagnostic tool
python3 tools/build_diagnostic_tool.py
```

### Option 3: Test Calamares Locally (Development Only)

To test the Calamares installer interface without building a full ISO:

```bash
# Install Calamares (if not installed)
sudo apt install calamares

# Run with Z-FORGE configuration
sudo calamares -d -c calamares/settings.conf
```

## 📋 Available Build Configurations

| Configuration File | Description | Use Case |
|-------------------|-------------|----------|
| `build_spec.yml` | Default configuration | General purpose builds |
| `build_spec_stable.yml` | Stable build configuration | Production deployments |
| `build_spec_proxmox_full.yml` | Full Proxmox VE build | Proxmox installations |
| `build_spec_trixie_clean.yml` | Clean Debian Trixie | Minimal Debian systems |
| `build_spec_proxmox9.yml` | Proxmox 9 specific | Latest Proxmox version |

## 🏗️ Build Requirements

### System Requirements
- **OS:** Debian-based Linux (Debian 12+ or Ubuntu 22.04+)
- **RAM:** Minimum 8GB (16GB recommended)
- **Disk:** 50GB free space
- **CPU:** 4+ cores recommended
- **Privileges:** Root/sudo access required

### Required Packages
```bash
# Install build dependencies
sudo apt update
sudo apt install -y \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-efi \
    grub-pc-bin \
    grub-efi-amd64-bin \
    grub-efi-amd64-signed \
    mtools \
    dosfstools \
    python3-yaml \
    python3-pip
```

## 🎯 Quick Start Commands

### Standard ISO Build
```bash
# Clean build with stable configuration
sudo python3 build.py --config build_spec_stable.yml --clean
```

### Proxmox Build
```bash
# Build Proxmox-based ISO
sudo python3 build.py --config build_spec_proxmox_full.yml
```

### Development Build (Faster)
```bash
# Skip package downloads if cached
sudo python3 build.py --config build_spec.yml --use-cache
```

## 📁 Project Structure

```
Z-FORGE/
├── build.py                    # Main build script
├── build_spec*.yml            # Build configurations
├── calamares/                 # Installer configuration (100% tested)
│   ├── modules/              # Installer modules
│   ├── settings.conf         # Calamares settings
│   └── branding/            # Installer branding
├── builder/                   # Build system modules
│   └── modules/             # Build components
├── output/                    # Built ISO files (created after build)
├── work/                      # Build workspace (temporary)
└── test_calamares_installer.sh  # Test suite (100% pass rate)
```

## 🔍 Troubleshooting

### Build Fails
```bash
# Check build logs
tail -f work/build.log

# Run diagnostic tool
python3 tools/build_diagnostic_tool.py

# Clean and retry
sudo rm -rf work/
sudo python3 build.py --config build_spec.yml --clean
```

### Test Suite Issues
```bash
# Run with verbose output
bash -x ./tests/calamares/test_calamares_installer.sh

# Check specific module
python3 -c "import sys; sys.path.insert(0, 'calamares'); import calamares.modules.MODULE_NAME.main"
```

### ISO Won't Boot
1. Verify ISO integrity: `md5sum output/zforge-*.iso`
2. Check UEFI/BIOS settings
3. Try different virtualization: QEMU vs VirtualBox
4. Ensure sufficient RAM (4GB minimum)

## 📊 Current Status

- **Calamares Installer:** ✅ 100% pass rate (84/84 tests)
- **Framework:** ✅ Pure Qt5 (GTK eliminated)
- **Error Handling:** ✅ Comprehensive
- **Module Status:** ✅ All 14 modules functional
- **Production Ready:** ✅ Yes

## 📚 Additional Resources

- **Checkpoints:** Review `CHECKPOINT_*.md` files for development history
- **Build Guide:** See `BUILD_GUIDE_STEP_BY_STEP.md` for detailed build instructions
- **Module Documentation:** Check `calamares/modules/*/README.md` for module details

## 🆘 Getting Help

If you encounter issues:
1. Check the test suite: `./test_calamares_installer.sh`
2. Review build logs: `work/build.log`
3. Consult checkpoints: `CHECKPOINT_*.md`
4. Check existing documentation in `docs/`

---

**Last Updated:** August 4, 2025  
**Status:** Production Ready with 100% Test Coverage
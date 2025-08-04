# Z-FORGE Build System - Complete Step-by-Step Guide

**Last Updated:** August 3, 2025  
**Status:** Build system fully operational

## Prerequisites

### System Requirements
- **OS:** Debian-based Linux (Ubuntu, Debian, etc.)
- **RAM:** Minimum 4GB (8GB recommended)
- **Disk Space:** 20GB free space
- **CPU:** x86_64 architecture
- **Privileges:** sudo access required

### Required Packages
```bash
# Install essential build tools
sudo apt update
sudo apt install -y \
    debootstrap \
    squashfs-tools \
    xorriso \
    grub-pc-bin \
    grub-efi-amd64-bin \
    python3 \
    python3-pip \
    python3-yaml \
    git \
    wget \
    curl
```

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/Z-FORGE.git
cd Z-FORGE

# Verify you're on the main branch
git branch
# Should show: * main

# Check the build system is ready
ls -la build.py builder/
```

## Step 2: Choose Your Build Configuration

Z-FORGE offers three main build configurations:

### Option A: Standard Build (Recommended for first build)
```bash
# Uses Debian Trixie with ZFS and full features
cat build_spec.yml
```

### Option B: Stable Build (Most reliable)
```bash
# Uses Debian Bookworm (stable) - simpler, no ZFS
cat build_spec_stable.yml
```

### Option C: Proxmox Build (Advanced)
```bash
# Includes Proxmox VE 9 integration
cat build_spec_proxmox_full.yml
```

## Step 3: Pre-Build Validation

```bash
# Run the build pipeline validator
python3 builder/modules/build_pipeline_validator.py

# Expected output:
# Overall Status: ALL_CHECKS_PASSED
# Total Checks: 81
# Passed: 81
# Failed: 0
```

## Step 4: Run the Build

### Basic Build Command
```bash
# Standard build (with ZFS)
sudo python3 build.py --spec build_spec.yml
```

### Alternative Builds
```bash
# Stable build (without ZFS, using Bookworm)
sudo python3 build.py --spec build_spec_stable.yml

# Proxmox build
sudo python3 build.py --spec build_spec_proxmox_full.yml
```

### Build with Options
```bash
# Verbose output
sudo python3 build.py --spec build_spec.yml --verbose

# Skip cleanup (keeps workspace for debugging)
sudo python3 build.py --spec build_spec.yml --skip-cleanup

# Custom workspace location
sudo python3 build.py --spec build_spec.yml --workspace /path/to/workspace
```

## Step 5: Monitor Build Progress

The build will go through these phases:

1. **Workspace Setup** (~1 min)
   ```
   [workspace_setup] Creating build workspace...
   [workspace_setup] ✓ Workspace ready
   ```

2. **Debootstrap** (~5-10 min)
   ```
   [debootstrap] Creating Debian base system...
   [debootstrap] Installing base packages...
   ```

3. **System Configuration** (~5 min)
   ```
   [gpg_bypass] Configuring APT...
   [kernel_acquisition] Installing kernel...
   ```

4. **Package Installation** (~10-15 min)
   ```
   [zfs_build] Installing ZFS packages...
   [live_environment] Setting up live boot...
   ```

5. **ISO Generation** (~5 min)
   ```
   [iso_generation] Creating bootable ISO...
   [iso_generation] ✓ ISO created: zforge-3.0-amd64.iso
   ```

**Total build time: ~30-45 minutes**

## Step 6: Handle Common Issues

### Issue 1: Permission Denied
```bash
# Make sure to use sudo
sudo python3 build.py --spec build_spec.yml
```

### Issue 2: Package Download Failures
```bash
# The system will retry automatically
# If persistent, check your internet connection
# Or try the stable build which uses Bookworm repos
```

### Issue 3: Workspace Already Exists
```bash
# Clean up previous build
rm -rf ~/zforge_workspace
# Or use --clean flag
sudo python3 build.py --spec build_spec.yml --clean
```

### Issue 4: Module Not Found
```bash
# This should not happen after our fixes, but if it does:
python3 scripts/test/check_all_module_naming.py
# All should show as correct
```

## Step 7: Verify Build Output

```bash
# Check ISO was created
ls -lh ~/zforge_workspace/iso/
# Should show: zforge-3.0-amd64.iso (or your configured name)

# Verify ISO size (should be 1-3GB)
du -h ~/zforge_workspace/iso/*.iso

# Check build log
cat ~/zforge_workspace/logs/build.log | tail -50
```

## Step 8: Test the ISO

### Option 1: Virtual Machine (Recommended)
```bash
# Using QEMU
qemu-system-x86_64 \
    -m 2048 \
    -cdrom ~/zforge_workspace/iso/zforge-3.0-amd64.iso \
    -boot d

# Using VirtualBox
# Create new VM, attach ISO as boot media
```

### Option 2: USB Boot
```bash
# Find your USB device (be careful!)
lsblk

# Write ISO to USB (replace sdX with your device)
sudo dd if=~/zforge_workspace/iso/zforge-3.0-amd64.iso of=/dev/sdX bs=4M status=progress
sync
```

## Step 9: Resume Failed Build

If a build fails, you can resume:

```bash
# Check where it failed
cat ~/zforge_workspace/build_progress.json

# Resume from last successful module
sudo python3 build.py --spec build_spec.yml --resume
```

## Step 10: Create Live Environment (Optional)

After successful ISO build:

```bash
# Create enhanced live environment
sudo ./scripts/build/build_live_environment.sh

# This adds:
# - Desktop environment (KDE/GNOME/XFCE)
# - Additional tools
# - User-friendly features
```

## Build Profiles Quick Reference

### Minimal Test Build
```bash
# Quick build for testing (no ZFS, minimal packages)
sudo python3 build.py --spec build_spec_stable.yml
```

### Full Featured Build
```bash
# Complete build with all features
sudo python3 build.py --spec build_spec.yml
```

### Proxmox Integration Build
```bash
# For Proxmox VE environments
sudo python3 build.py --spec build_spec_proxmox_full.yml
```

## Troubleshooting Commands

```bash
# Check system status
python3 scripts/test/check_all_issues.py

# Validate module naming
python3 scripts/test/check_all_module_naming.py

# Check build configuration
python3 scripts/test/test_config_loading.py build_spec.yml

# Clean everything and start fresh
rm -rf ~/zforge_workspace ~/zforge_cache
sudo python3 build.py --spec build_spec.yml --clean
```

## Expected Output

A successful build will show:
```
===========================================
 Z-FORGE BUILD COMPLETED SUCCESSFULLY! 
===========================================
ISO Location: /home/user/zforge_workspace/iso/zforge-3.0-amd64.iso
Build Duration: 35 minutes 42 seconds
Modules Executed: 16/16
Status: SUCCESS
```

## Next Steps

1. **Test the ISO** in a VM first
2. **Customize** by editing build_spec.yml
3. **Add packages** to the package lists
4. **Enable Calamares** installer for GUI installation
5. **Build variations** for different use cases

## Support

If you encounter issues:
1. Check the build log: `~/zforge_workspace/logs/build.log`
2. Run validation: `python3 scripts/test/check_all_issues.py`
3. Review this guide for common issues
4. Check the checkpoint files in `/checkpoint/` directory

Happy building! 🚀
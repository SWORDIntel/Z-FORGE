# Z-FORGE Fresh Build Guide

**Last Updated:** January 31, 2025  
**Status:** All scripts cleaned and in lockstep

## Prerequisites

### System Requirements
- Debian-based host system (Ubuntu, Debian, etc.)
- At least 20GB free disk space
- 4GB+ RAM recommended
- sudo access
- Internet connection

### Required Packages
```bash
# Install build dependencies
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    debootstrap \
    cdebootstrap \
    arch-install-scripts \
    git \
    python3 \
    python3-yaml \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-efi \
    grub-pc-bin \
    grub-efi-amd64-bin \
    mtools \
    dosfstools
```

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/Z-FORGE.git
cd Z-FORGE

# Set up workspace (avoids /tmp noexec issues)
./scripts/workspace/setup_no_tmp_build.sh
```

## Step 2: Bootstrap Chroot Environment

```bash
# Create fresh Debian Trixie chroot
sudo ./scripts/chroot/bootstrap_chroot.sh auto

# Verify bootstrap succeeded
ls -la ~/zforge_workspace/chroot/usr
# Should show directories with 755 permissions
```

## Step 3: Install ZFS in Chroot

### Option A: Complete Installation (Recommended)
```bash
# This installs ZFS and all dependencies
sudo ./scripts/chroot/complete_zfs_install.sh
```

### Option B: Manual Steps
```bash
# Enter chroot
sudo ./scripts/chroot/use_arch_chroot.sh

# Inside chroot, install ZFS
apt-get update
apt-get install -y zfsutils-linux

# Exit chroot
exit
```

## Step 4: Build ISO

### Using Makefile (Recommended)
```bash
# Build with HOME workspace
sudo make -f Makefile.no_tmp build
```

### Using Python Script
```bash
# Alternative method
sudo python3 build.py
```

### Build Output
- ISO location: `~/zforge_workspace/output/z-forge.iso`
- Build logs: `~/zforge_workspace/logs/`

## Step 5: Verify Build

```bash
# Check ISO was created
ls -lh ~/zforge_workspace/output/z-forge.iso

# Verify ISO contents (optional)
mkdir -p /tmp/iso_mount
sudo mount -o loop ~/zforge_workspace/output/z-forge.iso /tmp/iso_mount
ls -la /tmp/iso_mount/
sudo umount /tmp/iso_mount
```

## Common Issues and Solutions

### 1. Permission Denied
```bash
# Ensure scripts are executable
chmod +x scripts/**/*.sh
```

### 2. Bootstrap Fails
```bash
# Check internet connection
ping -c 3 deb.debian.org

# Try alternative bootstrap
sudo ./scripts/chroot/bootstrap_chroot.sh debootstrap
```

### 3. ZFS Installation Fails
```bash
# Verify chroot is ready
sudo ./scripts/chroot/use_arch_chroot.sh dpkg -l | grep -E "apt|dpkg"

# Fix apt sources
sudo ./scripts/fixes/fix_apt_sources_zfs.sh
```

### 4. Build Errors
```bash
# Check build prerequisites
./scripts/testing/pre-build-check.sh

# Clean workspace and retry
rm -rf ~/zforge_workspace
./scripts/workspace/setup_no_tmp_build.sh
```

## Quick Build Commands

### Minimal Build (Fast)
```bash
# Just the essentials
cd Z-FORGE
sudo ./scripts/chroot/bootstrap_chroot.sh auto
sudo ./scripts/chroot/complete_zfs_install.sh
sudo make -f Makefile.no_tmp build
```

### Full Build (Complete)
```bash
# With all checks and validations
cd Z-FORGE
./scripts/testing/pre-build-check.sh
./scripts/workspace/setup_no_tmp_build.sh
sudo ./scripts/chroot/bootstrap_chroot.sh auto
sudo ./scripts/chroot/complete_zfs_install.sh
./scripts/cleanup/verify_project_consistency.sh
sudo make -f Makefile.no_tmp build
```

## Build Time Estimates
- Bootstrap: ~3-5 minutes
- ZFS installation: ~2-3 minutes
- ISO build: ~10-15 minutes
- **Total**: ~15-25 minutes

## Post-Build Testing

### Test in Virtual Machine
```bash
# Using QEMU
qemu-system-x86_64 \
    -m 2048 \
    -cdrom ~/zforge_workspace/output/z-forge.iso \
    -boot d

# Using VirtualBox
# Create VM with 2GB RAM, attach ISO as CD-ROM
```

### Test on Physical Hardware
1. Write ISO to USB drive:
   ```bash
   sudo dd if=~/zforge_workspace/output/z-forge.iso of=/dev/sdX bs=4M status=progress
   ```
2. Boot from USB
3. Verify ZFS utilities available

## Advanced Options

### Custom Configuration
Edit `build_spec_no_tmp.yml` before building:
```yaml
workspace: ~/zforge_workspace
output_dir: ~/zforge_workspace/output
modules:
  - debootstrap
  - kernel_acquisition
  - zfs_build
  # Add more modules as needed
```

### Hardware-Specific Builds
```bash
# For Dell servers
cp config/r730xd/r730xd_build_spec.yml build_spec_no_tmp.yml
sudo make -f Makefile.no_tmp build

# For generic hardware
cp config/universal/universal_build_spec.yml build_spec_no_tmp.yml
sudo make -f Makefile.no_tmp build
```

## Cleanup

### Remove Build Artifacts
```bash
# Clean workspace but keep chroot
make -f Makefile.no_tmp clean

# Complete cleanup
rm -rf ~/zforge_workspace
```

### Reset to Fresh State
```bash
# Remove all generated files
git clean -fdx
git reset --hard HEAD
```

## Support

### Logs Location
- Build logs: `~/zforge_workspace/logs/`
- Bootstrap logs: `~/zforge_workspace/logs/bootstrap.log`
- Module logs: `~/zforge_workspace/logs/modules/`

### Getting Help
1. Check latest checkpoint: `checkpoint/CHECKPOINT_20250731_SCRIPT_CLEANUP.md`
2. Review documentation: `docs/README.md`
3. Run verification: `./scripts/cleanup/verify_project_consistency.sh`

## Summary

Building Z-FORGE from fresh is straightforward:
1. Clone repository
2. Set up workspace
3. Bootstrap chroot
4. Install ZFS
5. Build ISO

All scripts are now consistent and use HOME-based workspace paths, avoiding /tmp noexec issues. The build process has been tested and verified to work reliably.
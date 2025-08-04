# Z-FORGE Full Build Manual - Step by Step

**Last Updated:** August 3, 2025  
**Build System Status:** ✅ 100% Validated and Ready

## Table of Contents
1. [Pre-Build Checklist](#pre-build-checklist)
2. [System Preparation](#system-preparation)
3. [Build Execution](#build-execution)
4. [Build Monitoring](#build-monitoring)
5. [Post-Build Verification](#post-build-verification)
6. [Testing the ISO](#testing-the-iso)
7. [Troubleshooting](#troubleshooting)

---

## Pre-Build Checklist

### ✅ Check 1: System Requirements
```bash
# Check RAM (need 4GB minimum)
free -h

# Check disk space (need 20GB free)
df -h /

# Check CPU architecture
uname -m
# Should show: x86_64

# Check Linux distribution
lsb_release -a
# Should be Debian-based
```

### ✅ Check 2: Required Packages
```bash
# Update package list
sudo apt update

# Install all required packages
sudo apt install -y \
    debootstrap \
    squashfs-tools \
    xorriso \
    grub-pc-bin \
    grub-efi-amd64-bin \
    isolinux \
    syslinux-common \
    python3 \
    python3-pip \
    python3-yaml \
    git \
    wget \
    curl \
    dosfstools \
    mtools

# Verify installations
which debootstrap squashfs xorriso python3
```

### ✅ Check 3: Project Setup
```bash
# Navigate to project
cd /opt/github/Z-FORGE

# Check current branch
git branch
# Should show: * main

# Pull latest changes (optional)
git pull origin main

# Check build script exists
ls -la build.py
```

### ✅ Check 4: Run Validation
```bash
# Run the validator
python3 builder/modules/build_pipeline_validator.py

# Expected output:
# Validation Results: ALL_CHECKS_PASSED
# Checks: 88/88 passed
# Critical: 0, Errors: 0, Warnings: 0
```

---

## System Preparation

### Step 1: Clean Previous Builds (if any)
```bash
# Remove old workspace
rm -rf ~/zforge_workspace

# Remove old cache (optional, keeps downloads)
# rm -rf ~/zforge_cache

# Check no old mounts exist
mount | grep zforge
# Should return nothing
```

### Step 2: Check Network Connection
```bash
# Test Debian mirrors
curl -I http://deb.debian.org/debian/
# Should return: HTTP/1.1 200 OK

# Test DNS
ping -c 1 google.com
```

### Step 3: Configure Build Environment
```bash
# Set environment variables (optional)
export ZFORGE_CACHE_DIR="$HOME/zforge_cache"
export ZFORGE_LOG_LEVEL="INFO"

# Create cache directory if needed
mkdir -p "$ZFORGE_CACHE_DIR"
```

---

## Build Execution

### Option 1: Full Featured Build (Recommended)
```bash
# This builds with ZFS support and all features
sudo python3 build.py --spec build_spec.yml
```

### Option 2: Stable Build (Most Reliable)
```bash
# Uses Debian stable (Bookworm) - simpler, faster
sudo python3 build.py --spec build_spec_stable.yml
```

### Option 3: Verbose Build (For Debugging)
```bash
# Shows detailed output
sudo python3 build.py --spec build_spec.yml --verbose
```

### Option 4: Build with Custom Options
```bash
# Keep workspace after build
sudo python3 build.py --spec build_spec.yml --skip-cleanup

# Use custom workspace location
sudo python3 build.py --spec build_spec.yml --workspace /mnt/large-disk/workspace
```

---

## Build Monitoring

### During Build: What to Expect

The build progresses through these phases:

#### Phase 1: Workspace Setup (1-2 minutes)
```
[INFO] Executing module: workspace_setup
[workspace_setup] Creating workspace directory...
[workspace_setup] Setting up directory structure...
[workspace_setup] ✓ Workspace ready
```

#### Phase 2: Debootstrap (5-10 minutes)
```
[INFO] Executing module: debootstrap
[debootstrap] Creating base system for trixie...
I: Retrieving InRelease
I: Retrieving Packages
I: Validating Packages
I: Resolving dependencies...
I: Retrieving libacl1 2.3.1-3
[...many package downloads...]
I: Base system installed successfully
```

#### Phase 3: System Configuration (5-10 minutes)
```
[INFO] Executing module: gpg_bypass
[gpg_bypass] Configuring APT for build environment...

[INFO] Executing module: kernel_acquisition
[kernel_acquisition] Installing kernel 6.14.8-1...
[kernel_acquisition] Installing headers...
```

#### Phase 4: Feature Installation (10-15 minutes)
```
[INFO] Executing module: zfs_build
[zfs_build] Installing ZFS 2.3.3...
[zfs_build] Building kernel modules...

[INFO] Executing module: live_environment
[live_environment] Configuring live boot...
[live_environment] Creating user account...
```

#### Phase 5: ISO Creation (5 minutes)
```
[INFO] Executing module: iso_generation
[iso_generation] Creating squashfs filesystem...
[iso_generation] Generating ISO image...
[iso_generation] ✓ ISO created successfully
```

### Monitor in Another Terminal
```bash
# Watch the log file
tail -f ~/zforge_workspace/logs/build.log

# Check disk usage
watch df -h ~/zforge_workspace

# Monitor system resources
htop
```

---

## Post-Build Verification

### Step 1: Check Build Success
```bash
# Look for success message
# Should see:
# ===========================================
#  Z-FORGE BUILD COMPLETED SUCCESSFULLY! 
# ===========================================

# Check ISO was created
ls -lh ~/zforge_workspace/iso/
# Should show: zforge-3.0-amd64.iso (1-3GB size)

# Verify ISO integrity
file ~/zforge_workspace/iso/*.iso
# Should show: DOS/MBR boot sector; partition 2 : ID=0xef...
```

### Step 2: Check Build Artifacts
```bash
# Check complete log
less ~/zforge_workspace/logs/build.log

# Check module results
ls ~/zforge_workspace/logs/modules/

# Check lockfile (shows all completed steps)
cat ~/zforge_workspace/.build_lock
```

### Step 3: Calculate Checksums
```bash
# Generate checksums for ISO
cd ~/zforge_workspace/iso/
sha256sum *.iso > SHA256SUMS
md5sum *.iso > MD5SUMS

# Display checksums
cat SHA256SUMS
```

---

## Testing the ISO

### Option 1: Quick Test with QEMU
```bash
# Basic test (2GB RAM)
qemu-system-x86_64 \
    -m 2048 \
    -cdrom ~/zforge_workspace/iso/zforge-3.0-amd64.iso \
    -boot d

# With UEFI support
qemu-system-x86_64 \
    -m 2048 \
    -bios /usr/share/ovmf/OVMF.fd \
    -cdrom ~/zforge_workspace/iso/zforge-3.0-amd64.iso \
    -boot d

# With more features
qemu-system-x86_64 \
    -m 4096 \
    -smp 2 \
    -enable-kvm \
    -cdrom ~/zforge_workspace/iso/zforge-3.0-amd64.iso \
    -boot d
```

### Option 2: VirtualBox Testing
```bash
# Create VM
VBoxManage createvm --name "Z-FORGE-Test" --ostype "Debian_64" --register

# Configure VM
VBoxManage modifyvm "Z-FORGE-Test" \
    --memory 4096 \
    --cpus 2 \
    --boot1 dvd \
    --nic1 nat

# Attach ISO
VBoxManage storagectl "Z-FORGE-Test" --name "IDE" --add ide
VBoxManage storageattach "Z-FORGE-Test" \
    --storagectl "IDE" \
    --port 0 --device 0 \
    --type dvddrive \
    --medium ~/zforge_workspace/iso/zforge-3.0-amd64.iso

# Start VM
VBoxManage startvm "Z-FORGE-Test"
```

### Option 3: Create Bootable USB
```bash
# List USB devices (BE CAREFUL!)
lsblk
# Identify your USB device (e.g., /dev/sdb)

# Write ISO to USB (REPLACE sdX with your device)
sudo dd if=~/zforge_workspace/iso/zforge-3.0-amd64.iso \
    of=/dev/sdX \
    bs=4M \
    status=progress \
    oflag=sync

# Flush buffers
sync

# Verify
sudo fdisk -l /dev/sdX
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: "No space left on device"
```bash
# Check space
df -h ~/zforge_workspace

# Solution: Clean and use different location
rm -rf ~/zforge_workspace
sudo python3 build.py --spec build_spec.yml --workspace /mnt/larger-disk/workspace
```

#### Issue: "Package download failed"
```bash
# Solution 1: Retry (automatic)
# The build system retries 3 times

# Solution 2: Use stable build
sudo python3 build.py --spec build_spec_stable.yml

# Solution 3: Check network
ping -c 3 deb.debian.org
```

#### Issue: "Module not found"
```bash
# This shouldn't happen after our fixes, but:
python3 scripts/test/check_all_issues.py

# Verify all modules exist
ls builder/modules/*.py | wc -l
# Should be 50+ files
```

#### Issue: "Permission denied"
```bash
# Always use sudo for builds
sudo python3 build.py --spec build_spec.yml

# Check file permissions
ls -la build.py
# Should be readable
```

### Resume Failed Build
```bash
# Check last successful module
cat ~/zforge_workspace/build_progress.json | jq .

# Resume from failure point
sudo python3 build.py --spec build_spec.yml --resume

# Or start fresh
rm -rf ~/zforge_workspace
sudo python3 build.py --spec build_spec.yml
```

### Get Help
```bash
# Show build help
python3 build.py --help

# Check validation details
python3 scripts/test/show_validation_warnings.py

# Review build guide
less BUILD_GUIDE_STEP_BY_STEP.md
```

---

## Build Time Estimates

| Build Type | Time | Disk Space | Description |
|------------|------|------------|-------------|
| Stable | 20-30 min | 5-8 GB | Bookworm, no ZFS |
| Standard | 30-45 min | 8-12 GB | Trixie with ZFS |
| Proxmox | 40-60 min | 10-15 GB | Full Proxmox integration |

---

## Success Indicators

✅ **Build completed message appears**  
✅ **ISO file exists in ~/zforge_workspace/iso/**  
✅ **ISO size is 1-3 GB**  
✅ **No ERROR messages in log**  
✅ **All modules show success status**  

---

## Next Steps After Successful Build

1. **Test in VM** - Always test in virtual environment first
2. **Create USB** - For physical hardware testing
3. **Customize** - Edit build_spec.yml for your needs
4. **Document** - Record any customizations made
5. **Share** - Upload ISO to repository if needed

---

## Quick Reference Card

```bash
# Validate
python3 builder/modules/build_pipeline_validator.py

# Build (choose one)
sudo python3 build.py --spec build_spec_stable.yml    # Stable
sudo python3 build.py --spec build_spec.yml           # Standard
sudo python3 build.py --spec build_spec_proxmox_full.yml # Proxmox

# Check result
ls -lh ~/zforge_workspace/iso/

# Test
qemu-system-x86_64 -m 2048 -cdrom ~/zforge_workspace/iso/*.iso -boot d
```

---

**Remember:** The first build downloads many packages. Subsequent builds use the cache and are faster.

Good luck with your build! 🚀
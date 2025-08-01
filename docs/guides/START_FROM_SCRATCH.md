# Z-FORGE - Starting From Scratch Guide

This guide provides step-by-step instructions for setting up Z-FORGE from a clean system.

## Prerequisites

### System Requirements
- Debian-based Linux system (Debian 12+ or Ubuntu 22.04+)
- At least 20GB free disk space
- 4GB+ RAM recommended
- Internet connection
- sudo/root access

### Required Packages
```bash
# Install essential build tools
sudo apt update
sudo apt install -y \
    git \
    build-essential \
    debootstrap \
    python3 \
    python3-pip \
    python3-yaml \
    curl \
    wget \
    arch-install-scripts
```

## Step 1: Clone the Repository

```bash
# Create working directory
mkdir -p /opt/github
cd /opt/github

# Clone Z-FORGE
git clone https://github.com/[your-repo]/Z-FORGE.git
cd Z-FORGE
```

## Step 2: Set Up Directory Permissions

```bash
# Ensure proper ownership
sudo chown -R $USER:$USER /opt/github/Z-FORGE

# Set executable permissions on scripts
chmod +x scripts/**/*.sh
chmod +x scripts/**/*.py
chmod +x build.py
```

## Step 3: Create Workspace Structure

```bash
# Create HOME workspace (recommended)
mkdir -p ~/zforge_workspace/{chroot,cache,output,temp,logs}

# Alternative: Create /tmp workspace (if HOME not suitable)
# sudo mkdir -p /tmp/zforge_workspace/{chroot,cache,output,temp,logs}
```

## Step 4: Bootstrap the Chroot Environment

```bash
# Bootstrap Debian chroot (uses HOME workspace by default)
sudo ./scripts/chroot/bootstrap_chroot.sh auto

# Or specify custom location
# sudo ./scripts/chroot/bootstrap_chroot.sh auto ~/zforge_workspace/chroot
```

## Step 5: Install ZFS Support

### Option A: Complete Installation (Recommended)
```bash
# Run complete ZFS installation with all fixes
sudo ./scripts/chroot/complete_zfs_install.sh
```

### Option B: Manual Installation
```bash
# 1. Enter chroot
sudo ./scripts/chroot/use_arch_chroot.sh

# 2. Inside chroot, install ZFS manually
apt update
apt install -y zfsutils-linux zfs-dkms

# 3. Exit chroot
exit
```

### Option C: Install Pre-built Package
```bash
# If you have the pre-built ZFS package
sudo ./scripts/chroot/install_zfs_with_arch_chroot.sh
```

## Step 6: Configure Build Environment

### For Standard Build (using /tmp)
```bash
# Review build configuration
cat build_spec.yml

# Run standard build
sudo make build
```

### For Non-/tmp Build (Recommended)
```bash
# Review non-tmp build configuration
cat build_spec_no_tmp.yml

# Configure workspace
export ZFORGE_WORKSPACE="$HOME/zforge_workspace"

# Run non-tmp build
sudo make -f Makefile.no_tmp build
```

## Step 7: Build ISO

```bash
# Full build process
sudo python3 build.py

# Or use make
sudo make iso
```

## Common Issues and Solutions

### 1. Permission Denied Errors
```bash
# Fix ownership
sudo chown -R $USER:$USER /opt/github/Z-FORGE

# Fix script permissions
find scripts -name "*.sh" -exec chmod +x {} \;
```

### 2. Chroot Network Issues
```bash
# Fix DNS in chroot
sudo ./scripts/fixes/fix_chroot_network.sh
```

### 3. APT Repository Issues
```bash
# Fix APT sources
sudo ./scripts/fixes/fix_apt_sources_zfs.sh
```

### 4. Workspace noexec Issues
```bash
# Fix noexec on workspace
sudo ./scripts/workspace/fix_workspace_noexec.sh
```

### 5. Missing Dependencies
```bash
# Install additional dependencies
sudo apt install -y \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-utils \
    genisoimage
```

## Quick Start Commands

For the impatient, here's the absolute minimum to get started:

```bash
# 1. Clone
git clone https://github.com/[your-repo]/Z-FORGE.git /opt/github/Z-FORGE
cd /opt/github/Z-FORGE

# 2. Install dependencies
sudo apt update && sudo apt install -y git build-essential debootstrap python3 python3-pip python3-yaml arch-install-scripts

# 3. Make scripts executable
chmod +x scripts/**/*.sh

# 4. Bootstrap and install
sudo ./scripts/chroot/complete_zfs_install.sh

# 5. Build
sudo make -f Makefile.no_tmp build
```

## Verification Steps

### 1. Verify Chroot
```bash
# Check chroot exists
ls -la ~/zforge_workspace/chroot/

# Test chroot access
sudo ./scripts/chroot/use_arch_chroot.sh ls /
```

### 2. Verify ZFS Installation
```bash
# Check ZFS in chroot
sudo ./scripts/chroot/use_arch_chroot.sh which zfs
sudo ./scripts/chroot/use_arch_chroot.sh zfs version
```

### 3. Verify Build Environment
```bash
# Check Python modules
python3 -c "import yaml; print('YAML module OK')"

# Check build tools
which debootstrap
which mksquashfs
```

## Next Steps

Once the basic setup is complete:

1. **Review Documentation**
   - Read `docs/README.md` for project overview
   - Check `docs/build/BUILD_ENVIRONMENT_SETUP_GUIDE.md` for detailed build info
   - See `docs/hardware/SUPPORTED_HARDWARE.md` for hardware support

2. **Customize Build**
   - Edit `build_spec.yml` or `build_spec_no_tmp.yml`
   - Configure hardware-specific options in `config/`
   - Add custom modules in `builder/modules/`

3. **Test ISO**
   - Build ISO: `sudo make iso`
   - Test in VM first
   - Check `logs/` for build logs

4. **Hardware-Specific Setup**
   - For Dell servers: Check `config/r730xd/`, `config/t30/`, etc.
   - For Proxmox: See `docs/integration/PROXMOX_INTEGRATION.md`

## Troubleshooting

### Enable Debug Mode
```bash
# Debug build
sudo make debug

# Or
sudo python3 build.py --debug
```

### Check Logs
```bash
# Build logs
ls -la logs/

# Latest log
tail -f logs/zforge_build_*.log
```

### Get Help
- Check existing issues in checkpoint files
- Review scripts in `scripts/fixes/` for common solutions
- See `docs/reports/` for known issues and fixes

## Clean Start

If you need to start over:

```bash
# Clean build artifacts
sudo make clean

# Remove workspace (careful!)
sudo rm -rf ~/zforge_workspace

# Start fresh
sudo ./scripts/chroot/bootstrap_chroot.sh auto
```

---

Remember: The most reliable approach is using the HOME workspace with the complete installation script:

```bash
sudo ./scripts/chroot/complete_zfs_install.sh
```

This handles all the common issues automatically!
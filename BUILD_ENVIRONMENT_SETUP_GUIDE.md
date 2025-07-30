# Z-FORGE Build Environment Setup Guide
## Complete Step-by-Step Instructions

### Prerequisites
- Debian-based system (Ubuntu, Debian, etc.)
- At least 20GB free disk space
- 4GB+ RAM recommended
- sudo access

---

## Step 1: Install Build Dependencies

```bash
# Update package lists
sudo apt-get update

# Install essential build tools
sudo apt-get install -y \
    build-essential \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-common \
    grub-pc-bin \
    grub-efi-amd64-bin \
    mtools \
    dosfstools \
    git \
    python3 \
    python3-yaml \
    python3-pip \
    wget \
    curl

# Optional: Install cdebootstrap for faster builds
sudo apt-get install -y cdebootstrap
```

---

## Step 2: Clone or Prepare Z-FORGE Repository

```bash
# If not already cloned
cd /opt/github
git clone https://github.com/yourusername/Z-FORGE.git
cd Z-FORGE

# Or if already have it
cd /opt/github/Z-FORGE
```

---

## Step 3: Set Up No-/tmp Build Environment

```bash
# Make setup script executable
chmod +x setup_no_tmp_build.sh

# Run the setup (creates directories and sets environment)
./setup_no_tmp_build.sh

# This creates:
# - ~/zforge_workspace/
# - ~/zforge_workspace/chroot/
# - ~/zforge_workspace/cache/
# - ~/zforge_workspace/output/
# - ~/zforge_workspace/temp/
# - ~/zforge_workspace/logs/
```

---

## Step 4: Set Environment Variables

```bash
# Add to current session
export ZFORGE_WORKSPACE=$HOME/zforge_workspace
export TMPDIR=$HOME/zforge_workspace/temp
export TEMP=$HOME/zforge_workspace/temp
export TMP=$HOME/zforge_workspace/temp

# Make permanent (add to ~/.bashrc)
echo 'export ZFORGE_WORKSPACE=$HOME/zforge_workspace' >> ~/.bashrc
echo 'export TMPDIR=$HOME/zforge_workspace/temp' >> ~/.bashrc
echo 'export TEMP=$HOME/zforge_workspace/temp' >> ~/.bashrc
echo 'export TMP=$HOME/zforge_workspace/temp' >> ~/.bashrc

# Reload bashrc
source ~/.bashrc
```

---

## Step 5: Bootstrap the Chroot Environment

```bash
# Option A: Auto-detect best tool (recommended)
sudo ./bootstrap_chroot.sh auto

# Option B: Use specific tool
sudo ./bootstrap_chroot.sh debootstrap    # Standard tool
# OR
sudo ./bootstrap_chroot.sh cdebootstrap   # Faster alternative

# This installs a minimal Debian Trixie system with:
# - systemd
# - live-boot
# - live-config
# - Essential system packages
```

---

## Step 6: Add Proxmox Repository (Optional)

```bash
# Add Proxmox VE 9 repository to chroot
sudo ./add_proxmox_repo_to_chroot.sh

# This adds:
# - Proxmox repository configuration
# - GPG signing keys
# - Access to Proxmox packages
```

---

## Step 7: Install ZFS Package

We have a pre-built ZFS userspace package ready:

```bash
# Install our custom ZFS package
sudo ./install_our_zfs_package.sh

# Or manually:
sudo cp live_cd_packages/zfsutils-userspace_2.3.3-1_amd64.deb \
    $HOME/zforge_workspace/chroot/tmp/
sudo chroot $HOME/zforge_workspace/chroot \
    dpkg -i /tmp/zfsutils-userspace_2.3.3-1_amd64.deb
```

---

## Step 8: Verify Build Environment

```bash
# Check workspace
ls -la $ZFORGE_WORKSPACE

# Check chroot
sudo chroot $ZFORGE_WORKSPACE/chroot /bin/bash -c "
    echo 'Checking environment...'
    which debootstrap
    which zfs
    apt list --installed | grep -E 'systemd|live-boot' | head -5
    exit
"

# Check environment variables
env | grep -E "ZFORGE|TMP"
```

---

## Step 9: Run the Build

```bash
# Use the no-/tmp Makefile
make -f Makefile.no_tmp build

# Or if you fixed the original system
make build
```

---

## Troubleshooting

### If chroot already exists in /tmp
```bash
# Unmount any mounted filesystems
sudo umount -l /tmp/zforge_workspace/*/proc
sudo umount -l /tmp/zforge_workspace/*/sys
sudo umount -l /tmp/zforge_workspace/*/dev/pts
sudo umount -l /tmp/zforge_workspace/*/dev

# Move to new location
sudo mv /tmp/zforge_workspace $HOME/
```

### If build fails with permission errors
```bash
# Ensure workspace is writable
sudo chown -R $USER:$USER $ZFORGE_WORKSPACE

# Except chroot (needs root)
sudo chown -R root:root $ZFORGE_WORKSPACE/chroot
```

### If packages fail to install
```bash
# Update chroot repositories
sudo chroot $ZFORGE_WORKSPACE/chroot apt-get update

# Fix any broken packages
sudo chroot $ZFORGE_WORKSPACE/chroot apt-get install -f
```

---

## Complete Quick Setup (Copy & Paste)

```bash
# All commands in sequence
cd /opt/github/Z-FORGE

# Install dependencies
sudo apt-get update
sudo apt-get install -y build-essential debootstrap squashfs-tools \
    xorriso isolinux syslinux-common grub-pc-bin grub-efi-amd64-bin \
    mtools dosfstools git python3 python3-yaml wget

# Setup environment
export ZFORGE_WORKSPACE=$HOME/zforge_workspace
export TMPDIR=$HOME/zforge_workspace/temp
export TEMP=$HOME/zforge_workspace/temp
export TMP=$HOME/zforge_workspace/temp

# Create workspace
mkdir -p $ZFORGE_WORKSPACE/{chroot,cache,output,temp,logs}

# Bootstrap chroot
sudo ./bootstrap_chroot.sh auto

# Add Proxmox repo (optional)
sudo ./add_proxmox_repo_to_chroot.sh

# Install ZFS package
sudo ./install_our_zfs_package.sh

# Run build
make -f Makefile.no_tmp build
```

---

## Expected Results

After successful setup:
- ✅ Workspace at `~/zforge_workspace/`
- ✅ Chroot with Debian Trixie
- ✅ ZFS tools installed
- ✅ Proxmox repository available
- ✅ Build system ready
- ✅ No `/tmp` dependencies

The build will create:
- ISO image in `~/zforge_workspace/output/`
- Build logs in `~/zforge_workspace/logs/`
- Cached packages in `~/zforge_workspace/cache/`
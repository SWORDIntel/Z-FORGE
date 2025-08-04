# Z-FORGE Environment Bootstrap - Step by Step

**Date:** August 3, 2025  
**Purpose:** Complete environment setup from scratch

## Overview
We'll bootstrap the environment step by step, verifying each stage before proceeding.

## Step 1: System Information Gathering

Let's first understand your current environment.

### 1.1 Check System Details
```bash
# Check OS version
cat /etc/os-release

# Check kernel version
uname -r

# Check architecture
uname -m

# Check available disk space
df -h

# Check available memory
free -h

# Check current user
whoami

# Check sudo access
sudo -v
```

### 1.2 Check Current Directory
```bash
# Where are we?
pwd

# Is this a git repository?
git status

# List current files
ls -la
```

## Step 2: Basic Package Requirements

### 2.1 Update Package Lists
```bash
# Update apt cache
sudo apt update
```

### 2.2 Install Essential Build Tools
```bash
# Core tools needed for any build
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    python3 \
    python3-pip
```

### 2.3 Install Python Requirements
```bash
# Python YAML support (required for build configs)
sudo apt install -y python3-yaml

# Check Python version
python3 --version
```

## Step 3: Z-FORGE Specific Requirements

### 3.1 Install Debian Bootstrap Tools
```bash
# Debootstrap - creates Debian base systems
sudo apt install -y debootstrap

# Verify installation
debootstrap --version
```

### 3.2 Install ISO Creation Tools
```bash
# Tools for creating bootable ISOs
sudo apt install -y \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-common

# Verify installations
which mksquashfs xorriso
```

### 3.3 Install Bootloader Tools
```bash
# GRUB for both BIOS and UEFI
sudo apt install -y \
    grub-pc-bin \
    grub-efi-amd64-bin \
    grub-efi-amd64-signed \
    efibootmgr

# Additional filesystem tools
sudo apt install -y \
    dosfstools \
    mtools
```

## Step 4: Verify Z-FORGE Installation

### 4.1 Check Project Structure
```bash
# Navigate to Z-FORGE directory
cd /opt/github/Z-FORGE

# Verify critical files exist
ls -la build.py
ls -la builder/
ls -la builder/modules/
ls -la build_spec*.yml
```

### 4.2 Test Python Imports
```bash
# Test if we can import the builder
python3 -c "import sys; sys.path.append('.'); from builder.core.builder import ZForgeBuilder; print('✅ Builder imports successfully')"
```

### 4.3 Check Module Count
```bash
# Count available modules
ls builder/modules/*.py | wc -l
# Should be 50+ files
```

## Step 5: Environment Validation

### 5.1 Run Basic Validation
```bash
# Simple file check
python3 -c "
from pathlib import Path
required_files = [
    'build.py',
    'builder/core/builder.py',
    'builder/core/config.py',
    'build_spec.yml'
]
missing = []
for f in required_files:
    if not Path(f).exists():
        missing.append(f)
        
if missing:
    print('❌ Missing files:', missing)
else:
    print('✅ All required files present')
"
```

### 5.2 Run Module Validation
```bash
# Check module naming
python3 scripts/test/check_all_module_naming.py | tail -10
```

### 5.3 Run Full Validation
```bash
# Complete validation
python3 builder/modules/build_pipeline_validator.py
```

## Step 6: Prepare for First Build

### 6.1 Create Workspace Directory
```bash
# Default workspace location
mkdir -p ~/zforge_workspace
mkdir -p ~/zforge_cache
```

### 6.2 Check Network Connectivity
```bash
# Test Debian mirror access
curl -I http://deb.debian.org/debian/

# Test DNS resolution
host deb.debian.org
```

### 6.3 Review Build Configurations
```bash
# List available build specs
ls -la build_spec*.yml

# View stable build config (recommended for first build)
less build_spec_stable.yml
```

## Ready to Build?

Once all steps above complete successfully, you're ready to start your first build!

### Choose Your Build:
1. **Stable Build** (Recommended for first time)
   ```bash
   sudo python3 build.py --spec build_spec_stable.yml
   ```

2. **Standard Build** (With ZFS support)
   ```bash
   sudo python3 build.py --spec build_spec.yml
   ```

## Verification Checklist

Before building, ensure:
- [ ] All apt packages installed successfully
- [ ] Python 3 is working
- [ ] debootstrap is installed
- [ ] ISO tools are installed  
- [ ] Z-FORGE files are present
- [ ] Validation shows 88/88 passed
- [ ] Network connectivity works
- [ ] At least 20GB free disk space
- [ ] At least 4GB RAM available

## Troubleshooting

If any step fails:
1. Note the exact error message
2. Check system logs: `sudo journalctl -xe`
3. Verify internet connectivity
4. Ensure you have sudo access
5. Check disk space isn't full
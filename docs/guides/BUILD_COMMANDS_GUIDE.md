# Z-FORGE Step-by-Step Build Commands

## Prerequisites

Before starting, ensure you have:
- Debian/Ubuntu host system
- sudo access
- At least 50GB free disk space
- Internet connection

### Install Required Tools
```bash
sudo apt-get update
sudo apt-get install -y \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-utils \
    python3 \
    python3-yaml \
    git \
    wget \
    build-essential
```

## Step 1: Clone and Setup

```bash
# Clone the repository (if not already done)
cd /opt/github
git clone <repository-url> Z-FORGE
cd Z-FORGE

# Verify configuration is correct
python3 scripts/test/test_config_loading.py
```

## Step 2: Build ZFS Packages (if needed)

```bash
# Option A: Use prebuilt packages (faster)
cd prebuilt_packages
./install_proxmox_zfs.sh

# Option B: Build from source (recommended for customization)
cd scripts/build
sudo ./build_zfs_from_proxmox_source.sh
```

## Step 3: Run Pipeline Validation

```bash
# Validate the entire build pipeline
python3 scripts/test/test_build_pipeline.py

# Should show: "Overall Status: ALL_CHECKS_PASSED"
# If not, fix any reported issues before proceeding
```

## Step 4: Main ISO Build

### Option A: Standard Build
```bash
# Run the main build with default configuration
sudo python3 build.py --spec build_spec.yml

# Or with specific target
sudo python3 build.py --spec build_spec.yml --target production
```

### Option B: Proxmox Full Build
```bash
# For complete Proxmox integration
sudo python3 build.py --spec build_spec_proxmox_full.yml
```

### Option C: No-Temp Build
```bash
# To avoid using /tmp
sudo python3 build.py --spec build_spec_no_tmp.yml
```

## Step 5: Build Live Environment with GUI

After the base ISO is built, create the live environment:

```bash
# Build live environment with desktop and Calamares GUI
sudo ./scripts/build/build_live_environment.sh

# This will:
# - Install desktop environment
# - Configure Calamares GUI installer
# - Create bootable live ISO
# - Test GUI connectivity
```

## Step 6: Verify Build

```bash
# Test GUI connectivity
python3 scripts/test/test_gui_connectivity.py

# Check ISO was created
ls -lh ~/zforge_workspace/output/*.iso
```

## Build Process Details

The build will execute these modules in order:

1. **workspace_setup** - Creates build directories
2. **gpg_bypass** - Handles GPG verification
3. **universal_hardware_detect** - Detects hardware
4. **debootstrap** - Creates base Debian system
5. **kernel_acquisition** - Installs kernel
6. **zfs_build** - Installs ZFS support
7. **proxmox_integration** - Adds Proxmox packages
8. **live_environment** - Configures live boot
9. **dracut_config** - Configures initramfs
10. **zfsbootmenu_install** - Installs ZFS boot menu
11. **bootloader_setup** - Configures bootloader
12. **security_hardening** - Applies security settings
13. **zfs_encryption** - Configures ZFS encryption
14. **calamares_integration** - Installs GUI installer
15. **cleanup_handler** - Cleans temporary files
16. **iso_generation** - Creates final ISO

## Common Build Options

### Debug Build
```bash
# Enable debug output
sudo python3 build.py --spec build_spec.yml --debug
```

### Resume Failed Build
```bash
# Resume from last successful module
sudo python3 build.py --spec build_spec.yml --resume
```

### Custom Workspace
```bash
# Use different workspace location
export WORKSPACE=/path/to/custom/workspace
sudo python3 build.py --spec build_spec.yml
```

### Parallel Builds
```bash
# Run multiple builds (different specs)
sudo python3 build.py --spec build_spec.yml &
sudo python3 build.py --spec build_spec_proxmox_full.yml &
```

## Troubleshooting

### If Build Fails

1. Check the logs:
```bash
# View recent logs
tail -f ~/zforge_workspace/logs/build_*.log

# Check specific module logs
less ~/zforge_workspace/logs/modules/<module_name>_*.log
```

2. Run validation:
```bash
python3 scripts/test/test_build_pipeline.py
```

3. Clean and retry:
```bash
# Clean workspace
rm -rf ~/zforge_workspace/*

# Retry build
sudo python3 build.py --spec build_spec.yml
```

### Common Issues

**Module not found error:**
```bash
# Verify module names
python3 scripts/test/check_module_names.py
```

**Permission denied:**
```bash
# Ensure running with sudo
sudo python3 build.py --spec build_spec.yml
```

**Out of space:**
```bash
# Check disk space
df -h ~/zforge_workspace

# Clean old builds
rm -rf ~/zforge_workspace/chroot
rm -rf ~/zforge_workspace/output/*.iso
```

## Quick Test Build

For a quick test build with minimal features:

```bash
# Create test configuration
cat > build_spec_test.yml << EOF
builder_config:
  debian_release: trixie
  kernel_version: 6.14.8-1
  output_iso_name: zforge-test.iso
  workspace_path: \${HOME}/zforge_workspace
  iso_version: '3.0-test'

modules:
- name: workspace_setup
  enabled: true
- name: debootstrap
  enabled: true
- name: kernel_acquisition
  enabled: true
- name: live_environment
  enabled: true
- name: iso_generation
  enabled: true

name: Z-FORGE-TEST
version: '3.0'
codename: test
architecture: amd64
EOF

# Run test build
sudo python3 build.py --spec build_spec_test.yml
```

## Final Output

After successful build, you'll have:

1. **Base ISO**: `~/zforge_workspace/output/zforge-3.0-amd64.iso`
2. **Live ISO**: `~/zforge_workspace/output/zforge-live-minimal.iso`

Both ISOs will be bootable and include:
- ZFS support
- Proxmox integration (if selected)
- Calamares GUI installer
- Live desktop environment

## Verification

Boot the ISO in a VM or physical machine to verify:
- Live environment boots correctly
- Desktop environment loads
- Calamares installer launches
- ZFS options are available
- Installation completes successfully
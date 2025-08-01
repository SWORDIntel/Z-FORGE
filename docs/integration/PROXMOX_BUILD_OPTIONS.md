# Proxmox VE Build Options for Z-FORGE

Z-FORGE now supports three different methods for integrating Proxmox VE:

## 1. APT Repository Method (Default)

This is the standard and recommended approach for most users.

```yaml
proxmox_config:
  build_from_source: false
  use_beta_iso: false
```

**Advantages:**
- Fast and reliable
- Well-tested packages
- Automatic dependency resolution
- Regular security updates

**Disadvantages:**
- Limited to officially released versions
- No customization of Proxmox components

## 2. Build from Source

Build Proxmox VE directly from their Git repositories.

```yaml
proxmox_config:
  build_from_source: true
  use_beta_iso: false
```

**Advantages:**
- Latest development features
- Full customization possible
- Can apply custom patches
- Learn Proxmox internals

**Disadvantages:**
- Significantly longer build time
- Requires more RAM (26GB+ recommended)
- May encounter build failures
- Less stable than release versions

**Requirements:**
- 26GB+ RAM
- 50GB+ free disk space
- Good internet connection
- Build dependencies installed

## 3. Extract from Beta ISO

Use the Proxmox VE 9.0 BETA ISO as a base.

```yaml
proxmox_config:
  build_from_source: false
  use_beta_iso: true
```

**Advantages:**
- Access to beta features
- Pre-built and tested packages
- Faster than building from source
- Includes Proxmox's default configurations

**Disadvantages:**
- Beta software may have bugs
- Large ISO download (700MB+)
- May not be compatible with all systems

## Switching Between Methods

To change the Proxmox integration method:

1. Edit `build_spec.yml` or create a custom spec file
2. Set the appropriate option to `true` (only one at a time)
3. Clean the workspace: `./cleanup-workspace.sh`
4. Rebuild: `./build-iso.sh`

## Custom Package Selection

Regardless of the method chosen, you can customize which Proxmox packages to include:

```yaml
proxmox_config:
  include_packages:
    - proxmox-ve          # Core Proxmox VE metapackage
    - pve-kernel-6.8      # Proxmox kernel
    - pve-manager         # Web management interface
    - pve-cluster         # Cluster functionality
    - pve-ha-manager      # High availability
    - pve-firewall        # Firewall management
    - pve-container       # LXC container support
    - pve-qemu-kvm        # KVM virtualization
    - proxmox-backup      # Backup functionality
```

## Troubleshooting

### Build from Source Issues

If building from source fails:

1. Check available RAM: `free -h`
2. Check disk space: `df -h`
3. Verify internet connectivity
4. Check build logs in `/tmp/zforge_workspace/logs/`

### Beta ISO Issues

If using the beta ISO fails:

1. Verify ISO download completed: Check file size
2. Ensure mount permissions: Run as root/sudo
3. Check ISO integrity with checksums

### APT Repository Issues

If APT method fails:

1. Check network connectivity
2. Verify Proxmox GPG keys are imported
3. Try different Debian mirror
4. Check if Proxmox repos are accessible

## Performance Recommendations

- **APT Method**: 8GB RAM, 20GB disk
- **Source Build**: 26GB RAM, 50GB disk
- **Beta ISO**: 12GB RAM, 30GB disk

For production use, the APT repository method is recommended unless you have specific requirements for newer features or customizations.
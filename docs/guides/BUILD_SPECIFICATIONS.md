# Z-FORGE Build Specifications Guide

## Available Build Configurations

Z-FORGE provides 6 validated build specifications, each optimized for different use cases:

### 1. `build_spec.yml` - Full Featured Build
**Use Case:** Complete ZFS-enabled Linux distribution with all features
```yaml
name: Z-FORGE Full Build
version: 3.0
features:
  - ZFS 2.3.3+ with all features
  - Proxmox integration
  - Hardware optimization
  - Complete bootloader suite
  - Enterprise security features
```

**Build Command:**
```bash
sudo python3 build.py --spec build_spec.yml
```

### 2. `build_spec_stable.yml` - Debian Bookworm Stable
**Use Case:** Conservative build using stable packages
```yaml
name: Z-FORGE Stable
version: 3.0
base: Debian Bookworm (stable)
features:
  - Stable package versions
  - Conservative kernel
  - Proven hardware support
  - Long-term support focus
```

**Build Command:**
```bash
sudo python3 build.py --spec build_spec_stable.yml
```

### 3. `build_spec_proxmox9.yml` - Proxmox VE 9 Integration
**Use Case:** Specialized build for Proxmox VE 9 environments
```yaml
name: Z-FORGE Proxmox 9
version: 3.0
features:
  - Proxmox VE 9.0-beta integration
  - Enterprise storage features
  - Cluster management tools
  - Advanced networking
```

**Build Command:**
```bash
sudo python3 build.py --spec build_spec_proxmox9.yml
```

### 4. `build_spec_proxmox_full.yml` - Complete Proxmox Build
**Use Case:** Full Proxmox integration with all enterprise features
```yaml
name: Z-FORGE Proxmox Full
version: 3.0
features:
  - Complete Proxmox suite
  - ZFS enterprise features
  - High availability support
  - Management interfaces
```

**Build Command:**
```bash
sudo python3 build.py --spec build_spec_proxmox_full.yml
```

### 5. `build_spec_no_tmp.yml` - No /tmp Build
**Use Case:** Builds avoiding /tmp directory (recommended for most systems)
```yaml
name: Z-FORGE No Tmp
version: 3.0
features:
  - HOME workspace builds
  - Avoids /tmp noexec issues
  - Better permission handling
  - Workspace isolation
```

**Build Command:**
```bash
sudo python3 build.py --spec build_spec_no_tmp.yml
```

### 6. `build_spec_outside_packages.yml` - Maximum Outside Build
**Use Case:** Fastest builds using prebuilt packages
```yaml
name: Z-FORGE Outside Packages Build
version: 3.0
features:
  - Prebuilt package installation
  - Minimal chroot operations
  - Fastest build times
  - Maximum reliability
```

**Build Command:**
```bash
sudo python3 build.py --spec build_spec_outside_packages.yml
```

## Build Specification Structure

### Required Fields
Every build specification must include:
```yaml
name: "Build Name"           # Human-readable name
version: "X.Y"              # Version number
builder_config: {...}       # Core build settings
modules: [...]              # Build modules list
```

### Common Configuration Sections

#### Builder Configuration
```yaml
builder_config:
  debian_release: trixie|bookworm
  kernel_version: "6.14.x"
  output_iso_name: "custom-name.iso"
  enable_debug: true|false
  workspace_path: "${HOME}/workspace"
  auto_detect_hardware: true|false
```

#### ZFS Configuration
```yaml
zfs_config:
  version: "2.3.3"
  build_from_source: true|false
  enable_encryption: true|false
  compression:
    default: lz4|zstd|gzip
    algorithm: auto|manual
  features:
    - raid_z_expansion
    - block_cloning
    - improved_performance
```

#### Proxmox Configuration
```yaml
proxmox_config:
  version: "9.0-beta"
  minimal_install: true|false
  build_from_source: true|false
  install_method: source|prebuilt_packages
```

#### Hardware Detection
```yaml
hardware_detection:
  enabled: true|false
  enforce_zfs_mode: true|false
  gpu_passthrough: true|false
  raid_optimization: true|false
```

## Module System

### Available Modules

#### Core Modules
- `workspace_setup` - Workspace preparation
- `debootstrap` - Base system installation
- `kernel_acquisition` - Kernel and modules
- `zfs_build` - ZFS compilation and installation
- `live_environment` - Live system configuration

#### Integration Modules
- `proxmox_integration` - Proxmox VE integration
- `calamares_integration` - Installer configuration
- `hardware_optimization` - Hardware-specific tuning
- `security_hardening` - Security enhancements

#### Utility Modules
- `gpg_bypass` - Package verification bypass
- `cleanup_handler` - Build cleanup
- `iso_generation` - Final ISO creation

### Module Configuration
```yaml
modules:
- name: module_name
  enabled: true|false
  config:
    parameter1: value1
    parameter2: value2
```

## Custom Build Specifications

### Creating Custom Specs

1. Copy an existing specification:
```bash
cp build_spec_stable.yml build_spec_custom.yml
```

2. Modify required fields:
```yaml
name: "My Custom Build"
version: "1.0"
```

3. Adjust configuration for your needs
4. Validate the specification:
```bash
python3 builder/modules/build_pipeline_validator.py --spec build_spec_custom.yml
```

### Best Practices

#### Naming Convention
- Use descriptive names: `build_spec_server.yml`
- Include version numbers
- Document purpose in comments

#### Configuration Guidelines
- Start with a working specification
- Change one section at a time
- Test each modification
- Keep backups of working configs

#### Validation
- Always validate after changes
- Check for required fields
- Verify module dependencies
- Test build process

## Troubleshooting Build Specs

### Common Issues

#### Missing Required Fields
```bash
# Error: Build spec missing sections: ['name', 'version']
# Fix: Add required metadata
name: "Your Build Name"
version: "1.0"
```

#### Module Dependencies
```bash
# Error: Module 'X' requires module 'Y'
# Fix: Add required module to modules list
modules:
- name: required_module
  enabled: true
- name: dependent_module
  enabled: true
```

#### Invalid Configuration
```bash
# Error: Invalid configuration value
# Fix: Check allowed values in documentation
zfs_config:
  compression:
    default: lz4  # Valid: lz4, zstd, gzip
```

### Debugging

#### Validation Output
```bash
# Show detailed validation results
python3 scripts/test/show_validation_warnings.py

# Check specific build spec
python3 builder/modules/build_pipeline_validator.py --spec your_spec.yml --verbose
```

#### Build Logs
```bash
# Monitor build process
sudo python3 build.py --spec your_spec.yml --debug

# Check logs
tail -f /var/log/zforge/build.log
```

## Performance Optimization

### Build Speed Recommendations

1. **Fastest**: `build_spec_outside_packages.yml` - Uses prebuilt packages
2. **Balanced**: `build_spec_no_tmp.yml` - Good speed and features
3. **Complete**: `build_spec.yml` - All features, slower build

### Resource Usage

#### Disk Space Requirements
- Minimal build: 10GB
- Full build: 20GB
- With debug: 30GB

#### Memory Requirements
- Minimum: 4GB RAM
- Recommended: 8GB RAM
- With parallel builds: 16GB RAM

#### CPU Usage
- Single-threaded modules: Use `-j1`
- Multi-threaded safe: Use `-j$(nproc)`
- Mixed workloads: Use `-j4`

All build specifications are validated and production-ready with 100% validation coverage.
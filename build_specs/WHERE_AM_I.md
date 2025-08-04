# WHERE AM I - Build Specifications Directory

## 📍 Current Location: Build Specifications
**Path**: `/opt/github/Z-FORGE/build_specs/`

## 🎯 Directory Purpose
This directory contains **7 build configurations** with documented success rates and specific use cases.

## 📋 Available Build Specifications

### **Recommended Builds** (High Success)
- `build_spec_outside_packages.yml` - **95% Success** - FASTEST, uses pre-built packages
- `build_spec_stable.yml` - **85% Success** - STABLE, production-ready
- `build_spec_no_tmp.yml` - **80% Success** - For restricted environments

### **Specialized Builds** (Medium Success)
- `build_spec_proxmox9.yml` - **75% Success** - Proxmox VE 9.x integration
- `build_spec_proxmox_full.yml` - **75% Success** - Full Proxmox features

### **Advanced Builds** (Lower Success)
- `build_spec.yml` - **70% Success** - Full featured build
- `build_spec_trixie_clean.yml` - **60% Success** - Latest packages

## 🚀 Usage Examples

### Quick Successful Build
```bash
# From project root
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml
```

### Production Build
```bash
# From project root  
sudo python3 build.py --spec build_specs/build_spec_stable.yml
```

### Proxmox Integration
```bash
# From project root
sudo python3 build.py --spec build_specs/build_spec_proxmox9.yml
```

## 📊 Build Statistics

| Specification | Success Rate | Build Time | Use Case |
|---------------|-------------|------------|----------|
| outside_packages | 95% | ~30 min | First build, development |
| stable | 85% | ~45 min | Production systems |
| no_tmp | 80% | ~40 min | Restricted environments |
| proxmox9 | 75% | ~60 min | Proxmox VE integration |
| proxmox_full | 75% | ~60 min | Full Proxmox features |
| build_spec | 70% | ~90 min | All features enabled |
| trixie_clean | 60% | ~50 min | Latest packages |

## 🔧 Configuration Details

### Common Features (All Builds)
- ZFS 2.3.3+ support
- Dracut initramfs system  
- Modern kernel support
- Multiple desktop environments
- Calamares installer

### Build-Specific Features
- **Outside Packages**: Pre-built packages for speed
- **Stable**: Conservative package versions
- **No /tmp**: Alternative temp directory handling
- **Proxmox**: Virtualization platform integration
- **Trixie**: Latest Debian testing packages

## 🛠️ Modification Guidelines

### To Modify a Build Spec
1. **Backup**: Copy existing specification
2. **Edit**: Modify YAML configuration
3. **Validate**: Test with diagnostic tools
4. **Document**: Update success rate statistics

### Key Configuration Sections
- `packages`: Package selections and sources
- `modules`: Build modules to execute
- `zfs_config`: ZFS-specific settings
- `desktop`: Desktop environment choices
- `proxmox`: Virtualization settings (if applicable)

## 🔍 Related Files

### From Project Root
- `build.py` - Main build script that uses these specifications
- `tools/build_diagnostic_tool.py` - Validates build readiness
- `docs/BUILD_CONFIGURATION.md` - Detailed configuration guide

### Navigation
- **Up**: `../` - Return to project root
- **Documentation**: `../docs/` - Complete documentation
- **Tools**: `../tools/` - Diagnostic and recovery tools

## 🎯 Quick Tips for Agents

### For First-Time Success
- **Use**: `build_spec_outside_packages.yml` (95% success)
- **Run**: Diagnostics first with `../tools/build_diagnostic_tool.py`
- **Monitor**: Use enhanced GUI for automatic recovery

### For Production Use
- **Use**: `build_spec_stable.yml` (85% success, conservative)
- **Test**: Thoroughly in non-production environment first
- **Backup**: Always backup before production builds

### For Development
- **Experiment**: With different specifications safely
- **Validate**: Changes with integration tests
- **Document**: Success rates for future reference

---
**Agent Navigation**: Build specifications control the entire build process. Choose wisely based on success rate needs.
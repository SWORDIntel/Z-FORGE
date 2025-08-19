# Scripts Directory Index

This directory contains organized utility scripts for Z-FORGE operations.

## 📁 Directory Structure

### 🎨 GUI Scripts
- **[legacy-gui/](legacy-gui/)** - Non-enhanced GUI scripts
  - `zforge_gui.py` - Standard GUI (non-enhanced version)

### 🚀 Bootstrap Scripts  
- **[bootstrap/](bootstrap/)** - System bootstrap and initialization
  - `bootstrap_fixed.sh` - Fixed bootstrap implementation
  - `bootstrap_incremental.sh` - Incremental bootstrap approach
  - `bootstrap_progressive.sh` - Progressive bootstrap system

### 🚀 Deployment Scripts
- **[deployment/](deployment/)** - Server deployment and distribution
  - `zfs-stream-deploy.sh` - ZFS streaming deployment (10-100x faster)
  - `deploy-to-servers.sh` - Mass server deployment orchestration

### 🧪 Testing Scripts
- **[testing/](testing/)** - Testing and validation utilities
  - `test_ultrathink_chroot.sh` - Chroot environment testing
  - `check_layer_success.sh` - Build layer validation

### 🔧 Core Scripts
- `build-all-versions.sh` - Comprehensive build system with monitoring
- `ultrathink_chroot_solution.py` - Advanced chroot handling
- `integrate_ultrathink_chroot.py` - Chroot integration utilities

## 🎯 UltraThink Agents

The main UltraThink agents remain in **[agents/](../scripts/agents/)**:
- `ultrathink_build_fixer.py` - Automatic build failure recovery
- `ultrathink_iso_rebuild.py` - ISO generation and rebuild
- `ultrathink_log_analyzer.py` - Log analysis and pattern detection
- `ultrathink_proxmox_integration.py` - Proxmox VE integration
- `ultrathink_zfs_kernel_builder.py` - ZFS kernel module building
- `ultrathink_zfs_prebuilder.py` - Pre-build preparation

## 📋 Usage Notes

- **Enhanced Tools**: Primary tools remain in project root for easy access
  - `launch-enhanced-gui.sh` - Main enhanced GUI launcher
  - `zforge-launcher.sh` - Main TUI launcher  
  - `build.py` - Core build system
  - `build-spec-commands.sh` - Interactive command generator

- **Legacy Tools**: Moved here for organization but still functional
- **Specialized Tools**: Organized by category for better maintenance

## 🔍 Finding Tools

```bash
# List all scripts by category
find scripts/ -name "*.sh" -o -name "*.py" | sort

# Find a specific tool
find scripts/ -name "*deploy*" -o -name "*bootstrap*"

# Run tools (most require sudo)
sudo scripts/deployment/zfs-stream-deploy.sh
sudo scripts/bootstrap/bootstrap_fixed.sh
```

---

*Scripts organized for Z-FORGE RAM Server Build System v3.0*
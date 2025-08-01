# Z-FORGE Documentation

Welcome to the Z-FORGE documentation. This directory contains all project documentation organized by category.

## Documentation Structure

### 📁 [build/](build/)
Build process documentation, environment setup guides, and build-related instructions.
- `BUILD_ENVIRONMENT_SETUP_GUIDE.md` - Complete build environment setup
- `BUILD_ORDER_OPTIMIZATION.md` - Build process optimization guide
- `BUILD_READY.md` - Build readiness checklist
- `NEXT_STEPS_AFTER_BOOTSTRAP.md` - Post-bootstrap instructions
- `PACKAGE_SOLUTION.md` - Package management solutions
- `POST_REBOOT_RESUME.md` - Post-reboot resumption guide

### 📁 [checkpoints/](checkpoints/)
Build checkpoints and status snapshots documenting the project progress.
- `CHECKPOINT_BOOTSTRAP_SOLUTION.md` - Bootstrap solution checkpoint
- `CHECKPOINT_COMPLETE_STATUS_20250730.md` - Latest complete status
- `CHECKPOINT_NO_TMP_BUILD_REDESIGN.md` - Non-/tmp build redesign
- `CHECKPOINT_ZFS_DEB_PACKAGES.md` - ZFS package checkpoint
- Historical checkpoints from various dates

### 📁 [features/](features/)
Advanced features and capabilities documentation.
- `ADVANCED_FEATURES.md` - Complete advanced features guide

### 📁 [hardware/](hardware/)
Hardware support documentation, compatibility lists, and hardware-specific guides.
- `HARDWARE_SPECIFIC_OPTIMIZATIONS.md` - Hardware optimization guide
- `SUPPORTED_HARDWARE.md` - List of supported hardware
- `STORAGE_SUPPORT_INVENTORY.md` - Storage device support
- `SAS_INTEGRATION_VERIFICATION.md` - SAS integration guide
- `CALAMARES_HARDWARE_INTEGRATION.md` - Hardware integration with Calamares

### 📁 [integration/](integration/)
Integration guides for various systems and components.
- `PROXMOX_BUILD_OPTIONS.md` - Proxmox build configuration
- `PROXMOX_INTEGRATION.md` - Complete Proxmox integration guide
- `MODULE_IMPLEMENTATION_SUMMARY.md` - Module implementation overview
- `calamares_*.md` - Calamares module integration guides
- `FINAL_INTEGRATION_VERIFICATION.md` - Integration verification checklist

### 📁 [MODULE_PROPOSALS/](MODULE_PROPOSALS/)
Proposed modules and feature enhancements.
- GPU passthrough, hardware health, network configuration modules
- Post-install checklist and storage layout proposals

### 📁 [planning/](planning/)
Planning documents and future roadmap.
- `FUTURE_TODO.md` - Future development tasks
- `FINAL_PREP_CHECKLIST.md` - Final preparation checklist

### 📁 [project/](project/)
Project-level documentation and guidelines.
- `CLAUDE.md` - AI assistant guidelines and context
- `README.md` - Project overview

### 📁 [reports/](reports/)
Analysis reports, summaries, and progress tracking.
- `ANALYSIS_REPORT_ZFS_FIXES.md` - ZFS fixes analysis
- `ULTRATHINK_REBUILD_README.md` - AI agent rebuild documentation
- Progress reports and implementation summaries
- `cleanup-process.md` - Cleanup process documentation

### 📁 [zfs/](zfs/)
ZFS-specific documentation and configuration guides.
- `ZFS_BUILD_SUMMARY.md` - ZFS build process summary
- `ZFS_WITHOUT_KERNEL_MODULES.md` - Userspace ZFS guide
- `ZFS_WEB_GUI_PROPOSAL.md` - Web GUI proposal
- `zfs_configuration_guide_outline.md` - Configuration guide outline
- `ZFS_2.3.3_INTEGRATION.md` - ZFS 2.3.3 integration details
- `ZFS_BUILD_COMPLIANCE.md` - Build compliance documentation
- `ZFS_RAID_CONFIGURATION.md` - RAID configuration guide

## Key Documents

### Getting Started
1. Start with [project/README.md](project/README.md) for project overview
2. Read [build/BUILD_ENVIRONMENT_SETUP_GUIDE.md](build/BUILD_ENVIRONMENT_SETUP_GUIDE.md) for setup
3. Check [checkpoints/](checkpoints/) for current project status

### For Developers
- [integration/MODULE_IMPLEMENTATION_SUMMARY.md](integration/MODULE_IMPLEMENTATION_SUMMARY.md) - Module development guide
- [reports/IMPLEMENTED_FIXES_SUMMARY.md](reports/IMPLEMENTED_FIXES_SUMMARY.md) - Applied fixes
- [zfs/ZFS_BUILD_COMPLIANCE.md](zfs/ZFS_BUILD_COMPLIANCE.md) - ZFS build standards

### For System Integrators
- [hardware/SUPPORTED_HARDWARE.md](hardware/SUPPORTED_HARDWARE.md) - Hardware compatibility
- [integration/PROXMOX_INTEGRATION.md](integration/PROXMOX_INTEGRATION.md) - Proxmox setup
- [features/ADVANCED_FEATURES.md](features/ADVANCED_FEATURES.md) - Advanced capabilities

## Document Naming Convention

- `CHECKPOINT_*.md` - Build checkpoints and status snapshots
- `*_GUIDE.md` - Step-by-step guides
- `*_SUMMARY.md` - Overview and summary documents
- `*_INTEGRATION.md` - Integration documentation
- `README.md` - Directory-specific documentation

## Contributing

When adding new documentation:
1. Place it in the appropriate category directory
2. Follow the naming convention
3. Update this README if adding a significant document
4. Keep documentation concise and well-structured

## Quick Links

- [Latest Status](checkpoints/CHECKPOINT_COMPLETE_STATUS_20250730.md)
- [Build Guide](build/BUILD_ENVIRONMENT_SETUP_GUIDE.md)
- [Hardware Support](hardware/SUPPORTED_HARDWARE.md)
- [ZFS Integration](zfs/ZFS_2.3.3_INTEGRATION.md)
- [Proxmox Setup](integration/PROXMOX_INTEGRATION.md)
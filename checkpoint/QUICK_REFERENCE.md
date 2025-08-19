# Z-FORGE Quick Reference - Post Cleanup (Jan 31, 2025)

## Essential Commands

### Chroot Management
```bash
# Bootstrap chroot (in HOME workspace)
sudo ./scripts/chroot/bootstrap_chroot.sh auto

# Enter chroot with arch-chroot
sudo ./scripts/chroot/use_arch_chroot.sh

# Complete ZFS installation
sudo ./scripts/chroot/complete_zfs_install.sh

# Install ZFS package only
sudo ./scripts/chroot/install_zfs_with_arch_chroot.sh
```

### Build Commands
```bash
# Standard build
make build

# Non-/tmp build (recommended)
make -f Makefile.no_tmp build

# Python build script
sudo python3 build.py
```

### Common Script Locations
- Build scripts: `scripts/build/`
- Chroot tools: `scripts/chroot/`
- Workspace management: `scripts/workspace/`
- Package management: `scripts/package/`
- Fixes and patches: `scripts/fixes/`
- Cleanup tools: `scripts/cleanup/`

### Documentation
- Main docs index: `docs/README.md`
- Build guides: `docs/build/`
- Latest status: `docs/checkpoints/`
- Hardware support: `docs/hardware/`
- Latest checkpoint: `checkpoint/CHECKPOINT_20250731_SCRIPT_CLEANUP.md`

### Workspace Configuration
- **All scripts now use**: `${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}`
- **No more** `/tmp/zforge_workspace` paths
- **Consistent** across all 86 active scripts

### Key Updates (Jan 31, 2025)
1. **Script cleanup complete** - 44 obsolete scripts removed
2. **Path consistency** - All scripts use HOME workspace
3. **Clean organization** - Everything properly categorized
4. **Verification tools** - New cleanup and verify scripts

### Testing & Verification
1. Test arch-chroot: `sudo ./scripts/chroot/use_arch_chroot.sh ls /`
2. Verify ZFS install: `sudo ./scripts/chroot/use_arch_chroot.sh which zfs`
3. Check workspace: `ls -la ~/zforge_workspace/`
4. Verify consistency: `./scripts/cleanup/verify_project_consistency.sh`

### Quick Fixes
- DNS issues: `scripts/fixes/fix_chroot_network.sh`
- Workspace issues: `scripts/workspace/fix_workspace_noexec.sh`
- APT issues: `scripts/fixes/fix_apt_sources_zfs.sh`
- Path updates: `scripts/cleanup/fix_old_paths.sh`

### Project Statistics
- Active scripts: 86
- Removed obsolete: 44
- Path consistency: 100%
- Ready for build: ✅
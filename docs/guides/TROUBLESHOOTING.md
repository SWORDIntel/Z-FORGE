# Z-FORGE Troubleshooting Guide

**Last Updated:** January 31, 2025

## Common Issues and Solutions

### 1. Bootstrap Issues

#### Problem: Bootstrap hangs or fails
```bash
# Symptoms:
# - Process hangs at "Extracting..."
# - Network errors during download
# - Permission denied errors
```

**Solutions:**
```bash
# Try alternative bootstrap method
sudo ./scripts/chroot/bootstrap_chroot.sh debootstrap

# If still failing, check DNS
cat /etc/resolv.conf
# Should contain valid nameservers

# Fix DNS if needed
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# Clean and retry
rm -rf ~/zforge_workspace/chroot
sudo ./scripts/chroot/bootstrap_chroot.sh auto
```

#### Problem: arch-chroot hangs with no response
```bash
# Symptom: Can't exit with Ctrl+C
```

**Solution:**
```bash
# Use emergency cleanup
./scripts/chroot/emergency_cleanup.sh

# Use standard chroot instead
sudo ./scripts/chroot/use_arch_chroot.sh
# This auto-detects and falls back to standard chroot
```

### 2. Permission Issues

#### Problem: Permission denied on chroot directory
```bash
# Symptom: ls: cannot access 'chroot/usr': Permission denied
```

**Solution:**
```bash
# Fix permissions
sudo chmod 755 ~/zforge_workspace/chroot
sudo chmod 755 ~/zforge_workspace/chroot/usr

# If persists, check ownership
sudo chown -R root:root ~/zforge_workspace/chroot
```

### 3. Workspace Issues

#### Problem: /tmp mounted with noexec
```bash
# Symptom: Cannot execute scripts in /tmp
```

**Solution:**
```bash
# Already fixed! All scripts use HOME workspace
# Verify with:
echo $ZFORGE_WORKSPACE
# Should show: /home/youruser/zforge_workspace

# If not set, run:
export ZFORGE_WORKSPACE="$HOME/zforge_workspace"
```

### 4. ZFS Installation Issues

#### Problem: ZFS package not found
```bash
# Symptom: E: Unable to locate package zfsutils-linux
```

**Solution:**
```bash
# Fix apt sources
sudo ./scripts/fixes/fix_apt_sources_zfs.sh

# Or manually add backports
sudo ./scripts/chroot/use_arch_chroot.sh bash -c '
echo "deb http://deb.debian.org/debian trixie-backports main contrib" >> /etc/apt/sources.list
apt-get update
'
```

#### Problem: Python dependency missing
```bash
# Symptom: zfsutils-linux depends on python3 but it is not installable
```

**Solution:**
```bash
# Use our prebuilt package
sudo cp prebuilt_packages/zfsutils-userspace_2.3.3-1_amd64.deb ~/zforge_workspace/chroot/tmp/
sudo ./scripts/chroot/use_arch_chroot.sh bash -c '
dpkg -i /tmp/zfsutils-userspace_2.3.3-1_amd64.deb
apt-get -f install -y
'
```

### 5. Build Failures

#### Problem: Makefile not found
```bash
# Symptom: make: *** No rule to make target 'build'
```

**Solution:**
```bash
# Use the no_tmp Makefile
make -f Makefile.no_tmp build

# Or create standard Makefile symlink
ln -s Makefile.no_tmp Makefile
make build
```

#### Problem: Python module import errors
```bash
# Symptom: ImportError: No module named 'builder'
```

**Solution:**
```bash
# Ensure you're in project root
cd /opt/github/Z-FORGE

# Check Python path
python3 -c "import sys; print(sys.path)"

# Run with explicit path
PYTHONPATH=/opt/github/Z-FORGE sudo python3 build.py
```

### 6. Mount Issues

#### Problem: Hanging mounts after failed build
```bash
# Symptom: Device or resource busy
```

**Solution:**
```bash
# Check for active mounts
mount | grep zforge_workspace

# Clean up mounts
./scripts/chroot/emergency_cleanup.sh

# Or manually
sudo umount -l ~/zforge_workspace/chroot/dev/pts
sudo umount -l ~/zforge_workspace/chroot/dev
sudo umount -l ~/zforge_workspace/chroot/proc
sudo umount -l ~/zforge_workspace/chroot/sys
```

### 7. Git Issues

#### Problem: Permission denied on '=p/' directory
```bash
# Symptom: warning: could not open directory '=p/': Permission denied
```

**Solution:**
```bash
# This is a known issue, safe to ignore
# Or remove the directory
sudo rm -rf '=p/'
```

### 8. Script Path Issues

#### Problem: Scripts using old /tmp paths
```bash
# This should be fixed, but if you see it...
```

**Solution:**
```bash
# Run path update tool
./scripts/cleanup/fix_old_paths.sh

# Verify no old paths remain
grep -r "/tmp/zforge_workspace" scripts/ --include="*.sh" | wc -l
# Should return 0
```

## Diagnostic Commands

### Check System State
```bash
# Verify workspace
echo "Workspace: ${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}"

# Check mounts
mount | grep zforge

# Check chroot status
ls -ld ~/zforge_workspace/chroot 2>/dev/null || echo "No chroot found"

# Verify scripts are executable
find scripts/ -name "*.sh" -not -executable | wc -l
# Should be 0
```

### Run Full Diagnostics
```bash
# Pre-build check
./scripts/testing/pre-build-check.sh

# Consistency verification
./scripts/cleanup/verify_project_consistency.sh

# Check for old paths
grep -r "/tmp/zforge_workspace" scripts/ --include="*.sh"
```

## Recovery Procedures

### Complete Reset
```bash
# Remove everything and start fresh
rm -rf ~/zforge_workspace
git clean -fdx
git reset --hard HEAD

# Rebuild from scratch
./scripts/workspace/setup_no_tmp_build.sh
sudo ./scripts/chroot/bootstrap_chroot.sh auto
sudo ./scripts/chroot/complete_zfs_install.sh
sudo make -f Makefile.no_tmp build
```

### Partial Recovery
```bash
# Just clean build artifacts
make -f Makefile.no_tmp clean

# Keep chroot, rebuild ISO
sudo make -f Makefile.no_tmp build
```

## Getting More Help

### Log Files
- Build log: `~/zforge_workspace/logs/zforge_build_*.log`
- Bootstrap log: `~/zforge_workspace/logs/bootstrap.log`
- Module logs: `~/zforge_workspace/logs/modules/*.log`

### Verbose Output
```bash
# Run build with debug output
sudo make -f Makefile.no_tmp build DEBUG=1

# Or with Python
sudo python3 build.py --verbose
```

### Check Documentation
- Quick Reference: `checkpoint/QUICK_REFERENCE.md`
- Latest Status: `checkpoint/CHECKPOINT_20250731_SCRIPT_CLEANUP.md`
- Build Guide: `BUILD_FROM_FRESH.md`
- Project Docs: `docs/README.md`

## Known Working Configuration

- **OS**: Debian 12/13 or Ubuntu 22.04/24.04
- **Workspace**: `~/zforge_workspace` (not /tmp)
- **Scripts**: All 86 scripts using consistent paths
- **ZFS**: Version 2.3.3 from Proxmox source
- **Build System**: Makefile.no_tmp

## If All Else Fails

1. Save your work
2. Check the latest checkpoint in `checkpoint/`
3. Review recent git commits
4. Start fresh with `BUILD_FROM_FRESH.md`

Remember: All scripts now use `${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}` consistently!
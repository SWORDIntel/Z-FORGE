# Z-FORGE Troubleshooting Guide

## Quick Diagnostics & Recovery

### 🚀 Quick Start Commands

```bash
# Run full system diagnostics
python3 tools/build_diagnostic_tool.py

# Automatic recovery from common issues
python3 tools/build_recovery_tool.py --auto

# Analyze specific log file
python3 tools/build_recovery_tool.py --log logs/zforge_build_*.log

# Check integration status
python3 tools/test_full_integration.py
```

## Common Build Failures & Solutions

### 1. ❌ dpkg/APT Errors

**Symptoms:**
- `E: Sub-process /usr/bin/dpkg returned an error code (1)`
- `dpkg: error processing package`
- `E: Unable to correct problems, you have held broken packages`

**Solutions:**
```bash
# Automatic fix
python3 tools/build_recovery_tool.py --error dpkg_error

# Manual fix
sudo dpkg --configure -a
sudo apt-get install -f
sudo apt-get clean
sudo apt-get update
```

### 2. 🔒 APT Lock Files

**Symptoms:**
- `Could not get lock /var/lib/dpkg/lock-frontend`
- `Unable to acquire the dpkg frontend lock`
- `Another process is using APT`

**Solutions:**
```bash
# Automatic fix
python3 tools/build_recovery_tool.py --error apt_lock

# Manual fix
sudo killall apt apt-get dpkg
sudo rm /var/lib/dpkg/lock-frontend
sudo rm /var/lib/apt/lists/lock
sudo dpkg --configure -a
```

### 3. 💾 ZFS Installation Failures

**Symptoms:**
- `Failed to install ['zfsutils-linux', 'zfs-dkms']`
- `Module build for kernel failed`
- `DKMS: build failed`

**Solutions:**
```bash
# Automatic fix
python3 tools/build_recovery_tool.py --error zfs_install

# Manual fix
# Install kernel headers
sudo apt-get install linux-headers-$(uname -r)
sudo apt-get install dkms

# Add contrib/non-free repos
sudo sed -i 's/main/main contrib non-free/g' /etc/apt/sources.list
sudo apt-get update

# Install ZFS
sudo apt-get install zfsutils-linux zfs-dkms

# Or use prebuilt packages (faster)
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml
```

### 4. 🐧 Kernel Installation Issues

**Symptoms:**
- `Kernel acquisition failed`
- `linux-image-* not found`
- `returned non-zero exit status 100`

**Solutions:**
```bash
# Automatic fix
python3 tools/build_recovery_tool.py --error kernel_install

# Use stable kernel
sudo python3 build.py --spec build_specs/build_spec_stable.yml

# Manual kernel install
sudo apt-get update
sudo apt-get install linux-image-amd64 linux-headers-amd64

# Remove initramfs-tools conflicts
sudo apt-get remove initramfs-tools
sudo apt-get install dracut dracut-core
```

### 5. 🌐 Network Connectivity Issues

**Symptoms:**
- `Could not resolve host`
- `Network is unreachable`
- `Connection refused`

**Solutions:**
```bash
# Check connectivity
ping -c 4 8.8.8.8
nslookup debian.org

# Fix DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# Restart network
sudo systemctl restart systemd-resolved

# Use proxy if needed
export http_proxy=http://proxy:port
export https_proxy=http://proxy:port
```

### 6. 💽 Disk Space Issues

**Symptoms:**
- `No space left on device`
- `insufficient space`
- Build stops unexpectedly

**Solutions:**
```bash
# Automatic cleanup
python3 tools/build_recovery_tool.py --error disk_space

# Manual cleanup
# Check space
df -h

# Clean APT cache
sudo apt-get clean
sudo apt-get autoclean

# Remove old kernels
sudo apt-get autoremove --purge

# Clean workspace
rm -rf /home/john/zforge_workspace/chroot.old
rm -rf /home/john/zforge_workspace/*.log
```

### 7. 📁 Mount/Unmount Errors

**Symptoms:**
- `target is busy`
- `mount point does not exist`
- `already mounted`

**Solutions:**
```bash
# Automatic fix
python3 tools/build_recovery_tool.py --error mount_error

# Manual fix
# Check mounts
mount | grep chroot

# Kill processes using mount
sudo fuser -km /home/john/zforge_workspace/chroot

# Force unmount
sudo umount -l /home/john/zforge_workspace/chroot/dev
sudo umount -l /home/john/zforge_workspace/chroot/proc
sudo umount -l /home/john/zforge_workspace/chroot/sys
```

### 8. 🔨 Chroot Environment Issues

**Symptoms:**
- `chroot: failed to run command`
- `cannot change root directory`
- Missing directories in chroot

**Solutions:**
```bash
# Automatic fix
python3 tools/build_recovery_tool.py --error chroot_error

# Rebuild chroot
rm -rf /home/john/zforge_workspace/chroot
sudo python3 build.py --spec build_specs/build_spec_stable.yml

# Fix permissions
sudo chown -R root:root /home/john/zforge_workspace/chroot
```

### 9. 🔧 Initramfs/Dracut Errors

**Symptoms:**
- `update-initramfs failed`
- `dracut: command not found`
- `No space left on device` in /boot

**Solutions:**
```bash
# Automatic fix
python3 tools/build_recovery_tool.py --error initramfs_error

# Manual fix
# Remove old initramfs files
sudo rm /boot/initrd.img-*.old

# Install dracut
sudo apt-get remove initramfs-tools
sudo apt-get install dracut dracut-core

# Regenerate initramfs
sudo dracut -f
```

## Pre-Build Checklist

### System Requirements
- [ ] **CPU**: Minimum 2 cores (4+ recommended)
- [ ] **RAM**: Minimum 4GB (8GB+ recommended)
- [ ] **Disk**: Minimum 50GB free
- [ ] **Network**: Internet connectivity
- [ ] **Permissions**: sudo access

### Run Pre-Build Validation
```bash
# Full diagnostic check
python3 tools/build_diagnostic_tool.py

# Quick validation
python3 builder/modules/build_pipeline_validator.py

# Test integration
python3 tools/test_full_integration.py
```

## Build Strategies

### 🏃 Fastest Build (Prebuilt Packages)
```bash
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml
```
- Uses prebuilt ZFS and Proxmox packages
- Minimal compilation required
- Best for testing and development

### 🛡️ Most Stable Build
```bash
sudo python3 build.py --spec build_specs/build_spec_stable.yml
```
- Uses Debian Bookworm stable packages
- Conservative kernel version
- Best for production systems

### 🎯 Custom Workspace Build
```bash
# For systems with /tmp restrictions
sudo python3 build.py --spec build_specs/build_spec_no_tmp.yml
```
- Builds entirely in home directory
- Avoids noexec /tmp issues

### 🖥️ GUI Method (Easiest)
```bash
python3 zforge_gui.py
```
- Visual build selection
- Real-time progress monitoring
- Automatic error detection

## Advanced Recovery

### Complete System Reset
```bash
# Nuclear option - clean everything
sudo rm -rf /home/john/zforge_workspace
sudo apt-get clean
sudo apt-get autoremove --purge
sudo dpkg --configure -a
sudo apt-get install -f
sudo apt-get update

# Start fresh
python3 tools/build_diagnostic_tool.py
sudo python3 build.py --spec build_specs/build_spec_stable.yml
```

### Analyze Failed Builds
```bash
# Find recent failures
ls -la logs/*.log | tail -5

# Analyze specific log
python3 tools/build_recovery_tool.py --log logs/zforge_build_20250804_014118.log

# Generate failure report
python3 tools/analyze_build_failures.py
```

### Debug Mode Build
```bash
# Run with verbose output
sudo python3 build.py --spec build_specs/build_spec_stable.yml --debug

# Keep temporary files for inspection
sudo python3 build.py --spec build_specs/build_spec_stable.yml --keep-temp
```

## Environment Variables

### Optimize Build Performance
```bash
# Set parallel jobs (adjust to CPU count)
export MAKEFLAGS="-j$(nproc)"

# Set workspace
export ZFORGE_WORKSPACE="/home/john/zforge_workspace"

# Enable debug output
export ZFORGE_DEBUG=1

# Disable GPG checks (for testing only)
export APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1
```

## Known Issues & Workarounds

### Issue: Build crashes in Claude Code
**Solution**: Never run builds in Claude Code environment
```bash
# Always run in terminal with sudo
sudo python3 build.py --spec <spec_file>
```

### Issue: Trixie repository issues
**Solution**: Use stable or snapshot repositories
```bash
# Switch to stable
sudo python3 build.py --spec build_specs/build_spec_stable.yml

# Or use snapshot
export DEBIAN_SNAPSHOT="20250730T000000Z"
```

### Issue: ZFS version mismatches
**Solution**: Use matching kernel and ZFS versions
```bash
# Check compatibility
modinfo zfs | grep version
uname -r

# Use prebuilt packages for guaranteed compatibility
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml
```

## Getting Help

### Diagnostic Tools
1. **tools/build_diagnostic_tool.py** - System validation
2. **tools/build_recovery_tool.py** - Automatic recovery
3. **tools/analyze_build_failures.py** - Log analysis
4. **tools/test_full_integration.py** - Integration testing

### Log Locations
- Build logs: `/opt/github/Z-FORGE/logs/`
- Test logs: `/opt/github/Z-FORGE/logs/tests/`
- Chroot logs: `/home/john/zforge_workspace/chroot/var/log/`

### Support Resources
- Check `FULL_INTEGRATION_DOCUMENTATION.md`
- Review `DARK_THEME_IMPLEMENTATION.md` for GUI
- See `DRACUT_IMPLEMENTATION.md` for initramfs issues

## Emergency Recovery Commands

```bash
# If everything is broken
sudo killall -9 apt-get dpkg
sudo rm -f /var/lib/dpkg/lock*
sudo rm -f /var/lib/apt/lists/lock
sudo dpkg --configure -a
sudo apt-get install -f
sudo apt-get clean
sudo apt-get update

# Reset workspace
sudo rm -rf /home/john/zforge_workspace
mkdir -p /home/john/zforge_workspace

# Test system
python3 tools/build_diagnostic_tool.py

# Try simplest build
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml
```

## Build Success Tips

1. **Always run diagnostics first**: `python3 tools/build_diagnostic_tool.py`
2. **Use the GUI for easier management**: `python3 zforge_gui.py`
3. **Start with stable/prebuilt specs** before trying experimental ones
4. **Monitor disk space** - need at least 50GB free
5. **Run with sudo** - many operations require root
6. **Check network connectivity** before starting
7. **Use recovery tools** when builds fail
8. **Keep logs** for troubleshooting

---

**Remember**: When in doubt, run `python3 tools/build_diagnostic_tool.py` first!
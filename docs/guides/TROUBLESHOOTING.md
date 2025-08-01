# Z-FORGE Troubleshooting Guide

## Common Issues and Solutions

### 1. Permission Denied Errors

**Symptoms:**
- `Permission denied` when running scripts
- Cannot access files in Z-FORGE directory

**Solutions:**
```bash
# Fix ownership
sudo chown -R $USER:$USER /opt/github/Z-FORGE

# Fix script permissions
find scripts -name "*.sh" -exec chmod +x {} \;

# Fix Python scripts
find scripts -name "*.py" -exec chmod +x {} \;
```

### 2. Chroot Bootstrap Fails

**Symptoms:**
- `debootstrap` fails to create chroot
- Network errors during bootstrap

**Solutions:**
```bash
# Check internet connection
ping google.com

# Try different mirror
sudo ./scripts/chroot/bootstrap_chroot.sh auto ~/zforge_workspace/chroot http://deb.debian.org/debian

# Clean and retry
sudo rm -rf ~/zforge_workspace/chroot
sudo ./scripts/chroot/bootstrap_chroot.sh auto
```

### 3. Network Issues in Chroot

**Symptoms:**
- `apt update` fails in chroot
- DNS resolution errors
- Cannot download packages

**Solutions:**
```bash
# Quick fix
sudo ./scripts/fixes/fix_chroot_network.sh

# Manual fix
sudo cp /etc/resolv.conf ~/zforge_workspace/chroot/etc/resolv.conf

# Fix systemd-resolved
sudo ./scripts/fixes/fix_systemd_resolved_dns.sh
```

### 4. ZFS Installation Fails

**Symptoms:**
- `zfs` command not found
- DKMS build errors
- Kernel module issues

**Solutions:**
```bash
# Use complete installation (handles most issues)
sudo ./scripts/chroot/complete_zfs_install.sh

# Manual fix for repositories
sudo ./scripts/fixes/fix_zfs_backports.py

# Alternative: Use Debian packages
sudo ./scripts/chroot/use_arch_chroot.sh
apt install -y zfsutils-linux
```

### 5. Build Fails with Python Errors

**Symptoms:**
- `ModuleNotFoundError: No module named 'yaml'`
- Python import errors

**Solutions:**
```bash
# Install Python dependencies
sudo apt install -y python3-pip python3-yaml python3-dev

# Install additional modules
pip3 install pyyaml jinja2 requests
```

### 6. Workspace Permission Issues

**Symptoms:**
- Cannot execute scripts from `/tmp`
- `Operation not permitted` in workspace

**Solutions:**
```bash
# Fix noexec mount
sudo ./scripts/workspace/fix_workspace_noexec.sh

# Use HOME workspace instead
export ZFORGE_WORKSPACE="$HOME/zforge_workspace"
sudo make -f Makefile.no_tmp build
```

### 7. APT Repository Issues

**Symptoms:**
- GPG signature errors
- Repository not found
- Package authentication failures

**Solutions:**
```bash
# Fix APT sources
sudo ./scripts/fixes/fix_apt_sources_zfs.sh

# Fix GPG keys
sudo ./scripts/fixes/fix_apt_key_missing.sh

# Manual repository fix
sudo ./scripts/fixes/enhanced_zfs_repo_setup.sh
```

### 8. Missing Dependencies

**Symptoms:**
- `command not found` errors
- Build tools missing

**Solutions:**
```bash
# Install complete build environment
sudo apt install -y \
    build-essential \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-utils \
    genisoimage \
    python3-dev \
    python3-pip \
    python3-yaml \
    arch-install-scripts
```

### 9. Dracut Initramfs Issues

**Symptoms:**
- Initramfs generation fails
- Boot errors

**Solutions:**
```bash
# Fix dracut configuration
sudo ./scripts/fixes/fix_dracut_initramfs.py

# Manual dracut fix
sudo ./scripts/fixes/fix_dracut_issue.py
```

### 10. Build Hangs or Freezes

**Symptoms:**
- Build process stops responding
- No output for extended periods

**Solutions:**
```bash
# Kill and restart
sudo pkill -f python3
sudo pkill -f make

# Clean and rebuild
sudo make clean
sudo ./scripts/chroot/complete_zfs_install.sh
sudo make -f Makefile.no_tmp build
```

## Diagnostic Commands

### Check System Status
```bash
# Check disk space
df -h

# Check memory
free -h

# Check processes
ps aux | grep -E "(python|make|debootstrap)"
```

### Check Chroot Status
```bash
# Verify chroot exists
ls -la ~/zforge_workspace/chroot/

# Test chroot access
sudo ./scripts/chroot/use_arch_chroot.sh ls /

# Check ZFS in chroot
sudo ./scripts/chroot/use_arch_chroot.sh which zfs
```

### Check Build Environment
```bash
# Python modules
python3 -c "import yaml; print('OK')"

# Build tools
which debootstrap mksquashfs xorriso
```

## Emergency Recovery

### Complete Clean Start
```bash
# Stop all processes
sudo pkill -f zforge
sudo pkill -f python3

# Clean everything
sudo rm -rf ~/zforge_workspace
sudo make clean

# Start fresh
sudo ./scripts/chroot/complete_zfs_install.sh
```

### Backup Before Changes
```bash
# Backup working chroot
sudo cp -r ~/zforge_workspace/chroot ~/zforge_workspace/chroot.backup

# Restore if needed
sudo rm -rf ~/zforge_workspace/chroot
sudo mv ~/zforge_workspace/chroot.backup ~/zforge_workspace/chroot
```

## Getting More Help

### Check Logs
```bash
# Build logs
ls -la logs/
tail -50 logs/zforge_build_*.log

# System logs
sudo journalctl -f
sudo dmesg | tail -20
```

### Enable Debug Mode
```bash
# Debug build
sudo make debug

# Verbose Python
sudo python3 build.py --debug --verbose
```

### Use Quick Fixes
```bash
# Available quick fixes
ls scripts/fixes/

# Run specific fix
sudo ./scripts/fixes/[fix-name].sh
```

### Validation Scripts
```bash
# Validate environment
sudo ./scripts/testing/verify_build_ready.sh

# Check package availability
python3 scripts/fixes/validate_package_availability.py
```

## Prevention

### Before Starting
1. Ensure sufficient disk space (20GB+)
2. Use stable internet connection
3. Have sudo access
4. Update system packages first

### Best Practices
1. Use HOME workspace over /tmp
2. Run complete installation script first
3. Check logs if build fails
4. Keep backups of working chroot
5. Test in VM before real hardware

### Regular Maintenance
```bash
# Clean old logs
sudo rm logs/*.log.old

# Update system
sudo apt update && sudo apt upgrade

# Verify chroot health
sudo ./scripts/chroot/use_arch_chroot.sh apt update
```
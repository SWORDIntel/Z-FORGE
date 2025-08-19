# Z-FORGE Build Commands with Logging

## Quick Build Commands

### 1. Minimal Build (Testing - Fastest)
```bash
# Quick test build with minimal packages
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml \
    --workspace /tmp/zforge-minimal \
    --verbose 2>&1 | tee logs/minimal-$(date +%Y%m%d-%H%M%S).log
```

### 2. Proxmox VE 9 Standard Build
```bash
# Standard Proxmox VE 9 build
sudo python3 build.py --spec build_specs/build_spec_proxmox9.yml \
    --workspace /tmp/zforge-proxmox9 \
    --verbose 2>&1 | tee logs/proxmox9-$(date +%Y%m%d-%H%M%S).log
```

### 3. Proxmox VE 9 Full Build (All Features)
```bash
# Full Proxmox with all features (Ceph, HA, Backup Server)
sudo python3 build.py --spec build_specs/build_spec_proxmox_full.yml \
    --workspace /tmp/zforge-proxmox-full \
    --verbose 2>&1 | tee logs/proxmox-full-$(date +%Y%m%d-%H%M%S).log
```

### 4. Stable Production Build
```bash
# Stable configuration for production
sudo python3 build.py --spec build_specs/build_spec_stable.yml \
    --workspace /tmp/zforge-stable \
    --verbose 2>&1 | tee logs/stable-$(date +%Y%m%d-%H%M%S).log
```

### 5. Clean Trixie Build (No Proxmox)
```bash
# Clean Debian Trixie with ZFS
sudo python3 build.py --spec build_specs/build_spec_trixie_clean.yml \
    --workspace /tmp/zforge-trixie \
    --verbose 2>&1 | tee logs/trixie-$(date +%Y%m%d-%H%M%S).log
```

## Advanced Build Commands

### Build with Debug Output
```bash
# Maximum verbosity for troubleshooting
sudo python3 build.py --spec build_specs/build_spec_proxmox_full.yml \
    --workspace /tmp/zforge-debug \
    --debug \
    --verbose 2>&1 | tee -a logs/debug-$(date +%Y%m%d-%H%M%S).log
```

### Resume Failed Build
```bash
# Resume from last checkpoint
sudo python3 build.py --spec build_specs/build_spec_proxmox_full.yml \
    --workspace /tmp/zforge-proxmox-full \
    --resume \
    --verbose 2>&1 | tee -a logs/resume-$(date +%Y%m%d-%H%M%S).log
```

### Build with Custom Kernel
```bash
# Specify kernel version explicitly
sudo KERNEL_VERSION=6.14.8-2 python3 build.py \
    --spec build_specs/build_spec_proxmox_full.yml \
    --workspace /tmp/zforge-custom \
    --verbose 2>&1 | tee logs/custom-$(date +%Y%m%d-%H%M%S).log
```

## Parallel Builds (Different Terminals)

### Terminal 1: Minimal Build
```bash
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml \
    --workspace /tmp/zforge-minimal-1 \
    2>&1 | tee logs/parallel-minimal-$(date +%Y%m%d-%H%M%S).log &
```

### Terminal 2: Proxmox Build
```bash
sudo python3 build.py --spec build_specs/build_spec_proxmox9.yml \
    --workspace /tmp/zforge-proxmox-2 \
    2>&1 | tee logs/parallel-proxmox-$(date +%Y%m%d-%H%M%S).log &
```

## Monitoring Commands

### Watch Build Progress
```bash
# Real-time log monitoring
tail -f logs/proxmox-full-*.log | grep -E "INFO|ERROR|SUCCESS|FAIL"
```

### Monitor System Resources During Build
```bash
# In separate terminal
watch -n 2 'free -h; echo; df -h /tmp; echo; ps aux | grep python3 | grep -v grep'
```

### Check Build Status
```bash
# Show progress from checkpoint file
cat /tmp/zforge-*/build_progress.json | jq '.'
```

## Log Analysis Commands

### Find Errors in Logs
```bash
# Search all logs for errors
grep -n "ERROR\|FAIL\|Exception" logs/*.log | less
```

### Extract Build Times
```bash
# Show build durations
for log in logs/*.log; do
    echo "$(basename $log):"
    grep "Duration:" "$log" | tail -1
done
```

### Compare Build Sizes
```bash
# List ISO sizes
ls -lh output/*.iso | awk '{print $9, $5}'
```

## Automated Build Scripts

### Build All Versions
```bash
# Use the comprehensive build script
sudo ./build-all-versions.sh all
```

### Build Specific Set
```bash
# Build only Proxmox versions
sudo ./build-all-versions.sh proxmox
```

### Interactive Build Menu
```bash
# Interactive selection
sudo ./build-all-versions.sh menu
```

## Cleanup Commands

### Clean Failed Build
```bash
# Remove specific failed workspace
sudo rm -rf /tmp/zforge-workspace-*
```

### Clean All Workspaces
```bash
# Remove all build workspaces
sudo find /tmp -maxdepth 1 -name "zforge-*" -type d -exec rm -rf {} \;
```

### Archive Logs
```bash
# Compress old logs
tar czf logs/archive-$(date +%Y%m%d).tar.gz logs/*.log --remove-files
```

## Environment Variables

### Set Build Environment
```bash
# Configure build environment
export ZFORGE_DEBUG=1
export ZFORGE_CACHE_DIR=/var/cache/zforge
export ZFORGE_PARALLEL_JOBS=$(nproc)
export ZFORGE_RAM_BUILD=true
```

### Build with Custom Config
```bash
# Override configuration
DEBIAN_MIRROR=http://local-mirror.example.com/debian \
ZFS_VERSION=2.3.3 \
KERNEL_VERSION=6.14.8-2 \
sudo -E python3 build.py --spec build_specs/build_spec_proxmox_full.yml
```

## Troubleshooting Commands

### Check Prerequisites
```bash
# Verify system is ready
sudo apt-get update
sudo apt-get install -y debootstrap squashfs-tools xorriso arch-install-scripts
```

### Test Specific Module
```bash
# Test individual module
sudo python3 -c "
from builder.modules.debootstrap import Debootstrap
d = Debootstrap({'workspace': '/tmp/test', 'chroot_path': '/tmp/test/chroot'})
print(d.validate())
"
```

### Generate Diagnostic Report
```bash
# Full system diagnostic
sudo python3 tools/build_diagnostic_tool.py --full > diagnostic-$(date +%Y%m%d).txt
```

## Tips

1. **Always use logging**: Pipe output to `tee` for both console and file logging
2. **Use timestamps**: Include `$(date +%Y%m%d-%H%M%S)` in log filenames
3. **Monitor /tmp space**: RAM builds require sufficient space in /tmp
4. **Use --resume**: Can save hours on large builds that fail
5. **Parallel builds**: Use different workspace names to run multiple builds
6. **Clean regularly**: Remove old workspaces to free RAM/disk space

## Log File Locations

- **Build logs**: `./logs/`
- **Module logs**: `/tmp/zforge-*/logs/`
- **System logs**: `/var/log/zforge/`
- **Checkpoint files**: `/tmp/zforge-*/build_progress.json`
- **Resource monitoring**: `./logs/*_resources.log`
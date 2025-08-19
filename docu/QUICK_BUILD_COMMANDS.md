# Z-FORGE Quick Build Commands
## Direct Execution Without Complex Bootstrap

### 🎯 **Simplest Approach: Use Existing Build System**

**1. Minimal Working Build (Most Stable)**
```bash
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose --debug 2>&1 | tee logs/quick-minimal-$(date +%Y%m%d_%H%M%S).log
```

**2. ZFS-Only Build (No Proxmox)**
```bash
sudo python3 build.py --spec build_specs/build_spec_no_proxmox.yml --verbose --debug 2>&1 | tee logs/quick-zfs-$(date +%Y%m%d_%H%M%S).log
```

**3. High-Performance Build (Recommended)**
```bash
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml --verbose --debug 2>&1 | tee logs/quick-outside-$(date +%Y%m%d_%H%M%S).log
```

**4. Full Proxmox VE 9 Build**
```bash
sudo python3 build.py --spec build_specs/build_spec_proxmox_full.yml --verbose --debug 2>&1 | tee logs/quick-pve9-$(date +%Y%m%d_%H%M%S).log
```

---

## 🔧 **Manual Step-by-Step Approach**

### **Step 1: Create Base System**
```bash
# Set workspace
export WORKSPACE="/tmp/zforge-manual-workspace"
sudo rm -rf "$WORKSPACE"
mkdir -p "$WORKSPACE"

# Run debootstrap directly
sudo debootstrap --arch=amd64 --include=wget,curl,gnupg,lsb-release trixie "$WORKSPACE/chroot" http://deb.debian.org/debian

# Verify
ls -la "$WORKSPACE/chroot/bin/bash"
cat "$WORKSPACE/chroot/etc/debian_version"
```

### **Step 2: Mount Required Filesystems**
```bash
sudo mount -t proc proc "$WORKSPACE/chroot/proc"
sudo mount -t sysfs sys "$WORKSPACE/chroot/sys"
sudo mount -t devtmpfs udev "$WORKSPACE/chroot/dev"
sudo mount -t devpts devpts "$WORKSPACE/chroot/dev/pts"
```

### **Step 3: Configure APT**
```bash
# Create sources.list
sudo tee "$WORKSPACE/chroot/etc/apt/sources.list" << EOF
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
EOF

# Update package lists
sudo chroot "$WORKSPACE/chroot" apt-get update
```

### **Step 4: Install ZFS**
```bash
# Install ZFS packages
sudo chroot "$WORKSPACE/chroot" apt-get install -y zfsutils-linux zfs-dkms

# Verify
sudo chroot "$WORKSPACE/chroot" which zfs
```

### **Step 5: Install Kernel**
```bash
# Install kernel and headers
sudo chroot "$WORKSPACE/chroot" apt-get install -y linux-image-amd64 linux-headers-amd64

# Verify
ls "$WORKSPACE/chroot/boot/vmlinuz-"*
```

### **Step 6: Cleanup**
```bash
# Unmount filesystems
sudo umount "$WORKSPACE/chroot/dev/pts" || true
sudo umount "$WORKSPACE/chroot/dev" || true
sudo umount "$WORKSPACE/chroot/proc" || true
sudo umount "$WORKSPACE/chroot/sys" || true
```

---

## 🚀 **Quickest Success Path**

**For immediate results, run these in order:**

```bash
# 1. Create logs directory
mkdir -p logs

# 2. Run minimal build (5 minutes)
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose 2>&1 | tee logs/build-$(date +%Y%m%d_%H%M%S).log

# 3. Check result
ls -la *.iso
```

---

## 📊 **Success Validation**

**Quick validation after build:**
```bash
# Check for ISO
ls -la *.iso

# Check build log for errors
grep -i "error\|failed" logs/*.log | tail -20

# Check workspace (if still exists)
du -sh /tmp/zforge-workspace-*
```

---

## 🆘 **If Builds Fail**

**Common fixes:**
```bash
# 1. Clean all workspaces
sudo rm -rf /tmp/zforge-workspace-*

# 2. Clear package cache
sudo apt-get clean

# 3. Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# 4. Install missing dependencies
sudo apt-get install -y debootstrap squashfs-tools xorriso isolinux

# 5. Try the working build spec (most stable)
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose
```

---

## 💡 **Direct Module Testing**

**Test individual modules without full build:**

```bash
# Test debootstrap only
python3 -c "
from builder.modules.debootstrap import Debootstrap
from pathlib import Path
workspace = Path('/tmp/test-workspace')
config = {'debian_release': 'trixie', 'debian_mirror': 'http://deb.debian.org/debian'}
module = Debootstrap(workspace, config)
result = module.execute()
print(f'Result: {result}')
"

# Test ZFS module only
python3 -c "
from builder.modules.zfs_build import ZfsBuild
from pathlib import Path
workspace = Path('/tmp/test-workspace')
config = {'version': '2.3.3', 'build_from_source': False}
module = ZfsBuild(workspace, config)
result = module.execute()
print(f'Result: {result}')
"
```

These commands bypass the complex bootstrap and use the build system directly!
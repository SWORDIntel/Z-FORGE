#!/bin/bash
# Quick script to build kernel modules outside chroot
# Focuses on ZFS and essential drivers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MODULE_DIR="$PROJECT_ROOT/built_modules"
LOG_FILE="$PROJECT_ROOT/logs/module_build_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$MODULE_DIR"
mkdir -p "$PROJECT_ROOT/logs"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "🔧 Building kernel modules on host system..."

if [[ $EUID -ne 0 ]]; then
    log "❌ This script must be run as root"
    echo "   sudo $0"
    exit 1
fi

# Get current kernel info
KERNEL_VERSION=$(uname -r)
KERNEL_DIR="/lib/modules/$KERNEL_VERSION/build"

log "🔍 Kernel version: $KERNEL_VERSION"
log "🔍 Kernel build dir: $KERNEL_DIR"

if [ ! -d "$KERNEL_DIR" ]; then
    log "❌ Kernel headers not found. Installing..."
    apt-get update
    apt-get install -y linux-headers-$(uname -r)
fi

cd "$MODULE_DIR"

# Build ZFS modules if ZFS source is available
if [ -f "$PROJECT_ROOT/prebuilt_packages/zfs-2.3.3.tar.gz" ]; then
    log "🔨 Building ZFS modules..."
    
    if [ ! -d "zfs-2.3.3" ]; then
        tar -xzf "$PROJECT_ROOT/prebuilt_packages/zfs-2.3.3.tar.gz"
    fi
    
    cd zfs-2.3.3
    
    # Configure for kernel modules only
    ./autogen.sh
    ./configure \
        --with-linux="$KERNEL_DIR" \
        --with-linux-obj="$KERNEL_DIR" \
        --with-config=kernel
    
    # Build modules
    make -j$(nproc)
    
    # Install modules
    make modules_install
    
    log "✅ ZFS modules built and installed"
    
    cd "$MODULE_DIR"
else
    log "⚠️  ZFS source not found, skipping ZFS module build"
fi

# Build additional useful modules
log "🔧 Building additional kernel modules..."

# NVIDIA modules (if NVIDIA hardware detected)
if lspci | grep -i nvidia > /dev/null; then
    log "🔧 NVIDIA hardware detected, preparing NVIDIA modules..."
    # Note: NVIDIA modules require specific driver packages
    log "💡 Tip: Install nvidia-driver package for NVIDIA modules"
fi

# VirtIO modules (important for VMs)
log "🔧 Ensuring VirtIO modules are available..."
VIRTIO_MODULES=(
    "virtio_pci"
    "virtio_net" 
    "virtio_blk"
    "virtio_scsi"
    "virtio_balloon"
)

for module in "${VIRTIO_MODULES[@]}"; do
    if modinfo "$module" &>/dev/null; then
        log "✅ $module available"
    else
        log "⚠️  $module not found"
    fi
done

# Check storage modules
log "🔧 Checking storage modules..."
STORAGE_MODULES=(
    "ahci"
    "sd_mod"
    "nvme"
    "mpt3sas"
    "megaraid_sas"
)

for module in "${STORAGE_MODULES[@]}"; do
    if modinfo "$module" &>/dev/null; then
        log "✅ $module available"
    else
        log "⚠️  $module not found"
    fi
done

# Create module loading script
log "📝 Creating module loading script..."
cat > "$MODULE_DIR/load_modules.sh" << 'EOF'
#!/bin/bash
# Load essential modules for Z-FORGE

echo "🔧 Loading essential kernel modules..."

# Storage modules
modprobe ahci || echo "⚠️  ahci failed"
modprobe sd_mod || echo "⚠️  sd_mod failed"
modprobe nvme || echo "⚠️  nvme failed"

# VirtIO modules
modprobe virtio_pci || echo "⚠️  virtio_pci failed"
modprobe virtio_net || echo "⚠️  virtio_net failed"
modprobe virtio_blk || echo "⚠️  virtio_blk failed"
modprobe virtio_scsi || echo "⚠️  virtio_scsi failed"

# ZFS modules
modprobe zfs || echo "⚠️  ZFS module failed"

# Network modules
modprobe e1000e || echo "⚠️  e1000e failed"
modprobe r8169 || echo "⚠️  r8169 failed"

echo "✅ Module loading complete"
lsmod | grep -E "(zfs|virtio|ahci|nvme)" | head -10
EOF

chmod +x "$MODULE_DIR/load_modules.sh"

# Create initramfs with modules
log "📦 Updating initramfs with new modules..."
update-initramfs -u

# Create module package for chroot
log "📦 Creating module package for chroot installation..."
cat > "$MODULE_DIR/install_modules_to_chroot.sh" << 'EOF'
#!/bin/bash
# Install built modules to chroot environment

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"

if [ ! -d "$CHROOT_PATH" ]; then
    echo "❌ Chroot not found: $CHROOT_PATH"
    exit 1
fi

echo "📦 Installing modules to $CHROOT_PATH"

# Copy kernel modules
KERNEL_VERSION=$(uname -r)
HOST_MODULES="/lib/modules/$KERNEL_VERSION"
CHROOT_MODULES="$CHROOT_PATH/lib/modules/$KERNEL_VERSION"

mkdir -p "$CHROOT_MODULES"

# Copy essential modules
echo "📂 Copying kernel modules..."
rsync -av "$HOST_MODULES/kernel/drivers/block/" "$CHROOT_MODULES/kernel/drivers/block/" || true
rsync -av "$HOST_MODULES/kernel/drivers/scsi/" "$CHROOT_MODULES/kernel/drivers/scsi/" || true
rsync -av "$HOST_MODULES/kernel/drivers/virtio/" "$CHROOT_MODULES/kernel/drivers/virtio/" || true
rsync -av "$HOST_MODULES/kernel/fs/" "$CHROOT_MODULES/kernel/fs/" || true

# Copy ZFS modules if they exist
if [ -d "$HOST_MODULES/updates/dkms" ]; then
    echo "📂 Copying ZFS modules..."
    mkdir -p "$CHROOT_MODULES/updates/dkms"
    rsync -av "$HOST_MODULES/updates/dkms/" "$CHROOT_MODULES/updates/dkms/" || true
fi

# Update module dependencies in chroot
echo "🔧 Updating module dependencies..."
chroot "$CHROOT_PATH" depmod -a "$KERNEL_VERSION"

echo "✅ Module installation to chroot complete!"
EOF

chmod +x "$MODULE_DIR/install_modules_to_chroot.sh"

# Create module manifest
log "📋 Creating module manifest..."
cat > "$MODULE_DIR/module_manifest.txt" << EOF
# Z-FORGE Kernel Module Build
# Built on: $(date)
# Kernel: $KERNEL_VERSION
# System: $(uname -a)

Built modules:
$(find /lib/modules/$KERNEL_VERSION -name "*.ko" | grep -E "(zfs|virtio|ahci|nvme)" | head -20)

Available tools:
- load_modules.sh: Load essential modules
- install_modules_to_chroot.sh: Copy modules to chroot

ZFS module status:
$(lsmod | grep zfs || echo "ZFS not loaded")

Storage modules:
$(lsmod | grep -E "(ahci|nvme|sd_mod)" || echo "Storage modules not loaded")
EOF

log "🎉 Kernel module build complete!"
log "📍 Modules at: $MODULE_DIR"
log "📄 Build log: $LOG_FILE"
echo ""
echo "Available tools:"
echo "1. Load modules: $MODULE_DIR/load_modules.sh"
echo "2. Install to chroot: $MODULE_DIR/install_modules_to_chroot.sh"
echo "3. Module manifest: $MODULE_DIR/module_manifest.txt"
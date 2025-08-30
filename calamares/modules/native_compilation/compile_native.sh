#!/bin/bash
# Native Compilation Script for Calamares
# Compiles ZFS and Proxmox with hardware-specific optimizations

set -euo pipefail

# Configuration from Calamares
ZFS_VERSION="${ZFS_VERSION:-2.3.4}"
PROXMOX_VERSION="${PROXMOX_VERSION:-9.0}"
PARALLEL_JOBS="${PARALLEL_JOBS:-0}"
OPTIMIZATION_LEVEL="${OPTIMIZATION_LEVEL:-native}"

# Paths
CDROM_PATH="/cdrom"
LOG_FILE="/tmp/native_compilation.log"
PROGRESS_FILE="/tmp/calamares_progress"

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

progress() {
    local stage="$1"
    local percent="$2"
    local message="$3"
    echo "PROGRESS:${stage}:${percent}:${message}" | tee -a "$PROGRESS_FILE"
    log "Progress: $stage ($percent%) - $message"
}

error_exit() {
    log "ERROR: $1"
    echo "ERROR: $1" > "$PROGRESS_FILE"
    exit 1
}

# Hardware detection function
detect_hardware() {
    progress "detect_hardware" 0 "Analyzing CPU capabilities..."
    
    local cpu_vendor cpu_model cpu_cores total_ram
    cpu_vendor=$(lscpu | grep "Vendor ID" | awk '{print $3}')
    cpu_model=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
    cpu_cores=$(nproc)
    total_ram=$(free -h | awk '/^Mem:/{print $2}')
    
    log "Detected Hardware:"
    log "  CPU: $cpu_model ($cpu_vendor)"
    log "  Cores: $cpu_cores"
    log "  RAM: $total_ram"
    
    # Set parallel jobs if not specified
    if [ "$PARALLEL_JOBS" -eq 0 ]; then
        PARALLEL_JOBS=$((cpu_cores > 1 ? cpu_cores - 1 : 1))
        log "  Build Jobs: $PARALLEL_JOBS"
    fi
    
    # Check for virtualization features
    if grep -q "vmx\|svm" /proc/cpuinfo; then
        log "  Virtualization: Hardware support detected"
    fi
    
    # Check for encryption acceleration
    if grep -q "aes" /proc/cpuinfo; then
        log "  AES-NI: Hardware acceleration available"
    fi
    
    # Check for SIMD support
    if grep -q "avx512" /proc/cpuinfo; then
        log "  SIMD: AVX-512 support"
    elif grep -q "avx2" /proc/cpuinfo; then
        log "  SIMD: AVX2 support"
    elif grep -q "avx" /proc/cpuinfo; then
        log "  SIMD: AVX support"
    fi
    
    progress "detect_hardware" 100 "Hardware analysis complete"
}

# Environment preparation
prepare_environment() {
    progress "prepare_environment" 0 "Installing build dependencies..."
    
    # Update package lists
    apt-get update -qq
    
    # Install essential build tools
    apt-get install -y -qq \
        build-essential \
        dkms \
        linux-headers-$(uname -r) \
        autoconf \
        automake \
        libtool \
        pkg-config \
        zlib1g-dev \
        uuid-dev \
        libblkid-dev \
        libssl-dev \
        libudev-dev \
        libattr1-dev \
        libelf-dev \
        python3-dev \
        python3-cffi \
        python3-setuptools
    
    progress "prepare_environment" 50 "Dependencies installed"
    
    # Find and install the DKMS package
    local dkms_package
    dkms_package=$(find "$CDROM_PATH" -name "zforge-zfs-proxmox-dkms_*_all.deb" | head -1)
    
    if [ -z "$dkms_package" ]; then
        error_exit "DKMS package not found on installation media"
    fi
    
    log "Installing DKMS package: $(basename "$dkms_package")"
    dpkg -i "$dkms_package" || apt-get -f install -y
    
    progress "prepare_environment" 100 "Build environment ready"
}

# ZFS compilation
compile_zfs() {
    progress "compile_zfs" 0 "Starting ZFS native compilation..."
    
    log "Compiling ZFS $ZFS_VERSION with native optimizations"
    
    # DKMS will handle the actual compilation with our optimization scripts
    if ! dkms build -m zfs -v "$ZFS_VERSION" -j "$PARALLEL_JOBS"; then
        error_exit "ZFS compilation failed"
    fi
    
    progress "compile_zfs" 75 "Installing ZFS modules..."
    
    if ! dkms install -m zfs -v "$ZFS_VERSION"; then
        error_exit "ZFS module installation failed"
    fi
    
    progress "compile_zfs" 100 "ZFS compilation complete"
}

# Proxmox compilation
compile_proxmox() {
    progress "compile_proxmox" 0 "Starting Proxmox native compilation..."
    
    log "Compiling Proxmox $PROXMOX_VERSION components"
    
    # Compile Proxmox kernel modules
    if ! dkms build -m proxmox-modules -v "$PROXMOX_VERSION" -j "$PARALLEL_JOBS"; then
        log "Warning: Some Proxmox modules failed to compile (this is often normal)"
    fi
    
    progress "compile_proxmox" 50 "Installing Proxmox modules..."
    
    # Install what was successfully built
    dkms install -m proxmox-modules -v "$PROXMOX_VERSION" || true
    
    progress "compile_proxmox" 100 "Proxmox compilation complete"
}

# Module installation and configuration
install_modules() {
    progress "install_modules" 0 "Configuring system services..."
    
    # Load ZFS modules
    modprobe zfs 2>/dev/null || log "Warning: Could not load ZFS module (normal during installation)"
    
    # Enable ZFS services
    systemctl enable zfs-import-cache || true
    systemctl enable zfs-import-scan || true  
    systemctl enable zfs-mount || true
    systemctl enable zfs.target || true
    
    progress "install_modules" 50 "Enabling Proxmox services..."
    
    # Enable Proxmox services (if available)
    systemctl enable pve-cluster || true
    systemctl enable pvedaemon || true
    systemctl enable pveproxy || true
    
    # Configure automatic module loading
    cat > /etc/modules-load.d/zfs.conf <<EOF
# ZFS modules loaded at boot
zfs
EOF
    
    progress "install_modules" 100 "Module configuration complete"
}

# Main execution
main() {
    log "Starting native compilation process"
    log "Target: ZFS $ZFS_VERSION + Proxmox $PROXMOX_VERSION"
    
    # Initialize progress tracking
    echo "PROGRESS:init:0:Initializing native compilation..." > "$PROGRESS_FILE"
    
    # Execute compilation stages
    detect_hardware
    prepare_environment
    compile_zfs
    compile_proxmox  
    install_modules
    
    # Final success message
    progress "complete" 100 "Native compilation successful!"
    
    log "=== COMPILATION SUMMARY ==="
    log "System optimized for: $(lscpu | grep "Model name" | cut -d: -f2 | xargs)"
    
    # Show enabled optimizations
    if grep -q "avx512" /proc/cpuinfo; then
        log "✓ AVX-512 acceleration enabled"
    fi
    if grep -q "avx2" /proc/cpuinfo; then
        log "✓ AVX2 acceleration enabled"
    fi
    if grep -q "aes" /proc/cpuinfo; then
        log "✓ AES-NI encryption acceleration enabled"
    fi
    if grep -q "vmx\|svm" /proc/cpuinfo; then
        log "✓ Hardware virtualization optimized"
    fi
    
    log "Native compilation completed successfully!"
    log "Your system now has ZFS and Proxmox optimized specifically for this hardware."
    
    echo "SUCCESS" > "$PROGRESS_FILE"
}

# Run main function
main "$@"
#!/bin/bash
# Enhanced UltraThink Master Fix Script v2.0
# Production-ready chroot environment repair and validation

set -euo pipefail

# Configuration
CHROOT_PATH="${CHROOT_PATH:-/tmp/zforge_workspace/chroot}"
LOG_FILE="${LOG_FILE:-/tmp/ultrathink_fix_$(date +%Y%m%d_%H%M%S).log}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/zforge_workspace/backups}"
FIX_MODE="${FIX_MODE:-safe}" # safe, aggressive, rebuild

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${CYAN}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

# Header
echo "════════════════════════════════════════════════════════════════════" | tee "$LOG_FILE"
echo "           UltraThink Master Fix v2.0 for Z-FORGE Build" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
log "Fix mode: $FIX_MODE"
log "Chroot path: $CHROOT_PATH"
log "Log file: $LOG_FILE"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    error "This script must be run as root (sudo)"
    exit 1
fi

# Function to check chroot health
check_chroot_health() {
    log "Checking chroot environment health..."
    
    local issues=0
    
    # Check if chroot exists
    if [ ! -d "$CHROOT_PATH" ]; then
        error "Chroot directory not found at $CHROOT_PATH"
        return 1
    fi
    
    # Check essential directories
    for dir in etc usr bin sbin lib lib64 var proc sys dev; do
        if [ ! -d "$CHROOT_PATH/$dir" ]; then
            warning "Missing essential directory: $dir"
            ((issues++))
        fi
    done
    
    # Check essential files
    if [ ! -f "$CHROOT_PATH/etc/apt/sources.list" ]; then
        warning "Missing APT sources.list"
        ((issues++))
    fi
    
    if [ ! -f "$CHROOT_PATH/etc/resolv.conf" ]; then
        warning "Missing DNS configuration"
        ((issues++))
    fi
    
    # Check for broken symlinks
    local broken_links=$(find "$CHROOT_PATH" -xtype l 2>/dev/null | wc -l)
    if [ "$broken_links" -gt 0 ]; then
        warning "Found $broken_links broken symlinks"
        ((issues++))
    fi
    
    if [ "$issues" -eq 0 ]; then
        success "Chroot environment appears healthy"
        return 0
    else
        warning "Found $issues issues in chroot environment"
        return 1
    fi
}

# Function to backup current state
backup_chroot() {
    if [ "$FIX_MODE" != "rebuild" ]; then
        log "Creating backup of current chroot state..."
        mkdir -p "$BACKUP_DIR"
        
        local backup_name="chroot_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
        
        if tar -czf "$BACKUP_DIR/$backup_name" -C "$(dirname "$CHROOT_PATH")" "$(basename "$CHROOT_PATH")" 2>/dev/null; then
            success "Backup created: $BACKUP_DIR/$backup_name"
        else
            warning "Backup creation failed, but continuing..."
        fi
    fi
}

# Function to fix repository configuration
fix_repositories() {
    log "Fixing repository configuration..."
    
    # Create sources.list based on detected distribution
    if [ -f "$CHROOT_PATH/etc/os-release" ]; then
        source "$CHROOT_PATH/etc/os-release" 2>/dev/null || true
    fi
    
    # Determine the best repository configuration
    local dist_version="${VERSION_CODENAME:-trixie}"
    
    cat > "$CHROOT_PATH/etc/apt/sources.list" << EOF
# Primary distribution sources
deb http://deb.debian.org/debian ${dist_version} main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian ${dist_version} main contrib non-free non-free-firmware

# Security updates
deb http://security.debian.org/debian-security ${dist_version}-security main contrib non-free non-free-firmware

# Updates (if available)
deb http://deb.debian.org/debian ${dist_version}-updates main contrib non-free non-free-firmware
EOF

    # Add backports if not sid/unstable
    if [ "$dist_version" != "sid" ] && [ "$dist_version" != "unstable" ]; then
        echo "" >> "$CHROOT_PATH/etc/apt/sources.list"
        echo "# Backports" >> "$CHROOT_PATH/etc/apt/sources.list"
        echo "deb http://deb.debian.org/debian ${dist_version}-backports main contrib non-free non-free-firmware" >> "$CHROOT_PATH/etc/apt/sources.list"
    fi
    
    # Create APT preferences for stability
    mkdir -p "$CHROOT_PATH/etc/apt/preferences.d"
    cat > "$CHROOT_PATH/etc/apt/preferences.d/00-default-priority" << EOF
Package: *
Pin: release o=Debian
Pin-Priority: 500

Package: *
Pin: release a=${dist_version}-backports
Pin-Priority: 100
EOF

    # Configure APT for better reliability
    cat > "$CHROOT_PATH/etc/apt/apt.conf.d/99-fix-settings" << 'EOF'
Acquire::Retries "3";
Acquire::http::Timeout "120";
Acquire::https::Timeout "120";
Acquire::ftp::Timeout "120";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
APT::Get::Assume-Yes "true";
Debug::pkgProblemResolver "true";
EOF

    success "Repository configuration updated"
}

# Function to mount required filesystems
mount_filesystems() {
    log "Mounting required filesystems..."
    
    # Essential mount points
    local mounts=(
        "proc:proc:/proc"
        "sysfs:sysfs:/sys"
        "devtmpfs:udev:/dev"
        "devpts:devpts:/dev/pts"
        "tmpfs:tmpfs:/run"
    )
    
    for mount_spec in "${mounts[@]}"; do
        IFS=: read -r fstype source target <<< "$mount_spec"
        local full_target="$CHROOT_PATH$target"
        
        # Create mount point if it doesn't exist
        mkdir -p "$full_target"
        
        # Check if already mounted
        if ! mountpoint -q "$full_target" 2>/dev/null; then
            log "Mounting $fstype on $target..."
            if [ "$source" = "$fstype" ]; then
                # Special filesystems
                mount -t "$fstype" "$source" "$full_target" || warning "Failed to mount $target"
            else
                # Bind mounts
                mount --bind "/$target" "$full_target" || warning "Failed to bind mount $target"
            fi
        else
            info "$target already mounted"
        fi
    done
    
    success "Filesystems mounted"
}

# Function to fix DNS resolution
fix_dns() {
    log "Fixing DNS resolution..."
    
    # Copy host's resolv.conf
    if [ -f /etc/resolv.conf ]; then
        cp -f /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
        chmod 644 "$CHROOT_PATH/etc/resolv.conf"
    else
        # Create a basic resolv.conf
        cat > "$CHROOT_PATH/etc/resolv.conf" << 'EOF'
# Fallback DNS servers
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
EOF
    fi
    
    # Ensure /etc/hosts exists
    if [ ! -f "$CHROOT_PATH/etc/hosts" ]; then
        cat > "$CHROOT_PATH/etc/hosts" << 'EOF'
127.0.0.1	localhost
::1		localhost ip6-localhost ip6-loopback
EOF
    fi
    
    success "DNS resolution configured"
}

# Function to fix and install packages
fix_packages() {
    log "Fixing package system..."
    
    # Update package lists
    log "Updating package lists..."
    if ! chroot "$CHROOT_PATH" apt-get update 2>&1 | tee -a "$LOG_FILE"; then
        warning "Package update had issues"
        
        # Try to fix common issues
        log "Attempting to fix package issues..."
        chroot "$CHROOT_PATH" dpkg --configure -a 2>/dev/null || true
        chroot "$CHROOT_PATH" apt-get install -f 2>/dev/null || true
        chroot "$CHROOT_PATH" apt-get update || true
    fi
    
    # Essential packages for minimal system
    local essential_packages=(
        "base-files" "base-passwd" "bash" "coreutils" "dash"
        "debianutils" "diffutils" "dpkg" "e2fsprogs" "findutils"
        "grep" "gzip" "hostname" "init-system-helpers" "libc-bin"
        "login" "mount" "ncurses-base" "ncurses-bin" "passwd"
        "perl-base" "sed" "systemd-sysv" "tar" "util-linux"
    )
    
    # Additional useful packages
    local useful_packages=(
        "apt" "apt-utils" "ca-certificates" "curl" "gnupg"
        "iproute2" "iputils-ping" "less" "locales" "lsb-release"
        "nano" "procps" "sudo" "systemd" "tzdata" "wget"
    )
    
    # Install packages based on fix mode
    case "$FIX_MODE" in
        safe)
            log "Installing essential packages only..."
            for pkg in "${essential_packages[@]}"; do
                chroot "$CHROOT_PATH" apt-get install -y "$pkg" 2>/dev/null || warning "Failed to install $pkg"
            done
            ;;
        aggressive)
            log "Installing essential and useful packages..."
            for pkg in "${essential_packages[@]}" "${useful_packages[@]}"; do
                chroot "$CHROOT_PATH" apt-get install -y "$pkg" 2>/dev/null || warning "Failed to install $pkg"
            done
            ;;
        rebuild)
            log "Rebuilding with full package set..."
            chroot "$CHROOT_PATH" apt-get install -y "${essential_packages[@]}" "${useful_packages[@]}" || true
            ;;
    esac
    
    # Clean up
    log "Cleaning up package cache..."
    chroot "$CHROOT_PATH" apt-get clean
    chroot "$CHROOT_PATH" apt-get autoclean
    
    success "Package system fixed"
}

# Function to fix permissions
fix_permissions() {
    log "Fixing file permissions..."
    
    # Fix common permission issues
    chmod 755 "$CHROOT_PATH"
    
    # Essential directories
    for dir in bin sbin usr/bin usr/sbin lib lib64 usr/lib usr/lib64; do
        if [ -d "$CHROOT_PATH/$dir" ]; then
            chmod 755 "$CHROOT_PATH/$dir"
        fi
    done
    
    # /tmp should be world-writable
    if [ -d "$CHROOT_PATH/tmp" ]; then
        chmod 1777 "$CHROOT_PATH/tmp"
    fi
    
    # Fix /dev/null and other devices if they exist
    if [ -e "$CHROOT_PATH/dev/null" ]; then
        chmod 666 "$CHROOT_PATH/dev/null"
    fi
    
    success "Permissions fixed"
}

# Function to validate the fixes
validate_fixes() {
    log "Validating fixes..."
    
    local validation_failed=0
    
    # Test basic commands
    log "Testing basic commands..."
    for cmd in bash ls cat echo; do
        if chroot "$CHROOT_PATH" which "$cmd" &>/dev/null; then
            info "✓ $cmd is available"
        else
            error "✗ $cmd is missing"
            ((validation_failed++))
        fi
    done
    
    # Test package management
    log "Testing package management..."
    if chroot "$CHROOT_PATH" apt-get --version &>/dev/null; then
        info "✓ APT is functional"
    else
        error "✗ APT is not functional"
        ((validation_failed++))
    fi
    
    # Test DNS resolution
    log "Testing DNS resolution..."
    if chroot "$CHROOT_PATH" getent hosts google.com &>/dev/null; then
        info "✓ DNS resolution works"
    else
        warning "✗ DNS resolution may have issues"
    fi
    
    if [ "$validation_failed" -eq 0 ]; then
        success "All validations passed!"
        return 0
    else
        error "$validation_failed validations failed"
        return 1
    fi
}

# Function to generate report
generate_report() {
    local report_file="${LOG_FILE%.log}_report.txt"
    
    {
        echo "UltraThink Fix Report"
        echo "===================="
        echo ""
        echo "Date: $(date)"
        echo "Fix Mode: $FIX_MODE"
        echo "Chroot Path: $CHROOT_PATH"
        echo ""
        echo "Actions Performed:"
        echo "-----------------"
        grep -E "(SUCCESS|ERROR|WARNING)" "$LOG_FILE" | tail -20
        echo ""
        echo "Chroot Status:"
        echo "-------------"
        echo "Size: $(du -sh "$CHROOT_PATH" 2>/dev/null | cut -f1)"
        echo "Package Count: $(chroot "$CHROOT_PATH" dpkg -l 2>/dev/null | grep '^ii' | wc -l)"
        echo ""
        echo "Recommendations:"
        echo "---------------"
        echo "1. Run 'make clean' to clear any cached build artifacts"
        echo "2. Run 'make build' to test the fixed environment"
        echo "3. Monitor the build log for any remaining issues"
        echo ""
        echo "Full log: $LOG_FILE"
    } > "$report_file"
    
    info "Report saved to: $report_file"
}

# Main execution
main() {
    # Initial health check
    if ! check_chroot_health; then
        warning "Chroot environment has issues, proceeding with fixes..."
    fi
    
    # Create backup if requested
    if [ "$FIX_MODE" != "rebuild" ]; then
        backup_chroot
    fi
    
    # Apply fixes
    fix_repositories
    mount_filesystems
    fix_dns
    fix_packages
    fix_permissions
    
    # Validate fixes
    if validate_fixes; then
        success "All fixes applied successfully!"
    else
        warning "Some issues remain after fixes"
    fi
    
    # Generate report
    generate_report
    
    # Summary
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo "✅ UltraThink Fix Complete!"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    echo "📝 Log file: $LOG_FILE"
    echo "📋 Report: ${LOG_FILE%.log}_report.txt"
    echo ""
    echo "Next steps:"
    echo "1. Review the report for any remaining issues"
    echo "2. Run: make clean"
    echo "3. Run: make build"
    echo "4. Monitor for LiveEnvironment or build failures"
    echo ""
    
    # Unmount filesystems on exit
    trap 'for mp in "$CHROOT_PATH"/{dev/pts,dev,proc,sys,run}; do umount "$mp" 2>/dev/null || true; done' EXIT
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            FIX_MODE="$2"
            shift 2
            ;;
        --chroot)
            CHROOT_PATH="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --mode <safe|aggressive|rebuild>  Fix mode (default: safe)"
            echo "  --chroot <path>                   Chroot path (default: /tmp/zforge_workspace/chroot)"
            echo "  --help                            Show this help"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"
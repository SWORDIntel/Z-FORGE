#!/bin/bash
# Complete the debootstrap installation with missing Z-FORGE packages

set -e

WORKSPACE="/tmp/zforge_workspace"
CHROOT_PATH="$WORKSPACE/chroot"

echo "=== Completing Z-FORGE Package Installation ==="
echo "Adding missing packages to existing debootstrap installation"

# Check if debootstrap exists
if [ ! -d "$CHROOT_PATH" ] || [ ! -f "$CHROOT_PATH/bin/bash" ]; then
    echo "Error: No existing debootstrap installation found"
    echo "Run ./fix_debootstrap_tether.sh first"
    exit 1
fi

# Mount chroot filesystems
mount_chroot() {
    echo "1. Mounting chroot filesystems..."
    
    # Copy current DNS config
    sudo cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"
    
    # Mount if not already mounted
    if ! mountpoint -q "$CHROOT_PATH/proc" 2>/dev/null; then
        sudo mount -t proc proc "$CHROOT_PATH/proc"
        echo "   ✓ Mounted /proc"
    fi
    
    if ! mountpoint -q "$CHROOT_PATH/sys" 2>/dev/null; then
        sudo mount -t sysfs sysfs "$CHROOT_PATH/sys"
        echo "   ✓ Mounted /sys"
    fi
    
    if ! mountpoint -q "$CHROOT_PATH/dev" 2>/dev/null; then
        sudo mount --bind /dev "$CHROOT_PATH/dev"
        echo "   ✓ Mounted /dev"
    fi
    
    if ! mountpoint -q "$CHROOT_PATH/dev/pts" 2>/dev/null; then
        sudo mount -t devpts devpts "$CHROOT_PATH/dev/pts"
        echo "   ✓ Mounted /dev/pts"
    fi
}

# Update package lists
update_packages() {
    echo "2. Updating package lists..."
    
    # Configure APT for better reliability
    sudo tee "$CHROOT_PATH/etc/apt/apt.conf.d/99-zforge-complete" > /dev/null << 'EOF'
APT::Get::Assume-Yes "true";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
Acquire::Retries "3";
Acquire::http::Timeout "30";
EOF
    
    if sudo chroot "$CHROOT_PATH" apt-get update; then
        echo "   ✓ Package lists updated"
    else
        echo "   ✗ Package update failed"
        return 1
    fi
}

# Install the complete Z-FORGE package set
install_complete_packages() {
    echo "3. Installing complete Z-FORGE package set..."
    
    # These are the packages from the original debootstrap command
    local original_packages=(
        "locales"
        "linux-base" 
        "sudo"
        "bash-completion"
        "apt-transport-https"
        "ca-certificates"
        "curl"
        "wget"
        "gnupg"
        "gpgv"
    )
    
    # Additional packages that Z-FORGE modules might need
    local additional_packages=(
        "build-essential"     # For compiling (ZFS build, etc.)
        "python3"            # For Python modules
        "python3-pip"        # Package management
        "git"                # Version control
        "rsync"              # File synchronization
        "lsb-release"        # System identification
        "software-properties-common"  # Repository management
        "dirmngr"            # Key management
        "file"               # File type detection
        "less"               # Pager
        "vim-tiny"           # Text editor
        "nano"               # Alternative editor
        "net-tools"          # Network utilities
        "iputils-ping"       # Ping utility
        "iproute2"           # Network configuration
        "systemd"            # Service management
        "systemd-sysv"       # SysV compatibility
        "udev"               # Device management
        "kmod"               # Kernel module utilities
        "procps"             # Process utilities
        "psmisc"             # Process utilities
        "lsof"               # Open files utility
        "strace"             # System call tracer (debugging)
        "tcpdump"            # Network debugging
        "openssh-client"     # SSH client
        "tar"                # Archive utility
        "gzip"               # Compression
        "bzip2"              # Compression
        "xz-utils"           # Compression
        "unzip"              # Archive utility
        "zip"                # Archive utility
        "patch"              # Patch utility
        "diffutils"          # Diff utilities
        "findutils"          # Find utilities
        "grep"               # Text search
        "sed"                # Stream editor
        "gawk"               # Text processing
        "make"               # Build utility
        "pkg-config"         # Package configuration
        "autoconf"           # Build configuration
        "automake"           # Build automation
        "libtool"            # Library tools
        "flex"               # Lexical analyzer
        "bison"              # Parser generator
        "bc"                 # Calculator
        "dc"                 # Calculator
        "ed"                 # Line editor
        "hexdump"            # Hex dump utility
        "xxd"                # Hex dump utility
        "tree"               # Directory tree display
        "htop"               # Process monitor
        "iotop"              # I/O monitor
        "screen"             # Terminal multiplexer
        "tmux"               # Terminal multiplexer
        "parted"             # Partition editor
        "fdisk"              # Partition editor
        "gdisk"              # GPT partition editor
        "dosfstools"         # FAT filesystem tools
        "e2fsprogs"          # ext2/3/4 tools
        "btrfs-progs"        # Btrfs tools
        "xfsprogs"           # XFS tools
        "ntfs-3g"            # NTFS support
        "lvm2"               # Logical volume management
        "mdadm"              # Software RAID
        "cryptsetup"         # Disk encryption
        "smartmontools"      # Disk monitoring
        "hdparm"             # Disk utilities
        "sdparm"             # SCSI disk utilities
        "nvme-cli"           # NVMe utilities
        "pciutils"           # PCI utilities
        "usbutils"           # USB utilities
        "dmidecode"          # Hardware information
        "lshw"               # Hardware information
        "hwinfo"             # Hardware information
        "ethtool"            # Network interface utilities
        "wireless-tools"     # Wireless utilities
        "wpasupplicant"      # WiFi authentication
        "bridge-utils"       # Network bridging
        "vlan"               # VLAN utilities
        "iptables"           # Firewall
        "nftables"           # Modern firewall
        "ebtables"           # Ethernet bridge tables
        "tcpdump"            # Network packet capture
        "wireshark-common"   # Network analysis
        "nmap"               # Network scanning
        "netcat-openbsd"     # Network utility
        "socat"              # Network utility
        "telnet"             # Remote access
        "ftp"                # File transfer
        "lftp"               # Advanced FTP
        "rsync"              # File synchronization
        "scp"                # Secure copy
        "sftp"               # Secure FTP
        "nfs-common"         # NFS support
        "cifs-utils"         # SMB/CIFS support
        "samba-common"       # Samba support
        "acl"                # Access control lists
        "attr"               # Extended attributes
        "quota"              # Disk quotas
        "policycoreutils"    # SELinux utilities
        "apparmor-utils"     # AppArmor utilities
        "fail2ban"           # Intrusion prevention
        "logrotate"          # Log rotation
        "rsyslog"            # System logging
        "cron"               # Job scheduler
        "anacron"            # Anacron scheduler
        "at"                 # Job scheduler
        "ntp"                # Time synchronization
        "chrony"             # Time synchronization
        "tzdata"             # Timezone data
        "locales-all"        # All locales
        "manpages"           # Manual pages
        "manpages-dev"       # Development manual pages
        "info"               # Info documents
        "man-db"             # Manual page database
        "whatis"             # Manual page database
        "doc-base"           # Documentation base
    )
    
    echo "   Installing in groups to minimize failure impact..."
    echo "   This will take several minutes and download ~400-500MB"
    
    # Install original packages first (should already be there, but ensure)
    echo "   Group 1: Original debootstrap packages..."
    if sudo chroot "$CHROOT_PATH" apt-get install -y "${original_packages[@]}"; then
        echo "   ✓ Original packages confirmed"
    else
        echo "   ⚠ Some original packages failed"
    fi
    
    # Install additional packages in smaller groups
    local group_size=10
    local current_group=()
    local group_num=2
    
    for package in "${additional_packages[@]}"; do
        current_group+=("$package")
        
        if [ ${#current_group[@]} -eq $group_size ]; then
            echo "   Group $group_num: Installing ${current_group[*]}"
            if sudo chroot "$CHROOT_PATH" apt-get install -y "${current_group[@]}"; then
                echo "   ✓ Group $group_num successful"
            else
                echo "   ⚠ Group $group_num had failures (continuing)"
            fi
            current_group=()
            group_num=$((group_num + 1))
            
            # Small delay to be nice to the connection
            sleep 2
        fi
    done
    
    # Install remaining packages
    if [ ${#current_group[@]} -gt 0 ]; then
        echo "   Final group: Installing ${current_group[*]}"
        if sudo chroot "$CHROOT_PATH" apt-get install -y "${current_group[@]}"; then
            echo "   ✓ Final group successful"
        else
            echo "   ⚠ Final group had failures"
        fi
    fi
}

# Clean up and verify
cleanup_and_verify() {
    echo "4. Cleaning up and verifying..."
    
    # Clean package cache to save space
    sudo chroot "$CHROOT_PATH" apt-get clean
    
    # Unmount filesystems
    sudo umount "$CHROOT_PATH"/{dev/pts,dev,sys,proc} 2>/dev/null || true
    
    # Check final size and key files
    local final_size=$(du -sh "$CHROOT_PATH" 2>/dev/null | cut -f1 || echo "Unknown")
    echo "   Final installation size: $final_size"
    
    # Verify key Z-FORGE requirements
    local required_commands=(
        "/usr/bin/python3"
        "/usr/bin/git"
        "/usr/bin/make"
        "/usr/bin/gcc"
        "/sbin/fdisk"
        "/usr/bin/curl"
        "/usr/bin/wget"
    )
    
    local missing=0
    for cmd in "${required_commands[@]}"; do
        if [ -f "$CHROOT_PATH$cmd" ]; then
            echo "   ✓ Found: $cmd"
        else
            echo "   ✗ Missing: $cmd"
            missing=$((missing + 1))
        fi
    done
    
    if [ $missing -eq 0 ]; then
        echo "   ✓ All critical tools present"
        return 0
    else
        echo "   ⚠ $missing tools missing (may still work)"
        return 1
    fi
}

# Main execution
main() {
    echo "Completing Z-FORGE package installation"
    echo "This adds the full package set needed for Z-FORGE modules"
    echo
    
    mount_chroot
    
    if update_packages; then
        install_complete_packages
        
        if cleanup_and_verify; then
            echo
            echo "=== Package Installation Complete ==="
            echo "Full Z-FORGE package set installed"
            echo "Ready to run Z-FORGE build:"
            echo "sudo python3 builder/z-forge.py --build-spec build_spec.yml"
        else
            echo
            echo "=== Installation Mostly Complete ==="
            echo "Most packages installed, some may be missing"
            echo "Try running Z-FORGE build anyway"
        fi
    else
        echo
        echo "=== Update Failed ==="
        echo "Cannot update package lists"
        echo "Check network connectivity"
    fi
}

# Run main function
main "$@"
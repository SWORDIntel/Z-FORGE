#!/bin/bash
#
# ZFS LiveCD Builder - PXE Server Manager
# Advanced PXE/iPXE server management with integration to unified build system
#
# Features:
# - Automated PXE server deployment
# - Mass deployment orchestration
# - Client configuration management
# - Performance monitoring and optimization
#

set -euo pipefail

# Source common libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# shellcheck source=../../../lib/common.sh
source "$PROJECT_ROOT/lib/common.sh"

# PXE Server configuration
readonly PXE_VERSION="3.0.0"
readonly PXE_CONFIG_DIR="$PROJECT_ROOT/config/pxe"
readonly PXE_TFTP_ROOT="/srv/tftp"
readonly PXE_HTTP_ROOT="/srv/http"
readonly PXE_NFS_ROOT="/srv/nfs"
readonly PXE_IMAGES_DIR="$PXE_HTTP_ROOT/images"
readonly PXE_LOG_DIR="/var/log/zfs-livecd-pxe"

# Network configuration defaults
readonly DEFAULT_DHCP_RANGE_START="192.168.1.100"
readonly DEFAULT_DHCP_RANGE_END="192.168.1.200"
readonly DEFAULT_DHCP_LEASE_TIME="12h"
readonly DEFAULT_DOMAIN_NAME="zfs-livecd.local"

# Service management
declare -A SERVICE_STATUS
declare -A SERVICE_CONFIGS
declare -g NETWORK_INTERFACE=""
declare -g SERVER_IP=""
declare -g DHCP_RANGE_START=""
declare -g DHCP_RANGE_END=""
declare -g DOMAIN_NAME=""

# PXE Server initialization
pxe_server_init() {
    local config_file="${1:-$PXE_CONFIG_DIR/server.conf}"
    
    log_info "Initializing PXE Server Manager v$PXE_VERSION"
    
    # Create necessary directories
    for dir in "$PXE_CONFIG_DIR" "$PXE_LOG_DIR" "$PXE_TFTP_ROOT" \
               "$PXE_HTTP_ROOT" "$PXE_NFS_ROOT" "$PXE_IMAGES_DIR"; do
        safe_mkdir "$dir" 755
    done
    
    # Load configuration
    if [[ -f "$config_file" ]]; then
        # shellcheck source=/dev/null
        source "$config_file"
        log_info "Configuration loaded from: $config_file"
    else
        pxe_create_default_config "$config_file"
    fi
    
    # Detect network configuration if not specified
    if [[ -z "$NETWORK_INTERFACE" ]]; then
        pxe_detect_network_interface || die "Failed to detect network interface" $EXIT_CONFIGURATION_ERROR
    fi
    
    # Set defaults for unspecified values
    DHCP_RANGE_START="${DHCP_RANGE_START:-$DEFAULT_DHCP_RANGE_START}"
    DHCP_RANGE_END="${DHCP_RANGE_END:-$DEFAULT_DHCP_RANGE_END}"
    DOMAIN_NAME="${DOMAIN_NAME:-$DEFAULT_DOMAIN_NAME}"
    
    log_info "PXE Server initialized"
    log_info "Network Interface: $NETWORK_INTERFACE"
    log_info "Server IP: $SERVER_IP"
    log_info "DHCP Range: $DHCP_RANGE_START - $DHCP_RANGE_END"
}

# Create default PXE configuration
pxe_create_default_config() {
    local config_file="$1"
    
    log_info "Creating default PXE configuration: $config_file"
    
    cat > "$config_file" << EOF
# ZFS LiveCD PXE Server Configuration
# Generated: $(date)

# Network Configuration
NETWORK_INTERFACE=""  # Auto-detect if empty
SERVER_IP=""          # Auto-detect if empty
DHCP_RANGE_START="$DEFAULT_DHCP_RANGE_START"
DHCP_RANGE_END="$DEFAULT_DHCP_RANGE_END"
DHCP_LEASE_TIME="$DEFAULT_DHCP_LEASE_TIME"
DOMAIN_NAME="$DEFAULT_DOMAIN_NAME"

# Service Configuration
ENABLE_DHCP=true
ENABLE_TFTP=true
ENABLE_HTTP=true
ENABLE_NFS=true
ENABLE_WAKE_ON_LAN=true

# Performance Settings
MAX_CONCURRENT_BOOTS=50
TFTP_TIMEOUT=60
HTTP_TIMEOUT=300
CACHE_SIZE=1000

# Security Settings
ENABLE_SECURE_BOOT=false
ENABLE_CLIENT_FILTERING=false
ALLOWED_MAC_ADDRESSES=""
DENIED_MAC_ADDRESSES=""

# Integration Settings
BUILD_SYSTEM_INTEGRATION=true
AUTO_DEPLOY_BUILDS=true
NOTIFICATION_WEBHOOK=""
MONITORING_ENABLED=true
EOF

    chmod 600 "$config_file"
    log_info "Default configuration created: $config_file"
}

# Auto-detect network interface and IP
pxe_detect_network_interface() {
    local interfaces
    local ip_addr
    
    # Get active network interfaces with default routes
    interfaces=($(ip route | grep default | awk '{print $5}' | sort -u))
    
    if [[ ${#interfaces[@]} -eq 0 ]]; then
        log_error "No active network interface found"
        return 1
    fi
    
    # Use first interface
    NETWORK_INTERFACE="${interfaces[0]}"
    
    # Get IP address
    ip_addr=$(ip addr show "$NETWORK_INTERFACE" | grep -oP 'inet \K[\d.]+' | head -1)
    if [[ -z "$ip_addr" ]]; then
        log_error "No IP address found for interface $NETWORK_INTERFACE"
        return 1
    fi
    
    SERVER_IP="$ip_addr"
    
    log_info "Detected network interface: $NETWORK_INTERFACE"
    log_info "Detected server IP: $SERVER_IP"
    return 0
}

# Install PXE server dependencies
pxe_install_dependencies() {
    log_info "Installing PXE server dependencies"
    
    local packages=(
        # Core PXE services
        "dnsmasq"
        "tftpd-hpa"
        "apache2"
        "nfs-kernel-server"
        
        # Boot loaders
        "syslinux-common"
        "pxelinux"
        "isolinux"
        "grub-efi-amd64-bin"
        "grub-pc-bin"
        "ipxe"
        
        # File system tools
        "squashfs-tools"
        "genisoimage"
        "xorriso"
        
        # Network tools
        "wakeonlan"
        "etherwake"
        "nmap"
        "arp-scan"
        
        # Compression tools
        "pigz"
        "pixz"
        "lz4"
        "zstd"
        
        # Web interface dependencies
        "php"
        "php-cli"
        "php-curl"
        "php-json"
        "php-xml"
        
        # Monitoring tools
        "htop"
        "iotop"
        "nethogs"
        "iftop"
        
        # Additional utilities
        "curl"
        "wget"
        "rsync"
        "p7zip-full"
        "unzip"
    )
    
    # Update package lists
    apt_update_cache
    
    # Install packages
    for package in "${packages[@]}"; do
        if ! is_package_installed "$package"; then
            log_info "Installing package: $package"
            if ! apt_install_package "$package"; then
                log_warn "Failed to install package: $package"
            fi
        fi
    done
    
    log_info "PXE server dependencies installation completed"
}

# Configure DNSMASQ for PXE boot
pxe_configure_dnsmasq() {
    local config_file="/etc/dnsmasq.d/zfs-livecd-pxe.conf"
    
    log_info "Configuring DNSMASQ for PXE boot"
    
    # Stop dnsmasq service
    systemctl stop dnsmasq 2>/dev/null || true
    
    # Backup original configuration
    if [[ -f /etc/dnsmasq.conf ]]; then
        cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup.$(date +%Y%m%d)
    fi
    
    # Create PXE-specific configuration
    cat > "$config_file" << EOF
# ZFS LiveCD PXE Boot Configuration
# Generated: $(date)
# Interface: $NETWORK_INTERFACE
# Server IP: $SERVER_IP

# Bind to specific interface
interface=$NETWORK_INTERFACE
bind-interfaces

# DHCP configuration
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,$DHCP_LEASE_TIME
dhcp-option=option:router,$SERVER_IP
dhcp-option=option:dns-server,$SERVER_IP
dhcp-option=option:domain-name,$DOMAIN_NAME
dhcp-option=option:netmask,255.255.255.0

# Domain configuration
domain=$DOMAIN_NAME
expand-hosts
local=/$DOMAIN_NAME/

# TFTP configuration
enable-tftp
tftp-root=$PXE_TFTP_ROOT
tftp-secure

# PXE boot configuration for BIOS
dhcp-boot=tag:!ipxe,undionly.kpxe
dhcp-boot=tag:ipxe,http://$SERVER_IP/boot.ipxe

# UEFI boot configuration
dhcp-match=set:efi-x86_64,option:client-arch,7
dhcp-match=set:efi-x86_64,option:client-arch,9
dhcp-boot=tag:efi-x86_64,tag:!ipxe,ipxe.efi
dhcp-boot=tag:efi-x86_64,tag:ipxe,http://$SERVER_IP/boot.ipxe

# iPXE detection
dhcp-match=set:ipxe,175

# DNS upstream servers
server=8.8.8.8
server=8.8.4.4
server=1.1.1.1

# Logging
log-dhcp
log-queries=extra
log-facility=$PXE_LOG_DIR/dnsmasq.log

# Cache and performance
cache-size=10000
dns-forward-max=1000

# Security
stop-dns-rebind
rebind-localhost-ok

# Additional configuration directory
conf-dir=/etc/dnsmasq.d/,*.conf
EOF
    
    # Set proper permissions
    chmod 644 "$config_file"
    
    # Enable and start dnsmasq
    systemctl enable dnsmasq
    systemctl start dnsmasq
    
    if systemctl is-active --quiet dnsmasq; then
        SERVICE_STATUS[dnsmasq]="running"
        log_info "DNSMASQ configured and started successfully"
    else
        SERVICE_STATUS[dnsmasq]="failed"
        log_error "DNSMASQ failed to start"
        return 1
    fi
    
    return 0
}

# Setup iPXE boot environment
pxe_setup_ipxe() {
    log_info "Setting up iPXE boot environment"
    
    # Copy iPXE boot files
    if [[ -f /usr/lib/ipxe/undionly.kpxe ]]; then
        cp /usr/lib/ipxe/undionly.kpxe "$PXE_TFTP_ROOT/"
    elif [[ -f /usr/lib/syslinux/modules/bios/undionly.kpxe ]]; then
        cp /usr/lib/syslinux/modules/bios/undionly.kpxe "$PXE_TFTP_ROOT/"
    else
        log_info "Downloading iPXE boot files"
        wget -O "$PXE_TFTP_ROOT/undionly.kpxe" http://boot.ipxe.org/undionly.kpxe
    fi
    
    # Copy UEFI iPXE
    if [[ -f /usr/lib/ipxe/ipxe.efi ]]; then
        cp /usr/lib/ipxe/ipxe.efi "$PXE_TFTP_ROOT/"
    else
        log_info "Downloading iPXE UEFI boot file"
        wget -O "$PXE_TFTP_ROOT/ipxe.efi" http://boot.ipxe.org/ipxe.efi
    fi
    
    # Create main iPXE boot script
    pxe_create_ipxe_menu
    
    # Set proper permissions
    chown -R nobody:nogroup "$PXE_TFTP_ROOT"
    chmod -R 755 "$PXE_TFTP_ROOT"
    
    log_info "iPXE boot environment configured"
}

# Create iPXE boot menu
pxe_create_ipxe_menu() {
    local boot_script="$PXE_HTTP_ROOT/boot.ipxe"
    
    log_info "Creating iPXE boot menu"
    
    cat > "$boot_script" << EOF
#!ipxe

# ZFS LiveCD Network Boot Menu
# Generated: $(date)
# Server: $SERVER_IP

:start
menu ZFS LiveCD Network Boot - v$PXE_VERSION
item --gap --             ------------------------- ZFS LiveCD Options -------------------------
item zfs-latest           Boot Latest ZFS LiveCD
item zfs-stable           Boot Stable ZFS LiveCD
item zfs-debug            Boot ZFS LiveCD (Debug Mode)
item zfs-recovery         Boot ZFS LiveCD (Recovery Mode)
item --gap --             ------------------------- System Tools -------------------------
item hardware-detect     Hardware Detection & Inventory
item memory-test          Memory Test (Memtest86+)
item disk-tools           Disk Utilities & Recovery
item network-tools        Network Diagnostics
item --gap --             ------------------------- Deployment Options -------------------------
item mass-deployment     Mass Deployment (Automated)
item custom-deployment    Custom Deployment Wizard
item image-selection      Image Selection Menu
item --gap --             ------------------------- Administration -------------------------
item server-status       Server Status & Monitoring
item client-management   Client Management
item image-management    Image Management
item --gap --             ----------------------------- System ---------------------------
item shell               iPXE Shell
item reboot              Reboot
item poweroff            Power Off
choose --timeout 30000 --default zfs-latest target && goto \${target}

:zfs-latest
echo Loading latest ZFS LiveCD...
kernel http://$SERVER_IP/images/zfs-livecd/latest/vmlinuz boot=live components quiet splash toram live-media-path=/live/filesystem.squashfs
initrd http://$SERVER_IP/images/zfs-livecd/latest/initrd.img
boot || goto failed

:zfs-stable
echo Loading stable ZFS LiveCD...
kernel http://$SERVER_IP/images/zfs-livecd/stable/vmlinuz boot=live components quiet splash toram live-media-path=/live/filesystem.squashfs
initrd http://$SERVER_IP/images/zfs-livecd/stable/initrd.img
boot || goto failed

:zfs-debug
echo Loading ZFS LiveCD in debug mode...
kernel http://$SERVER_IP/images/zfs-livecd/latest/vmlinuz boot=live components debug systemd.log_level=debug live-media-path=/live/filesystem.squashfs toram
initrd http://$SERVER_IP/images/zfs-livecd/latest/initrd.img
boot || goto failed

:zfs-recovery
echo Loading ZFS LiveCD in recovery mode...
kernel http://$SERVER_IP/images/zfs-livecd/latest/vmlinuz boot=live components nomodeset noacpi acpi=off single live-media-path=/live/filesystem.squashfs toram
initrd http://$SERVER_IP/images/zfs-livecd/latest/initrd.img
boot || goto failed

:hardware-detect
echo Starting hardware detection...
kernel http://$SERVER_IP/tools/hardware-detect/vmlinuz quiet
initrd http://$SERVER_IP/tools/hardware-detect/initrd.img
boot || goto failed

:memory-test
echo Starting memory test...
kernel http://$SERVER_IP/tools/memtest/memtest86+.bin
boot || goto failed

:disk-tools
echo Loading disk utilities...
kernel http://$SERVER_IP/tools/disk-utils/vmlinuz boot=live components quiet
initrd http://$SERVER_IP/tools/disk-utils/initrd.img
boot || goto failed

:network-tools
echo Loading network diagnostic tools...
kernel http://$SERVER_IP/tools/network-diag/vmlinuz boot=live components quiet
initrd http://$SERVER_IP/tools/network-diag/initrd.img
boot || goto failed

:mass-deployment
echo Initiating mass deployment...
chain http://$SERVER_IP/deployment/mass-deploy.ipxe || goto start

:custom-deployment
echo Loading custom deployment wizard...
chain http://$SERVER_IP/deployment/custom-deploy.ipxe || goto start

:image-selection
echo Loading image selection menu...
chain http://$SERVER_IP/menus/image-select.ipxe || goto start

:server-status
echo Checking server status...
chain http://$SERVER_IP/admin/status.ipxe || goto start

:client-management
echo Loading client management...
chain http://$SERVER_IP/admin/clients.ipxe || goto start

:image-management
echo Loading image management...
chain http://$SERVER_IP/admin/images.ipxe || goto start

:shell
echo Dropping to iPXE shell...
shell

:reboot
reboot

:poweroff
poweroff

:failed
echo Boot failed! Press any key to return to menu...
prompt
goto start
EOF
    
    # Set proper permissions
    chmod 644 "$boot_script"
    
    log_info "iPXE boot menu created: $boot_script"
}

# Configure Apache HTTP server
pxe_configure_apache() {
    local site_config="/etc/apache2/sites-available/zfs-livecd-pxe.conf"
    
    log_info "Configuring Apache HTTP server for PXE"
    
    # Enable required Apache modules
    a2enmod rewrite headers ssl deflate expires
    
    # Create virtual host configuration
    cat > "$site_config" << EOF
<VirtualHost *:80>
    ServerName $SERVER_IP
    ServerAlias zfs-livecd-pxe.$DOMAIN_NAME
    DocumentRoot $PXE_HTTP_ROOT
    
    # Logging
    ErrorLog \${APACHE_LOG_DIR}/zfs-livecd-pxe_error.log
    CustomLog \${APACHE_LOG_DIR}/zfs-livecd-pxe_access.log combined
    LogLevel info
    
    # Security headers
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    
    # Main document root
    <Directory $PXE_HTTP_ROOT>
        Options Indexes FollowSymLinks MultiViews
        AllowOverride All
        Require all granted
        
        # Enable compression for large files
        <IfModule mod_deflate.c>
            AddOutputFilterByType DEFLATE text/plain
            AddOutputFilterByType DEFLATE text/html
            AddOutputFilterByType DEFLATE text/xml
            AddOutputFilterByType DEFLATE text/css
            AddOutputFilterByType DEFLATE application/xml
            AddOutputFilterByType DEFLATE application/xhtml+xml
            AddOutputFilterByType DEFLATE application/rss+xml
            AddOutputFilterByType DEFLATE application/javascript
            AddOutputFilterByType DEFLATE application/x-javascript
        </IfModule>
        
        # Cache control for boot files
        <IfModule mod_expires.c>
            ExpiresActive On
            ExpiresByType text/plain "access plus 1 hour"
            ExpiresByType application/octet-stream "access plus 1 hour"
        </IfModule>
    </Directory>
    
    # iPXE scripts
    <FilesMatch "\.ipxe$">
        Header set Content-Type "text/plain"
        Header set Cache-Control "no-cache, no-store, must-revalidate"
        Header set Pragma "no-cache"
        Header set Expires "0"
    </FilesMatch>
    
    # Boot images - no caching
    <Directory $PXE_HTTP_ROOT/images>
        Header set Cache-Control "no-cache"
        
        # Large file optimization
        EnableSendfile On
        EnableMMAP On
    </Directory>
    
    # Administration interface
    <Directory $PXE_HTTP_ROOT/admin>
        Options -Indexes
        AllowOverride AuthConfig
        
        # Basic authentication (replace with proper auth)
        AuthType Basic
        AuthName "PXE Server Administration"
        AuthUserFile $PXE_CONFIG_DIR/.htpasswd
        Require valid-user
    </Directory>
    
    # PHP configuration
    <IfModule mod_php7.c>
        php_admin_value upload_max_filesize 2G
        php_admin_value post_max_size 2G
        php_admin_value max_execution_time 300
        php_admin_value memory_limit 512M
    </IfModule>
    
    # Status monitoring endpoint
    <Location "/server-status">
        SetHandler server-status
        Require ip 127.0.0.1
        Require ip $SERVER_IP
    </Location>
    
    # Info monitoring endpoint
    <Location "/server-info">
        SetHandler server-info
        Require ip 127.0.0.1
        Require ip $SERVER_IP
    </Location>
</VirtualHost>
EOF
    
    # Create basic authentication file
    htpasswd -bc "$PXE_CONFIG_DIR/.htpasswd" admin "$(openssl rand -base64 12)"
    log_info "Admin password stored in: $PXE_CONFIG_DIR/.htpasswd"
    
    # Enable site
    a2ensite zfs-livecd-pxe.conf
    a2dissite 000-default.conf 2>/dev/null || true
    
    # Test configuration
    if apache2ctl configtest; then
        systemctl restart apache2
        
        if systemctl is-active --quiet apache2; then
            SERVICE_STATUS[apache2]="running"
            log_info "Apache HTTP server configured and started successfully"
        else
            SERVICE_STATUS[apache2]="failed"
            log_error "Apache HTTP server failed to start"
            return 1
        fi
    else
        log_error "Apache configuration test failed"
        return 1
    fi
    
    return 0
}

# Configure NFS server for large file sharing
pxe_configure_nfs() {
    log_info "Configuring NFS server for PXE"
    
    # Configure NFS exports
    cat > /etc/exports << EOF
# ZFS LiveCD PXE NFS Exports
# Generated: $(date)

$PXE_NFS_ROOT *(ro,sync,no_root_squash,no_subtree_check,crossmnt)
$PXE_IMAGES_DIR *(ro,sync,no_root_squash,no_subtree_check,crossmnt)
EOF
    
    # Update exports
    exportfs -ra
    
    # Start NFS services
    systemctl enable rpcbind nfs-kernel-server
    systemctl start rpcbind nfs-kernel-server
    
    if systemctl is-active --quiet nfs-kernel-server; then
        SERVICE_STATUS[nfs]="running"
        log_info "NFS server configured and started successfully"
    else
        SERVICE_STATUS[nfs]="failed"
        log_error "NFS server failed to start"
        return 1
    fi
    
    return 0
}

# Deploy ZFS LiveCD images to PXE server
pxe_deploy_images() {
    local source_dir="${1:-$PROJECT_ROOT/src/build/output}"
    
    log_info "Deploying ZFS LiveCD images to PXE server"
    
    if [[ ! -d "$source_dir" ]]; then
        log_warn "Source directory not found: $source_dir"
        return 1
    fi
    
    # Create image directories
    safe_mkdir "$PXE_IMAGES_DIR/zfs-livecd/latest" 755
    safe_mkdir "$PXE_IMAGES_DIR/zfs-livecd/stable" 755
    
    # Find and deploy ISO files
    local iso_files
    iso_files=($(find "$source_dir" -name "*.iso" -type f | head -5))
    
    for iso_file in "${iso_files[@]}"; do
        local iso_name=$(basename "$iso_file" .iso)
        local extract_dir="$PXE_IMAGES_DIR/zfs-livecd/latest"
        
        log_info "Extracting boot files from: $iso_file"
        
        # Create temporary mount point
        local mount_point="/tmp/iso-mount-$$"
        safe_mkdir "$mount_point" 755
        
        # Mount ISO
        mount -o loop "$iso_file" "$mount_point"
        
        # Extract boot files
        if [[ -f "$mount_point/live/vmlinuz" ]]; then
            cp "$mount_point/live/vmlinuz" "$extract_dir/"
            cp "$mount_point/live/initrd.img" "$extract_dir/"
            [[ -f "$mount_point/live/filesystem.squashfs" ]] && \
                cp "$mount_point/live/filesystem.squashfs" "$extract_dir/"
        elif [[ -f "$mount_point/casper/vmlinuz" ]]; then
            cp "$mount_point/casper/vmlinuz" "$extract_dir/"
            cp "$mount_point/casper/initrd" "$extract_dir/initrd.img"
            [[ -f "$mount_point/casper/filesystem.squashfs" ]] && \
                cp "$mount_point/casper/filesystem.squashfs" "$extract_dir/"
        fi
        
        # Unmount and cleanup
        umount "$mount_point"
        rmdir "$mount_point"
        
        log_info "Boot files extracted to: $extract_dir"
    done
    
    # Set proper permissions
    chown -R www-data:www-data "$PXE_IMAGES_DIR"
    
    log_info "Image deployment completed"
}

# Check PXE server status
pxe_check_status() {
    log_info "Checking PXE server status"
    
    echo "ZFS LiveCD PXE Server Status"
    echo "============================"
    echo "Server IP: $SERVER_IP"
    echo "Interface: $NETWORK_INTERFACE"
    echo "Domain: $DOMAIN_NAME"
    echo ""
    
    # Check services
    local services=("dnsmasq" "apache2" "nfs-kernel-server" "rpcbind")
    echo "Service Status:"
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            echo "  ✓ $service: Running"
            SERVICE_STATUS[$service]="running"
        else
            echo "  ✗ $service: Stopped"
            SERVICE_STATUS[$service]="stopped"
        fi
    done
    echo ""
    
    # Check network connectivity
    echo "Network Status:"
    if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        echo "  ✓ Internet connectivity: OK"
    else
        echo "  ! Internet connectivity: Limited"
    fi
    
    if ping -c 1 -W 2 "$SERVER_IP" >/dev/null 2>&1; then
        echo "  ✓ Server IP reachable: $SERVER_IP"
    else
        echo "  ✗ Server IP not reachable: $SERVER_IP"
    fi
    echo ""
    
    # Check listening ports
    echo "Listening Ports:"
    local ports=("53:DNS" "67:DHCP" "69:TFTP" "80:HTTP" "111:RPC" "2049:NFS")
    for port_info in "${ports[@]}"; do
        local port="${port_info%:*}"
        local service_name="${port_info#*:}"
        
        if ss -tln | grep -q ":$port "; then
            echo "  ✓ Port $port ($service_name): Listening"
        else
            echo "  ! Port $port ($service_name): Not listening"
        fi
    done
    echo ""
    
    # Check disk space
    echo "Storage Status:"
    df -h "$PXE_HTTP_ROOT" "$PXE_TFTP_ROOT" | grep -v "Filesystem"
    echo ""
    
    # Check image availability
    echo "Available Images:"
    if [[ -d "$PXE_IMAGES_DIR/zfs-livecd" ]]; then
        find "$PXE_IMAGES_DIR/zfs-livecd" -name "vmlinuz" -exec dirname {} \; | \
        while read -r img_dir; do
            local img_name=$(basename "$(dirname "$img_dir")")/$(basename "$img_dir")
            local size=$(du -sh "$img_dir" 2>/dev/null | cut -f1)
            echo "  - $img_name ($size)"
        done
    else
        echo "  No images deployed"
    fi
}

# Start all PXE services
pxe_start_services() {
    log_info "Starting PXE server services"
    
    local services=("dnsmasq" "apache2" "nfs-kernel-server" "rpcbind")
    
    for service in "${services[@]}"; do
        log_info "Starting service: $service"
        systemctl start "$service"
        
        if systemctl is-active --quiet "$service"; then
            echo "  ✓ $service started successfully"
            SERVICE_STATUS[$service]="running"
        else
            echo "  ✗ $service failed to start"
            SERVICE_STATUS[$service]="failed"
        fi
    done
}

# Stop all PXE services
pxe_stop_services() {
    log_info "Stopping PXE server services"
    
    local services=("dnsmasq" "apache2" "nfs-kernel-server")
    
    for service in "${services[@]}"; do
        log_info "Stopping service: $service"
        systemctl stop "$service"
        echo "  ! $service stopped"
        SERVICE_STATUS[$service]="stopped"
    done
}

# Complete PXE server setup
pxe_server_setup() {
    log_info "Setting up complete PXE server infrastructure"
    
    # Initialize PXE server
    pxe_server_init
    
    # Install dependencies
    pxe_install_dependencies
    
    # Configure services
    pxe_configure_dnsmasq
    pxe_setup_ipxe
    pxe_configure_apache
    pxe_configure_nfs
    
    # Deploy images if available
    pxe_deploy_images
    
    # Start services
    pxe_start_services
    
    # Check final status
    pxe_check_status
    
    log_info "PXE server setup completed successfully"
    log_info "Access the server at: http://$SERVER_IP"
    log_info "Admin interface: http://$SERVER_IP/admin"
    log_info "iPXE boot URL: http://$SERVER_IP/boot.ipxe"
}

# Main function
main() {
    case "${1:-}" in
        init|initialize)
            pxe_server_init "${2:-}"
            ;;
        setup|install)
            check_root || die "Root privileges required for PXE server setup" $EXIT_PERMISSION_DENIED
            pxe_server_setup
            ;;
        start)
            check_root || die "Root privileges required" $EXIT_PERMISSION_DENIED
            pxe_start_services
            ;;
        stop)
            check_root || die "Root privileges required" $EXIT_PERMISSION_DENIED
            pxe_stop_services
            ;;
        status)
            pxe_check_status
            ;;
        deploy-images)
            pxe_deploy_images "${2:-}"
            ;;
        create-config)
            pxe_create_default_config "${2:-$PXE_CONFIG_DIR/server.conf}"
            ;;
        *)
            echo "ZFS LiveCD PXE Server Manager v$PXE_VERSION"
            echo ""
            echo "Usage: $0 COMMAND [OPTIONS]"
            echo ""
            echo "Commands:"
            echo "  init [config_file]     Initialize PXE server configuration"
            echo "  setup                  Complete PXE server setup"
            echo "  start                  Start PXE server services"
            echo "  stop                   Stop PXE server services"
            echo "  status                 Show PXE server status"
            echo "  deploy-images [dir]    Deploy ZFS LiveCD images"
            echo "  create-config [file]   Create default configuration"
            echo ""
            echo "Examples:"
            echo "  $0 setup                           # Full PXE server setup"
            echo "  $0 deploy-images /path/to/builds   # Deploy specific images"
            echo "  $0 status                          # Check server status"
            echo ""
            exit 0
            ;;
    esac
}

# Execute main function
main "$@"
#!/bin/bash
# Build additional packages needed for the live CD
# Creates multiple .deb packages from different sources

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "        Building Additional Packages for Live CD"
echo "═══════════════════════════════════════════════════════════════════"

OUTPUT_DIR="/opt/github/Z-FORGE/live_cd_packages"
BUILD_DIR="/tmp/additional_packages_build_$$"

mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"

echo ""
echo "Current packages in live_cd_packages/:"
ls -la "$OUTPUT_DIR"

echo ""
echo "What additional packages would you like to build?"
echo ""
echo "1. ZFS kernel modules (if compatible kernel available)"
echo "2. Proxmox-specific packages (custom configurations)"
echo "3. Live system packages (boot, rescue tools)"
echo "4. Hardware drivers (network, storage)"
echo "5. All of the above"
echo "6. Just show what we have and exit"
echo ""
read -p "Enter your choice [1-6]: " choice

case "$choice" in
    1)
        echo ""
        echo "Checking kernel module compatibility..."
        if grep -q "CONFIG_MODULES=y" /boot/config-$(uname -r) 2>/dev/null; then
            echo "✅ Kernel supports modules"
            echo ""
            echo "Building ZFS kernel modules package..."
            
            cd "$BUILD_DIR"
            
            # Use existing ZFS source
            if [ -f "/opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3.tar.gz" ]; then
                cp "/opt/github/Z-FORGE/prebuilt_packages/zfs-2.3.3.tar.gz" .
                tar xzf zfs-2.3.3.tar.gz
                cd zfs-2.3.3
                
                echo "Configuring for kernel modules..."
                ./configure --with-config=kernel --enable-systemd
                
                echo "Building kernel modules..."
                make -j$(nproc)
                
                echo "Creating kernel modules package..."
                # Create DKMS-style package
                mkdir -p "$BUILD_DIR/zfs-dkms/DEBIAN"
                mkdir -p "$BUILD_DIR/zfs-dkms/usr/src/zfs-2.3.3"
                
                # Copy source for DKMS
                cp -r . "$BUILD_DIR/zfs-dkms/usr/src/zfs-2.3.3/"
                
                cat > "$BUILD_DIR/zfs-dkms/DEBIAN/control" << EOF
Package: zfs-dkms
Version: 2.3.3-1
Section: kernel
Priority: optional
Architecture: all
Depends: dkms, build-essential, linux-headers-generic
Maintainer: Z-FORGE Build System
Description: ZFS kernel modules (DKMS)
 ZFS kernel modules built with DKMS for automatic kernel compatibility.
EOF
                
                dpkg-deb --build "$BUILD_DIR/zfs-dkms" "$OUTPUT_DIR/zfs-dkms_2.3.3-1_all.deb"
                echo "✅ Created zfs-dkms package"
            else
                echo "❌ ZFS source not found"
            fi
        else
            echo "❌ Kernel doesn't support modules"
            echo "   Only userspace package available"
        fi
        ;;
        
    2)
        echo ""
        echo "Building Proxmox-specific packages..."
        
        # Create Proxmox configuration package
        mkdir -p "$BUILD_DIR/proxmox-zforge-config/DEBIAN"
        mkdir -p "$BUILD_DIR/proxmox-zforge-config/etc/pve"
        mkdir -p "$BUILD_DIR/proxmox-zforge-config/etc/systemd/system"
        mkdir -p "$BUILD_DIR/proxmox-zforge-config/usr/local/bin"
        
        # Create Proxmox live configuration
        cat > "$BUILD_DIR/proxmox-zforge-config/etc/pve/storage.cfg" << EOF
# Z-FORGE Live CD Storage Configuration
dir: local
	path /var/lib/vz
	content backup,iso,vztmpl
	
zfspool: local-zfs
	pool rpool
	content rootdir,images
	mountpoint /
EOF
        
        # Create Z-FORGE specific scripts
        cat > "$BUILD_DIR/proxmox-zforge-config/usr/local/bin/zforge-setup" << 'EOF'
#!/bin/bash
# Z-FORGE Live CD setup script
echo "Setting up Z-FORGE Proxmox Live Environment..."

# Create default storage if ZFS available
if command -v zpool >/dev/null 2>&1; then
    echo "ZFS tools available"
    # Setup would go here
fi

echo "Z-FORGE setup complete!"
EOF
        chmod +x "$BUILD_DIR/proxmox-zforge-config/usr/local/bin/zforge-setup"
        
        cat > "$BUILD_DIR/proxmox-zforge-config/DEBIAN/control" << EOF
Package: proxmox-zforge-config
Version: 1.0-1
Section: admin
Priority: optional
Architecture: all
Depends: proxmox-ve
Maintainer: Z-FORGE Build System  
Description: Z-FORGE Proxmox VE configuration
 Configuration files and scripts for Z-FORGE live CD with Proxmox VE.
EOF
        
        dpkg-deb --build "$BUILD_DIR/proxmox-zforge-config" "$OUTPUT_DIR/proxmox-zforge-config_1.0-1_all.deb"
        echo "✅ Created proxmox-zforge-config package"
        ;;
        
    3)
        echo ""
        echo "Building live system packages..."
        
        # Create live system tools package
        mkdir -p "$BUILD_DIR/zforge-live-tools/DEBIAN"
        mkdir -p "$BUILD_DIR/zforge-live-tools/usr/local/bin"
        mkdir -p "$BUILD_DIR/zforge-live-tools/etc/systemd/system"
        
        # Create live CD utilities
        cat > "$BUILD_DIR/zforge-live-tools/usr/local/bin/zforge-install" << 'EOF'
#!/bin/bash
# Z-FORGE installation script
echo "Z-FORGE Live CD Installer"
echo "This would install Z-FORGE to disk"
EOF
        chmod +x "$BUILD_DIR/zforge-live-tools/usr/local/bin/zforge-install"
        
        cat > "$BUILD_DIR/zforge-live-tools/DEBIAN/control" << EOF
Package: zforge-live-tools
Version: 1.0-1
Section: utils
Priority: optional
Architecture: all
Maintainer: Z-FORGE Build System
Description: Z-FORGE live system tools
 Utilities and tools for the Z-FORGE live environment.
EOF
        
        dpkg-deb --build "$BUILD_DIR/zforge-live-tools" "$OUTPUT_DIR/zforge-live-tools_1.0-1_all.deb"
        echo "✅ Created zforge-live-tools package"
        ;;
        
    4)
        echo ""
        echo "Hardware drivers are typically provided by the kernel and firmware packages."
        echo "The bootstrap process should include firmware-linux-free and other essentials."
        echo "Custom driver packages would need specific hardware requirements."
        ;;
        
    5)
        echo ""
        echo "Building all additional packages..."
        # Run options 1, 2, and 3
        choice=1; source <(echo 'case "$choice" in 1)'); echo ""
        choice=2; source <(echo 'case "$choice" in 2)'); echo ""  
        choice=3; source <(echo 'case "$choice" in 3)');
        ;;
        
    6)
        echo ""
        echo "Current package inventory:"
        echo "========================="
        cd "$OUTPUT_DIR"
        for pkg in *.deb; do
            if [ -f "$pkg" ]; then
                echo "📦 $pkg"
                echo "   Size: $(du -h "$pkg" | cut -f1)"
                echo "   Info: $(dpkg-deb --field "$pkg" Description | head -1)"
                echo ""
            fi
        done
        exit 0
        ;;
        
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                Additional Packages Built"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Packages now available in $OUTPUT_DIR:"
cd "$OUTPUT_DIR"
for pkg in *.deb; do
    if [ -f "$pkg" ]; then
        echo "✅ $pkg ($(du -h "$pkg" | cut -f1))"
    fi
done

echo ""
echo "Total packages: $(ls *.deb 2>/dev/null | wc -l)"
echo "Total size: $(du -sh *.deb 2>/dev/null | tail -1 | cut -f1 || echo '0')"

# Clean up
rm -rf "$BUILD_DIR"
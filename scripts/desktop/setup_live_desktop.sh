#!/bin/bash
#
# Z-FORGE Live Desktop Setup Script
# Configures desktop environment for live ISO with Calamares launcher
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHROOT_PATH="${1:-}"

if [ -z "$CHROOT_PATH" ]; then
    echo "Usage: $0 <chroot_path>"
    exit 1
fi

if [ ! -d "$CHROOT_PATH" ]; then
    echo "Error: Chroot path does not exist: $CHROOT_PATH"
    exit 1
fi

echo "=== Z-FORGE Live Desktop Setup ==="
echo "Chroot: $CHROOT_PATH"

# Function to run commands in chroot
chroot_run() {
    chroot "$CHROOT_PATH" "$@"
}

# Function to copy files to chroot
copy_to_chroot() {
    local src="$1"
    local dest="$2"
    cp -r "$src" "$CHROOT_PATH/$dest"
}

# Detect which desktop environment to install
detect_desktop_environment() {
    # Check build spec or use minimal by default
    local desktop="${DESKTOP_ENVIRONMENT:-minimal}"
    echo "$desktop"
}

# Install minimal desktop environment
install_minimal_desktop() {
    echo "Installing minimal desktop environment..."
    
    # Install Xorg base
    chroot_run apt-get update
    chroot_run apt-get install -y --no-install-recommends \
        xorg \
        xinit \
        x11-xserver-utils \
        x11-utils
    
    # Install lightweight window manager (Openbox)
    chroot_run apt-get install -y --no-install-recommends \
        openbox \
        obconf \
        obmenu
    
    # Install display manager (LightDM)
    chroot_run apt-get install -y --no-install-recommends \
        lightdm \
        lightdm-gtk-greeter
    
    # Install essential GUI applications
    chroot_run apt-get install -y --no-install-recommends \
        xterm \
        pcmanfm \
        firefox-esr \
        network-manager-gnome \
        pavucontrol
}

# Install XFCE desktop
install_xfce_desktop() {
    echo "Installing XFCE desktop environment..."
    
    chroot_run apt-get update
    chroot_run apt-get install -y --no-install-recommends \
        xfce4 \
        xfce4-terminal \
        xfce4-power-manager \
        xfce4-notifyd \
        lightdm \
        lightdm-gtk-greeter
}

# Configure auto-login for live session
configure_autologin() {
    echo "Configuring auto-login..."
    
    # Create live user if not exists
    if ! chroot_run id -u zforge >/dev/null 2>&1; then
        chroot_run useradd -m -s /bin/bash -G sudo,audio,video,plugdev,netdev zforge
        echo "zforge:zforge" | chroot_run chpasswd
    fi
    
    # Configure LightDM for auto-login
    cat > "$CHROOT_PATH/etc/lightdm/lightdm.conf.d/99-autologin.conf" << EOF
[Seat:*]
autologin-user=zforge
autologin-user-timeout=0
user-session=default
EOF
    
    # Ensure lightdm is enabled
    chroot_run systemctl enable lightdm || true
}

# Create Calamares desktop launcher
create_calamares_launcher() {
    echo "Creating Calamares launcher..."
    
    # Create desktop directory
    mkdir -p "$CHROOT_PATH/home/zforge/Desktop"
    mkdir -p "$CHROOT_PATH/usr/share/applications"
    
    # Create launcher
    cat > "$CHROOT_PATH/usr/share/applications/install-system.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Version=1.0
Name=Install Z-FORGE System
Comment=Install Z-FORGE to your computer
Exec=pkexec /usr/bin/calamares
Icon=calamares
Terminal=false
StartupNotify=true
Categories=System;
Keywords=calamares;system;install;
EOF
    
    # Copy to desktop
    cp "$CHROOT_PATH/usr/share/applications/install-system.desktop" \
       "$CHROOT_PATH/home/zforge/Desktop/"
    
    # Make executable
    chmod +x "$CHROOT_PATH/home/zforge/Desktop/install-system.desktop"
    
    # Set ownership
    chroot_run chown -R zforge:zforge /home/zforge/Desktop
}

# Configure desktop session
configure_desktop_session() {
    echo "Configuring desktop session..."
    
    # Create default Openbox config for minimal desktop
    if [ -d "$CHROOT_PATH/etc/xdg/openbox" ]; then
        cat > "$CHROOT_PATH/etc/xdg/openbox/autostart" << 'EOF'
# Set wallpaper
nitrogen --restore &

# Start panel (if installed)
tint2 &

# Network manager applet
nm-applet &

# Volume control
volumeicon &

# Power manager
xfce4-power-manager &

# Show install icon on desktop
pcmanfm --desktop &
EOF
    fi
    
    # Configure XFCE session for XFCE desktop
    if [ -d "$CHROOT_PATH/etc/xdg/xfce4" ]; then
        # Ensure Calamares launcher is visible
        mkdir -p "$CHROOT_PATH/etc/xdg/xfce4/panel"
        mkdir -p "$CHROOT_PATH/etc/xdg/xfce4/xfconf/xfce-perchannel-xml"
    fi
}

# Main setup
main() {
    local desktop_env=$(detect_desktop_environment)
    
    echo "Setting up $desktop_env desktop environment..."
    
    case "$desktop_env" in
        minimal)
            install_minimal_desktop
            ;;
        xfce)
            install_xfce_desktop
            ;;
        none)
            echo "No desktop environment requested"
            return 0
            ;;
        *)
            echo "Unknown desktop environment: $desktop_env"
            echo "Using minimal desktop"
            install_minimal_desktop
            ;;
    esac
    
    # Common configurations
    configure_autologin
    create_calamares_launcher
    configure_desktop_session
    
    echo "Desktop setup complete!"
}

# Run main
main
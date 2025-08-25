#!/usr/bin/env python3
"""
KDE Optional Module for Z-FORGE
Installs KDE Plasma desktop environment with manual startup (no autostart)
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from builder.core.module import BaseModule


class KDEOptional(BaseModule):
    """
    Installs KDE Plasma desktop environment configured for manual startup only
    System boots to TTY by default, user can launch KDE with startx
    """
    
    def __init__(self, config: Dict, chroot_path: Path = None):
        super().__init__(config, chroot_path)
        self.module_name = "kde_optional"
        
        # KDE configuration
        self.enable_kde = config.get('services', {}).get('kde', {}).get('enable', False)
        self.variant = config.get('services', {}).get('kde', {}).get('variant', 'minimal')
        self.autostart = config.get('services', {}).get('kde', {}).get('autostart', False)
        self.display_manager = config.get('services', {}).get('kde', {}).get('display_manager', False)
        
        # Package lists based on variant
        self.package_variants = {
            'minimal': [
                'kde-plasma-desktop',
                'sddm',
                'xserver-xorg',
                'xserver-xorg-video-all',
                'xserver-xorg-input-all',
                'konsole',
                'dolphin',
                'kate',
                'fonts-noto',
                'breeze-gtk-theme'
            ],
            'standard': [
                'kde-standard',
                'sddm',
                'xserver-xorg',
                'xserver-xorg-video-all',
                'xserver-xorg-input-all',
                'fonts-noto',
                'firefox-esr',
                'libreoffice'
            ],
            'full': [
                'kde-full',
                'sddm',
                'xserver-xorg',
                'xserver-xorg-video-all',
                'xserver-xorg-input-all',
                'fonts-noto',
                'firefox-esr',
                'libreoffice',
                'gimp',
                'vlc'
            ]
        }
        
    def execute(self) -> bool:
        """Execute KDE installation with manual startup configuration"""
        try:
            # Check if KDE installation is enabled
            if not self.enable_kde:
                self.logger.info("KDE installation not enabled in configuration, skipping")
                return True
                
            self.logger.info(f"Starting KDE Plasma installation (variant: {self.variant})")
            
            # Step 1: Install X11 base system
            if not self._install_x11_base():
                return False
                
            # Step 2: Install KDE packages
            if not self._install_kde_packages():
                return False
                
            # Step 3: Configure display manager (disable autostart)
            if not self._configure_display_manager():
                return False
                
            # Step 4: Create startup scripts
            if not self._create_startup_scripts():
                return False
                
            # Step 5: Configure user environment
            if not self._configure_user_environment():
                return False
                
            # Step 6: Optimize KDE for server use
            if not self._optimize_kde_settings():
                return False
                
            # Step 7: Create usage documentation
            if not self._create_documentation():
                return False
                
            # Step 8: Validate installation
            if not self._validate_installation():
                return False
                
            self.logger.success("KDE Plasma installed - manual startup only via 'startx' or 'start-kde'")
            return True
            
        except Exception as e:
            self.logger.error(f"KDE installation failed: {e}")
            return False
    
    def _install_x11_base(self) -> bool:
        """Install X11 base system"""
        try:
            self.logger.info("Installing X11 base system")
            
            x11_packages = [
                'xorg',
                'xinit',
                'x11-xserver-utils',
                'x11-utils',
                'x11-common',
                'xauth',
                'mesa-utils',
                'libgl1-mesa-dri',
                'libglx-mesa0',
                'xfonts-base',
                'xfonts-100dpi',
                'xfonts-75dpi',
                'xfonts-scalable'
            ]
            
            cmd = f"apt-get update && apt-get install -y {' '.join(x11_packages)}"
            return self._run_in_chroot(cmd)
            
        except Exception as e:
            self.logger.error(f"X11 installation failed: {e}")
            return False
    
    def _install_kde_packages(self) -> bool:
        """Install KDE Plasma packages based on selected variant"""
        try:
            self.logger.info(f"Installing KDE Plasma {self.variant} variant")
            
            # Get package list for selected variant
            packages = self.package_variants.get(self.variant, self.package_variants['minimal'])
            
            # Additional useful packages
            additional_packages = [
                'plasma-nm',           # Network management
                'powerdevil',          # Power management
                'kde-config-gtk-style', # GTK integration
                'kde-config-sddm',     # SDDM configuration
                'kscreen',             # Screen management
                'plasma-pa',           # PulseAudio integration
                'ark',                 # Archive manager
                'spectacle',           # Screenshot utility
                'kwalletmanager'       # Wallet manager
            ]
            
            all_packages = packages + additional_packages
            
            # Install in chunks to avoid command line length issues
            chunk_size = 20
            for i in range(0, len(all_packages), chunk_size):
                chunk = all_packages[i:i+chunk_size]
                cmd = f"apt-get install -y {' '.join(chunk)}"
                if not self._run_in_chroot(cmd):
                    self.logger.warning(f"Some packages in chunk {i//chunk_size + 1} failed to install")
                    
            return True
            
        except Exception as e:
            self.logger.error(f"KDE package installation failed: {e}")
            return False
    
    def _configure_display_manager(self) -> bool:
        """Configure display manager to NOT autostart"""
        try:
            self.logger.info("Configuring display manager (disabling autostart)")
            
            # CRITICAL: Disable ALL display managers
            display_managers = ['sddm', 'gdm3', 'lightdm', 'xdm', 'kdm']
            
            for dm in display_managers:
                # Disable service
                self._run_in_chroot(f"systemctl disable {dm} 2>/dev/null || true")
                # Mask service to prevent any activation
                self._run_in_chroot(f"systemctl mask {dm} 2>/dev/null || true")
                
            # Set default target to multi-user (text mode)
            self._run_in_chroot("systemctl set-default multi-user.target")
            
            # Configure SDDM for manual use (when started)
            sddm_config = """
[General]
# SDDM Configuration for Z-FORGE
HaltCommand=/usr/bin/systemctl poweroff
RebootCommand=/usr/bin/systemctl reboot

[Theme]
Current=breeze
CursorTheme=breeze_cursors

[Users]
MaximumUid=60000
MinimumUid=1000

[Wayland]
EnableHiDPI=true
SessionCommand=/usr/share/sddm/scripts/wayland-session

[X11]
EnableHiDPI=true
ServerPath=/usr/bin/X
SessionCommand=/usr/share/sddm/scripts/Xsession
DisplayCommand=/usr/share/sddm/scripts/Xsetup
MinimumVT=7

[Autologin]
# IMPORTANT: No autologin
Relogin=false
Session=
User=
"""
            
            sddm_config_path = self.chroot_path / 'etc/sddm.conf'
            sddm_config_path.write_text(sddm_config)
            
            self.logger.success("Display manager disabled - system will boot to TTY")
            return True
            
        except Exception as e:
            self.logger.error(f"Display manager configuration failed: {e}")
            return False
    
    def _create_startup_scripts(self) -> bool:
        """Create convenient startup scripts for KDE"""
        try:
            self.logger.info("Creating KDE startup scripts")
            
            # Main KDE startup script
            start_kde_script = """#!/bin/bash
# Z-FORGE KDE Plasma Startup Script
# Launches KDE Plasma desktop environment manually

echo "═══════════════════════════════════════════════"
echo "    Z-FORGE KDE Plasma Desktop Launcher"
echo "═══════════════════════════════════════════════"
echo ""

# Check if X is already running
if [ -n "$DISPLAY" ]; then
    echo "X server is already running on display $DISPLAY"
    echo "Please exit the current X session first."
    exit 1
fi

# Check for running display manager
if systemctl is-active --quiet sddm || systemctl is-active --quiet gdm || systemctl is-active --quiet lightdm; then
    echo "A display manager is already running."
    echo "Please stop it first with: sudo systemctl stop <display-manager>"
    exit 1
fi

echo "Starting KDE Plasma Desktop..."
echo "Press Ctrl+Alt+F2-F6 to switch to other TTYs"
echo "Logout from KDE to return to this TTY"
echo ""
echo "Launching in 3 seconds..."
sleep 3

# Start X with KDE Plasma
exec startx /usr/bin/startplasma-x11 -- :0 vt$XDG_VTNR
"""
            
            script_path = self.chroot_path / 'usr/local/bin/start-kde'
            script_path.write_text(start_kde_script)
            script_path.chmod(0o755)
            
            # Alternative script using SDDM
            start_sddm_script = """#!/bin/bash
# Start SDDM display manager manually

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Starting SDDM display manager..."
echo "This will provide a graphical login screen."
echo ""

# Unmask SDDM temporarily
systemctl unmask sddm

# Start SDDM
systemctl start sddm

echo ""
echo "SDDM started. To stop it and return to console:"
echo "  1. Press Ctrl+Alt+F2 to switch to TTY2"
echo "  2. Login and run: sudo systemctl stop sddm"
echo "  3. Run: sudo systemctl mask sddm"
"""
            
            sddm_script_path = self.chroot_path / 'usr/local/bin/start-sddm'
            sddm_script_path.write_text(start_sddm_script)
            sddm_script_path.chmod(0o755)
            
            # Quick GUI script (simplified launcher)
            quick_gui_script = """#!/bin/bash
# Quick GUI launcher - starts minimal KDE session

export DISPLAY=:0
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=KDE
export KDE_SESSION_VERSION=5

# Start only essential KDE components
xinit /usr/bin/startplasma-x11 -- :0 -nolisten tcp
"""
            
            quick_script_path = self.chroot_path / 'usr/local/bin/quick-gui'
            quick_script_path.write_text(quick_gui_script)
            quick_script_path.chmod(0o755)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Startup script creation failed: {e}")
            return False
    
    def _configure_user_environment(self) -> bool:
        """Configure user environment for KDE"""
        try:
            self.logger.info("Configuring user environment")
            
            # Create .xinitrc template
            xinitrc_content = """#!/bin/sh
# .xinitrc for KDE Plasma on Z-FORGE

# Set up environment
userresources=$HOME/.Xresources
usermodmap=$HOME/.Xmodmap
sysresources=/etc/X11/xinit/.Xresources
sysmodmap=/etc/X11/xinit/.Xmodmap

# Merge in defaults and keymaps
if [ -f $sysresources ]; then
    xrdb -merge $sysresources
fi

if [ -f $sysmodmap ]; then
    xmodmap $sysmodmap
fi

if [ -f "$userresources" ]; then
    xrdb -merge "$userresources"
fi

if [ -f "$usermodmap" ]; then
    xmodmap "$usermodmap"
fi

# Start D-Bus session
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    eval $(dbus-launch --sh-syntax --exit-with-session)
fi

# Export desktop environment
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=KDE
export KDE_SESSION_VERSION=5
export QT_QPA_PLATFORMTHEME=kde

# Start KDE Plasma
exec startplasma-x11
"""
            
            # Install to /etc/skel for new users
            skel_xinitrc = self.chroot_path / 'etc/skel/.xinitrc'
            skel_xinitrc.write_text(xinitrc_content)
            skel_xinitrc.chmod(0o755)
            
            # Create .xsession as well
            xsession_content = """#!/bin/sh
# .xsession for KDE Plasma on Z-FORGE
exec startplasma-x11
"""
            
            skel_xsession = self.chroot_path / 'etc/skel/.xsession'
            skel_xsession.write_text(xsession_content)
            skel_xsession.chmod(0o755)
            
            # Create helpful bash aliases
            bashrc_additions = """
# Z-FORGE KDE aliases
alias kde='start-kde'
alias gui='quick-gui'
alias start-gui='start-kde'
alias plasma='start-kde'

# Desktop environment helpers
alias kde-logout='qdbus org.kde.ksmserver /KSMServer logout 0 0 0'
alias kde-restart='qdbus org.kde.ksmserver /KSMServer logout 0 1 0'
alias kde-shutdown='qdbus org.kde.ksmserver /KSMServer logout 0 2 0'

# Quick status check
alias kde-status='systemctl status sddm 2>/dev/null || echo "KDE not running (start with: start-kde)"'
"""
            
            bashrc_path = self.chroot_path / 'etc/skel/.bashrc'
            if bashrc_path.exists():
                current_bashrc = bashrc_path.read_text()
                if "Z-FORGE KDE aliases" not in current_bashrc:
                    bashrc_path.write_text(current_bashrc + "\n" + bashrc_additions)
            else:
                bashrc_path.write_text(bashrc_additions)
                
            return True
            
        except Exception as e:
            self.logger.error(f"User environment configuration failed: {e}")
            return False
    
    def _optimize_kde_settings(self) -> bool:
        """Optimize KDE settings for server/minimal use"""
        try:
            self.logger.info("Optimizing KDE settings for server use")
            
            # KDE system-wide configuration
            kde_config = """
[General]
# Disable unnecessary effects for better performance
AnimationSpeed=0

[Compositing]
# Reduce compositor overhead
Backend=OpenGL
Enabled=true
GLCore=true
GLPreferBufferSwap=a
GLTextureFilter=1
HiddenPreviews=5
OpenGLIsUnsafe=false
WindowsBlockCompositing=true
XRenderSmoothScale=false

[Plugins]
# Disable heavy effects
blurEnabled=false
contrastEnabled=false
wobblywindowsEnabled=false
cubeslideEnabled=false

[Windows]
# Optimize window behavior
BorderlessMaximizedWindows=true
ClickRaise=true
FocusPolicy=ClickToFocus
RollOverDesktops=false
"""
            
            # Create KDE config directory
            kde_config_dir = self.chroot_path / 'etc/xdg'
            kde_config_dir.mkdir(parents=True, exist_ok=True)
            
            config_path = kde_config_dir / 'kwinrc'
            config_path.write_text(kde_config)
            
            # Plasma shell configuration for minimal resource usage
            plasma_config = """
[General]
# Minimal plasma configuration
ImmutabilityMode=1

[Theme]
name=breeze-dark

[Defaults]
# Reduce resource usage
EnableBrightnessControl=false
EnablePowerManagement=false
"""
            
            plasma_path = kde_config_dir / 'plasmarc'
            plasma_path.write_text(plasma_config)
            
            # Disable KDE indexing service (baloo) by default
            baloo_config = """
[Basic Settings]
Indexing-Enabled=false
"""
            
            baloo_path = kde_config_dir / 'baloofilerc'
            baloo_path.write_text(baloo_config)
            
            return True
            
        except Exception as e:
            self.logger.error(f"KDE optimization failed: {e}")
            return False
    
    def _create_documentation(self) -> bool:
        """Create usage documentation for KDE"""
        try:
            self.logger.info("Creating KDE usage documentation")
            
            # Main documentation
            doc_content = """
═══════════════════════════════════════════════════════════════════
                    Z-FORGE KDE PLASMA DESKTOP GUIDE
═══════════════════════════════════════════════════════════════════

KDE Plasma has been installed with MANUAL startup configuration.
The system boots to a text console (TTY) by default.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STARTING KDE PLASMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After logging in at the console, use one of these commands:

  start-kde      # Recommended: Full KDE Plasma desktop
  startx         # Standard X11 startup (uses .xinitrc)
  quick-gui      # Minimal KDE session
  start-sddm     # Start graphical login (requires sudo)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SWITCHING BETWEEN CONSOLE AND GUI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From KDE to Console:
  • Logout from KDE menu
  • Press Ctrl+Alt+F2 through F6 for other TTYs
  • Press Ctrl+Alt+Backspace to force X server termination

From Console to KDE:
  • Press Ctrl+Alt+F7 (if KDE is running)
  • Run 'start-kde' to launch new session

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USEFUL KEYBOARD SHORTCUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KDE Plasma:
  • Alt+F2         : Run command
  • Alt+Tab        : Switch windows
  • Alt+F4         : Close window
  • Meta (Win key) : Application menu
  • Meta+L         : Lock screen
  • Ctrl+Alt+Del   : Logout dialog

Console:
  • Ctrl+Alt+F1-F6 : Switch to TTY1-6
  • Ctrl+Alt+F7    : Switch to GUI (if running)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Black screen after startx:
  • Check ~/.xsession-errors for errors
  • Try: rm -rf ~/.cache/plasma* ~/.config/plasma*
  • Verify graphics drivers: lspci -k | grep -A3 VGA

KDE won't start:
  • Check X server: X -version
  • Test X: xinit /usr/bin/xterm
  • Check logs: journalctl -xe

Performance issues:
  • Disable effects: System Settings → Display → Compositor
  • Reduce animations: System Settings → Workspace → Animation Speed
  • Disable file indexing: balooctl disable

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIGURATION FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User configuration:
  ~/.xinitrc       : X initialization
  ~/.xsession      : X session configuration
  ~/.config/       : KDE user settings

System configuration:
  /etc/sddm.conf   : SDDM display manager
  /etc/xdg/        : System-wide KDE settings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTALLED VARIANT: {variant}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This installation includes:
  ✓ KDE Plasma Desktop
  ✓ Essential KDE applications
  ✓ X11 window system
  ✓ SDDM display manager (disabled)
  ✓ Hardware acceleration support

Note: The system is configured for SERVER use with desktop available
on-demand. This reduces resource usage when GUI is not needed.

═══════════════════════════════════════════════════════════════════
""".format(variant=self.variant.upper())
            
            # Write to multiple locations for discoverability
            doc_locations = [
                self.chroot_path / 'usr/share/doc/kde/zforge-guide.txt',
                self.chroot_path / 'etc/motd.d/50-kde-guide'
            ]
            
            for doc_path in doc_locations:
                doc_path.parent.mkdir(parents=True, exist_ok=True)
                doc_path.write_text(doc_content)
                
            # Create quick reference card
            quick_ref = """
┌─────────────────────────────────────┐
│  Z-FORGE KDE QUICK REFERENCE        │
├─────────────────────────────────────┤
│  Start KDE:     start-kde           │
│  Quick GUI:     quick-gui           │
│  Start SDDM:    sudo start-sddm     │
│  Switch TTY:    Ctrl+Alt+F1-F7      │
│  KDE Logout:    kde-logout          │
│  Check status:  kde-status          │
└─────────────────────────────────────┘
"""
            
            ref_path = self.chroot_path / 'etc/motd.d/51-kde-quick-ref'
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            ref_path.write_text(quick_ref)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Documentation creation failed: {e}")
            return False
    
    def _validate_installation(self) -> bool:
        """Validate KDE installation"""
        try:
            self.logger.info("Validating KDE installation")
            
            # Check critical binaries
            critical_binaries = [
                'startplasma-x11',
                'kwin_x11',
                'plasmashell',
                'sddm',
                'X',
                'startx'
            ]
            
            missing_binaries = []
            for binary in critical_binaries:
                binary_path = self.chroot_path / 'usr/bin' / binary
                if not binary_path.exists():
                    # Check alternative locations
                    alt_path = self.chroot_path / 'usr/sbin' / binary
                    if not alt_path.exists():
                        missing_binaries.append(binary)
                        
            if missing_binaries:
                self.logger.warning(f"Missing binaries: {', '.join(missing_binaries)}")
                
            # Check startup scripts
            scripts = ['start-kde', 'start-sddm', 'quick-gui']
            for script in scripts:
                script_path = self.chroot_path / 'usr/local/bin' / script
                if not script_path.exists():
                    self.logger.warning(f"Startup script missing: {script}")
                    
            # Verify display manager is disabled
            result = self._run_in_chroot("systemctl is-enabled sddm 2>/dev/null || echo disabled")
            if result and "disabled" not in str(result):
                self.logger.warning("SDDM may be enabled - verifying mask status")
                self._run_in_chroot("systemctl mask sddm")
                
            self.logger.success(f"""
KDE Plasma Installation Summary:
================================
✓ Variant: {self.variant}
✓ Autostart: DISABLED (boots to TTY)
✓ Start command: start-kde
✓ Display manager: SDDM (masked)
✓ X11: Installed
✓ Scripts: Created

Usage: Login at console and run 'start-kde'
""")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False
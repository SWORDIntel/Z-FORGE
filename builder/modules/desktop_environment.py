"""
Desktop Environment Module
Configures desktop environment for live ISO with Calamares integration
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional, List
import logging
import os

class DesktopEnvironment:
    """Sets up desktop environment for live ISO"""

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.desktop_type = config.get('desktop_environment', 'minimal')

    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """Configure desktop environment"""
        self.logger.info(f"Configuring {self.desktop_type} desktop environment...")

        try:
            # Run desktop setup script
            self._run_desktop_setup()
            
            # Configure Calamares GUI integration
            self._configure_calamares_gui()
            
            # Setup display manager
            self._setup_display_manager()
            
            # Create user session
            self._create_user_session()
            
            return {
                'status': 'success',
                'desktop_type': self.desktop_type,
                'autologin_enabled': True,
                'calamares_launcher': True
            }

        except Exception as e:
            self.logger.error(f"Desktop environment setup failed: {e}")
            return {'status': 'error', 'error': str(e)}

    def _run_desktop_setup(self):
        """Run the desktop setup script"""
        setup_script = Path(__file__).parent.parent.parent / "scripts" / "desktop" / "setup_live_desktop.sh"
        
        if not setup_script.exists():
            raise FileNotFoundError(f"Desktop setup script not found: {setup_script}")
        
        # Set desktop environment variable
        env = os.environ.copy()
        env['DESKTOP_ENVIRONMENT'] = self.desktop_type
        
        cmd = [str(setup_script), str(self.chroot_path)]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.logger.error(f"Desktop setup failed: {result.stderr}")
            raise RuntimeError(f"Desktop setup script failed: {result.stderr}")
        
        self.logger.info("Desktop setup completed successfully")

    def _configure_calamares_gui(self):
        """Configure Calamares for GUI mode"""
        # Ensure Calamares is configured for GUI
        calamares_conf = self.chroot_path / "etc" / "calamares" / "settings.conf"
        
        if calamares_conf.exists():
            # Update settings for GUI mode
            content = calamares_conf.read_text()
            
            # Ensure GUI mode is enabled
            if "disable-gui: true" in content:
                content = content.replace("disable-gui: true", "disable-gui: false")
                calamares_conf.write_text(content)
            
            self.logger.info("Calamares GUI mode configured")

    def _setup_display_manager(self):
        """Configure display manager for live session"""
        # Enable display manager service
        services_to_enable = []
        
        if (self.chroot_path / "usr/bin/lightdm").exists():
            services_to_enable.append("lightdm")
        elif (self.chroot_path / "usr/bin/gdm3").exists():
            services_to_enable.append("gdm3")
        elif (self.chroot_path / "usr/bin/sddm").exists():
            services_to_enable.append("sddm")
        
        for service in services_to_enable:
            cmd = ["chroot", str(self.chroot_path), "systemctl", "enable", service]
            subprocess.run(cmd, capture_output=True)
            self.logger.info(f"Enabled {service} display manager")

    def _create_user_session(self):
        """Create default user session configuration"""
        user_home = self.chroot_path / "home" / "zforge"
        
        # Create .xinitrc for fallback
        xinitrc = user_home / ".xinitrc"
        xinitrc.write_text("""#!/bin/sh
# Z-FORGE Live Session

# Start desktop environment
case "$DESKTOP_ENVIRONMENT" in
    minimal)
        exec openbox-session
        ;;
    xfce)
        exec startxfce4
        ;;
    *)
        exec openbox-session
        ;;
esac
""")
        
        # Set permissions
        subprocess.run(["chroot", str(self.chroot_path), "chown", "zforge:zforge", "/home/zforge/.xinitrc"])
        subprocess.run(["chmod", "+x", str(xinitrc)])
        
        self.logger.info("User session configured")

    def validate(self) -> Dict:
        """Validate desktop environment setup"""
        issues = []
        
        # Check for display manager
        display_managers = ["lightdm", "gdm3", "sddm"]
        has_dm = any((self.chroot_path / "usr/bin" / dm).exists() for dm in display_managers)
        
        if not has_dm:
            issues.append("No display manager installed")
        
        # Check for Calamares launcher
        launcher = self.chroot_path / "usr/share/applications/install-system.desktop"
        if not launcher.exists():
            issues.append("Calamares launcher not found")
        
        # Check for X server
        if not (self.chroot_path / "usr/bin/X").exists():
            issues.append("X server not installed")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

    def cleanup(self):
        """Cleanup temporary files"""
        # Remove package caches
        apt_cache = self.chroot_path / "var/cache/apt/archives"
        if apt_cache.exists():
            for pkg in apt_cache.glob("*.deb"):
                pkg.unlink()
        
        self.logger.info("Desktop environment cleanup completed")
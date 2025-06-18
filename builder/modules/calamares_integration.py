# z-forge/builder/modules/calamares_integration.py

"""
Calamares Integration Module
Prepares Calamares installer with Z-Forge modules
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional
import logging
import yaml

class CalamaresIntegration:
    """Integrates Calamares with custom Z-Forge modules"""

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"

    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        """
        Install and configure Calamares

        Returns:
            Dict with installation status
        """

        self.logger.info("Starting Calamares integration...")

        try:
            # Install Calamares
            self._install_calamares()

            # Copy custom modules
            self._install_custom_modules()

            # Configure Calamares
            self._configure_calamares()

            # Setup desktop environment
            self._setup_desktop_environment()

            # Create launcher
            self._create_launcher()

            return {
                'status': 'success',
                'calamares_version': self._get_calamares_version()
            }

        except Exception as e:
            self.logger.error(f"Calamares integration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }

    def _install_calamares(self):
        """Install Calamares and dependencies"""

        self.logger.info("Installing Calamares...")

        # Add Calamares repository if needed
        sources_content = """
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware
"""

        sources_file = self.chroot_path / "etc/apt/sources.list"
        sources_file.write_text(sources_content)

        # Update and install
        install_cmd = """
apt-get update
apt-get install -y calamares calamares-settings-debian \
    xfce4 xfce4-terminal lightdm lightdm-gtk-greeter \
    firefox-esr network-manager-gnome \
    gparted vim nano htop \
    python3-pyqt5 python3-yaml python3-jsonschema
"""

        subprocess.run(
            ["chroot", str(self.chroot_path), "bash", "-c", install_cmd],
            check=True
        )

    def _install_custom_modules(self):
        """Copy Z-Forge custom modules to Calamares"""

        self.logger.info("Installing custom Calamares modules...")

        # Source modules directory (from our project)
        modules_src = Path("calamares/modules")

        # Destination in chroot
        modules_dst = self.chroot_path / "usr/lib/calamares/modules"

        # Copy each module
        for module_dir in modules_src.iterdir():
            if module_dir.is_dir():
                module_name = module_dir.name
                self.logger.info(f"Installing module: {module_name}")

                # Create module directory
                dst_dir = modules_dst / module_name
                dst_dir.mkdir(parents=True, exist_ok=True)

                # Copy module files
                for file in module_dir.iterdir():
                    shutil.copy2(file, dst_dir)

                # Make Python files executable
                for py_file in dst_dir.glob("*.py"):
                    py_file.chmod(0o755)

    def _configure_calamares(self):
        """Configure Calamares settings"""

        self.logger.info("Configuring Calamares...")

        # Main settings configuration
        settings = {
            'modules-search': ['local'],
            'instances': [
                {'id': 'zfsbench', 'module': 'shellprocess', 'config': 'zfsbench.conf'},
                {'id': 'zfspool', 'module': 'zfspooldetect'},
                {'id': 'zfstarget', 'module': 'zfsrootselect'},
                {'id': 'zfsboot', 'module': 'zfsbootloader'},
                {'id': 'proxmox', 'module': 'proxmoxconfig'}
            ],
            'sequence': [
                {
                    'show': [
                        'welcome',
                        'locale',
                        'keyboard',
                        'partition'
                    ]
                },
                {
                    'exec': [
                        'partition',
                        'mount',
                        'unpackfs',
                        'machineid',
                        'fstab',
                        'locale',
                        'keyboard',
                        'localecfg',
                        'zfsbench',
                        'zfspool',
                        'users',
                        'displaymanager',
                        'networkcfg',
                        'hwclock',
                        'zfsboot',
                        'proxmox',
                        'initramfscfg',
                        'initramfs',
                        'grubcfg',
                        'bootloader',
                        'umount'
                    ]
                },
                {
                    'show': [
                        'finished'
                    ]
                }
            ],
            'branding': 'zforge',
            'prompt-install': True,
            'dont-chroot': False,
            'oem-setup': False,
            'disable-cancel': False,
            'disable-cancel-during-exec': True
        }

        settings_path = self.chroot_path / "etc/calamares/settings.conf"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        with open(settings_path, 'w') as f:
            yaml.dump(settings, f, default_flow_style=False)

        # Create benchmarking configuration
        bench_config = {
            'dontChroot': False,
            'timeout': 600,
            'script': [
                {
                    'command': '/install/benchmarking/zfs_performance_test.sh',
                    'timeout': 600
                }
            ]
        }

        bench_conf_path = self.chroot_path / "etc/calamares/modules/zfsbench.conf"
        with open(bench_conf_path, 'w') as f:
            yaml.dump(bench_config, f, default_flow_style=False)

        # Create branding
        self._create_branding()

    def _create_branding(self):
        """Create Z-Forge branding for Calamares"""

        branding_dir = self.chroot_path / "etc/calamares/branding/zforge"
        branding_dir.mkdir(parents=True, exist_ok=True)

        # Branding descriptor
        branding = {
            'componentName': 'zforge',
            'welcomeStyleCalamares': False,
            'welcomeExpandingLogo': True,
            'windowExpanding': 'normal',
            'windowSize': '800,600',
            'strings': {
                'productName': 'Z-Forge Proxmox VE',
                'shortProductName': 'Z-Forge',
                'version': '3.0',
                'shortVersion': 'v3',
                'versionedName': 'Z-Forge Proxmox VE v3',
                'shortVersionedName': 'Z-Forge v3',
                'bootloaderEntryName': 'Z-Forge Proxmox',
                'productUrl': 'https://proxmox.com',
                'supportUrl': 'https://proxmox.com/support',
                'bugReportUrl': 'https://bugzilla.proxmox.com'
            },
            'images': {
                'productLogo': 'logo.png',
                'productIcon': 'icon.png',
                'productWelcome': 'welcome.png'
            },
            'slideshow': 'show.qml',
            'style': {
                'sidebarBackground': '#292F34',
                'sidebarText': '#FFFFFF',
                'sidebarTextSelect': '#292F34',
                'sidebarTextHighlight': '#D35400'
            }
        }

        branding_path = branding_dir / "branding.desc"
        with open(branding_path, 'w') as f:
            yaml.dump(branding, f, default_flow_style=False)

        # Create placeholder images
        for img in ['logo.png', 'icon.png', 'welcome.png']:
            img_path = branding_dir / img
            # In production, copy actual images
            img_path.touch()

    def _setup_desktop_environment(self):
        """Configure lightweight desktop for installer"""

        self.logger.info("Setting up desktop environment...")

        # Configure LightDM for auto-login
        lightdm_conf = """
[Seat:*]
autologin-guest=false
autologin-user=root
autologin-user-timeout=0
autologin-session=xfce

[Security]
allow-root=true
"""

        lightdm_path = self.chroot_path / "etc/lightdm/lightdm.conf"
        lightdm_path.parent.mkdir(parents=True, exist_ok=True)
        lightdm_path.write_text(lightdm_conf)

        # Create desktop session
        xinitrc = """#!/bin/bash
# Start XFCE session for installer
exec startxfce4
"""

        xinitrc_path = self.chroot_path / "root/.xinitrc"
        xinitrc_path.write_text(xinitrc)
        xinitrc_path.chmod(0o755)

    def _create_launcher(self):
        """Create desktop launcher for Calamares"""

        launcher = """[Desktop Entry]
Type=Application
Version=1.0
Name=Install Z-Forge Proxmox VE
Comment=Install Z-Forge Proxmox VE to disk
Exec=pkexec calamares
Icon=calamares
Terminal=false
StartupNotify=true
Categories=System;
"""

        desktop_path = self.chroot_path / "usr/share/applications/calamares.desktop"
        desktop_path.parent.mkdir(parents=True, exist_ok=True)
        desktop_path.write_text(launcher)

        # Also create on desktop
        desktop_dir = self.chroot_path / "root/Desktop"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(desktop_path, desktop_dir)

    def _get_calamares_version(self) -> str:
        """Get installed Calamares version"""

        result = subprocess.run(
            ["chroot", self.chroot_path, "calamares", "--version"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return "unknown"

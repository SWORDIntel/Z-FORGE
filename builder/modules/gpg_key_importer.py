#!/usr/bin/env python3
"""
GPG Key Importer Module for Z-Forge
Imports GPG keys for Debian and Proxmox repositories
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

class GPGKeyImporter:
    """Imports GPG keys for the build process"""

    def __init__(self, workspace: Path, config: Dict[str, Any]):
        self.workspace = workspace
        self.config = config
        self.chroot_path = workspace / "chroot"
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, resume_data: Optional[Dict[str, Any]] = None,
                lockfile: Optional[Any] = None) -> Dict[str, Any]:
        """Import GPG keys"""
        self.logger.info("Importing GPG keys for repositories...")

        try:
            self._import_debian_keys()
            self._import_proxmox_keys()

            return {
                'status': 'success',
                'message': 'GPG keys imported successfully'
            }

        except Exception as e:
            self.logger.error(f"GPG key import failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _import_debian_keys(self):
        """Import Debian GPG keys"""
        self.logger.info("Importing Debian GPG keys...")

        keyring_path = self.chroot_path / "usr/share/keyrings"
        keyring_path.mkdir(parents=True, exist_ok=True)

        # The debian-archive-keyring package should handle this,
        # but we can add keys manually if needed.
        # For now, we'll rely on the package.
        self.logger.info("Debian GPG keys will be handled by the debian-archive-keyring package.")


    def _import_proxmox_keys(self):
        """Import Proxmox GPG keys"""
        self.logger.info("Importing Proxmox GPG keys...")

        key_url = "https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg"
        key_path = self.chroot_path / "etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg"
        key_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                ["wget", "-O", str(key_path), key_url],
                check=True,
                capture_output=True,
                text=True,
            )
            self.logger.info("Proxmox GPG key downloaded and installed.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to download Proxmox GPG key: {e.stderr}")
            raise

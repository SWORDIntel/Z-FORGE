#!/usr/bin/env python3
# z-forge/builder/core/config.py

"""
Build Configuration Manager
Handles loading, validation, and access to build configuration
"""

import yaml
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

class BuildConfig:
    """Manages Z-Forge build configuration"""

    def __init__(self, config_path: str = "build_spec.yml"):
        """
        Load and validate build configuration

        Args:
            config_path: Path to build_spec.yml configuration

        Raises:
            ValueError: If config file is missing or invalid
        """

        self.config_path = config_path
        self.data = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict:
        """Load build configuration from YAML file"""

        try:
            if not os.path.exists(config_path):
                # Create default configuration
                default_config = self._create_default_config()

                with open(config_path, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

                print(f"Created default configuration: {config_path}")
                return default_config

            # Load existing configuration
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Validate required fields
            required = ['builder_config', 'modules']
            for field in required:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")

            return config

        except Exception as e:
            print(f"Failed to load config: {e}", file=sys.stderr)
            sys.exit(1)

    def _create_default_config(self) -> Dict:
        """Create a default configuration if none exists"""

        return {
            'builder_config': {
                'debian_release': 'bookworm',
                'kernel_version': 'latest',  # Will fetch latest stable
                'output_iso_name': 'zforge-proxmox-v3.iso',
                'enable_debug': True,
                'workspace_path': '/tmp/zforge_workspace',
                'cache_packages': True
            },
            'proxmox_config': {
                'version': 'latest',  # Will use latest PVE 8.x
                'minimal_install': True,
                'include_packages': [
                    'proxmox-ve',
                    'proxmox-kernel-6.8',  # Latest kernel series
                    'zfs-dkms',
                    'zfsutils-linux',
                    'pve-zsync'
                ]
            },
            'zfs_config': {
                'version': 'latest',  # Latest OpenZFS
                'build_from_source': True,
                'enable_encryption': True,
                'default_compression': 'lz4'
            },
            'bootloader_config': {
                'primary': 'zfsbootmenu',
                'enable_opencore': True,
                'opencore_drivers': ['NvmExpressDxe.efi', 'OpenRuntime.efi']
            },
            'modules': [
                {'name': 'WorkspaceSetup', 'enabled': True},
                {'name': 'Debootstrap', 'enabled': True},
                {'name': 'KernelAcquisition', 'enabled': True},
                {'name': 'ZFSBuild', 'enabled': True},
                {'name': 'ProxmoxIntegration', 'enabled': True},
                {'name': 'BootloaderSetup', 'enabled': True},
                {'name': 'CalamaresIntegration', 'enabled': True},
                {'name': 'SecurityHardening', 'enabled': True},
                {'name': 'ISOGeneration', 'enabled': True}
            ]
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key

        Args:
            key: Configuration key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Value from configuration or default
        """

        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            key: Configuration key to set
            value: Value to set
        """

        self.data[key] = value

    def save(self) -> None:
        """Save current configuration to file"""

        with open(self.config_path, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)

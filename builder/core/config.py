#!/usr/bin/env python3
# z-forge/builder/core/config.py

"""
Build Configuration Manager
Handles loading, validation, and access to build configuration
"""

import yaml
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Initialize a logger for this module
logger = logging.getLogger(__name__)

class BuildConfig:
    """
    Manages the Z-Forge build configuration loaded from `build_spec.yml`.

    This class is responsible for loading the YAML configuration file,
    validating its basic structure, providing access to configuration values,
    and creating a default configuration if the specified file doesn't exist.
    The configuration dictates various aspects of the build process, such as
    Debian release, kernel versions, Proxmox settings, ZFS options,
    and the sequence of builder modules to execute.
    """

    def __init__(self, config_path: Union[str, Path] = "build_spec.yml") -> None:
        """
        Load and validate the build configuration from the given path.

        If the configuration file does not exist, a default configuration
        will be created and saved at `config_path`.

        Args:
            config_path: Path to the `build_spec.yml` configuration file.
                         Defaults to "build_spec.yml" in the current working directory.

        Raises:
            SystemExit: If the config file is invalid (e.g., missing required fields)
                        or an I/O error occurs during loading/saving.
        """
        self.config_path: Path = Path(config_path)
        self.data: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load the build configuration from the YAML file specified by `self.config_path`.

        If the file doesn't exist, it calls `_create_default_config` to generate
        a default configuration and saves it. It also performs basic validation
        to ensure essential keys like 'builder_config' and 'modules' are present.

        Returns:
            A dictionary representing the loaded (or default) configuration.

        Raises:
            SystemExit: If there's an error loading or parsing the YAML file,
                        or if basic validation fails.
        """
        try:
            if not self.config_path.exists():
                logger.info(f"Configuration file not found at {self.config_path}. Creating a default configuration.")
                default_config: Dict[str, Any] = self._create_default_config()
                self.save(default_config) # Save the newly created default config
                logger.info(f"Default configuration created and saved to: {self.config_path}")
                return default_config

            # Load existing configuration
            logger.info(f"Loading configuration from: {self.config_path}")
            with self.config_path.open('r') as f:
                config: Optional[Dict[str, Any]] = yaml.safe_load(f)

            if config is None: # Handle empty YAML file
                logger.error(f"Configuration file {self.config_path} is empty or not valid YAML.")
                sys.exit(1)

            # Validate required top-level fields
            required_fields: List[str] = ['builder_config', 'modules']
            for field in required_fields:
                if field not in config:
                    logger.error(f"Missing required top-level field '{field}' in {self.config_path}.")
                    # Optionally, could raise ValueError and let __init__ handle exit
                    sys.exit(1)

            logger.info("Configuration loaded successfully.")
            return config

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {self.config_path}: {e}")
            sys.exit(1)
        except IOError as e:
            logger.error(f"I/O error accessing configuration file {self.config_path}: {e}")
            sys.exit(1)
        except Exception as e: # Catch-all for other unexpected errors during load
            logger.error(f"An unexpected error occurred while loading configuration from {self.config_path}: {e}")
            sys.exit(1)

    def _create_default_config(self) -> Dict[str, Any]:
        """
        Create and return a default build configuration dictionary.

        This default configuration is used if `build_spec.yml` is not found.
        It defines a standard build pipeline with common settings for Proxmox,
        ZFS, and necessary builder modules.

        Returns:
            A dictionary containing the default configuration structure and values.
        """
        logger.debug("Generating default configuration structure.")
        return {
            # General settings for the ZForgeBuilder itself
            'builder_config': {
                'debian_release': 'sid',  # Base Debian version for the ISO
                'kernel_version': 'latest',    # Kernel version to install (can be specific or 'latest')
                'output_iso_name': 'zforge-proxmox-v3.iso', # Name of the final ISO file
                'enable_debug': True,          # Flag for enabling debug features in modules
                'workspace_path': '/tmp/zforge_workspace', # Directory for all build operations
                'cache_packages': True         # Whether to cache downloaded Debian packages
            },
            # Configuration for Proxmox VE integration
            'proxmox_config': {
                'version': 'latest',          # Proxmox VE version (e.g., '8.1', 'latest')
                'minimal_install': True,      # If true, installs a minimal set of PVE packages
                'include_packages': [         # List of essential Proxmox and ZFS packages
                    'proxmox-ve',
                    'proxmox-kernel-6.8', # Example: Specify a recent kernel series
                    'zfs-dkms',
                    'zfsutils-linux',
                    'pve-zsync'
                ]
            },
            # Configuration for ZFS setup
            'zfs_config': {
                'version': 'latest',          # OpenZFS version
                'build_from_source': True,    # Whether to build ZFS from source or use packages
                'enable_encryption': True,    # Enable ZFS native encryption support
                'default_compression': 'zstd-6'  # Default ZFS compression algorithm
            },
            # Configuration for the bootloader (e.g., GRUB, systemd-boot, ZFSBootMenu)
            'bootloader_config': {
                'primary': 'zfsbootmenu',     # Preferred bootloader
                'enable_opencore': True,      # Option to include OpenCore (e.g., for Hackintosh compatibility)
                'opencore_drivers': ['NvmExpressDxe.efi', 'OpenRuntime.efi'] # Drivers for OpenCore
            },
            # List of builder modules to execute, and their enabled status.
            # The order in this list defines the execution sequence of the build pipeline.
            'modules': [
                {'name': 'WorkspaceSetup', 'enabled': True},    # Sets up the build workspace
                {'name': 'Debootstrap', 'enabled': True},       # Creates a minimal Debian rootfs
                {'name': 'KernelAcquisition', 'enabled': True}, # Installs the Linux kernel
                {'name': 'ZFSBuild', 'enabled': True},          # Builds/installs ZFS
                # Note: DracutConfig is often implicitly created by build-iso.sh if not present as a file
                # {'name': 'DracutConfig', 'enabled': True},    # Configures Dracut for initramfs
                {'name': 'ProxmoxIntegration', 'enabled': True},# Integrates Proxmox VE
                {'name': 'BootloaderSetup', 'enabled': True},   # Sets up the chosen bootloader
                # {'name': 'LiveEnvironment', 'enabled': True}, # Configures live environment aspects
                {'name': 'CalamaresIntegration', 'enabled': True}, # Integrates Calamares installer framework
                {'name': 'SecurityHardening', 'enabled': True}, # Applies security hardening measures
                {'name': 'ISOGeneration', 'enabled': True}      # Generates the final ISO image
            ]
        }

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value by its key.

        Args:
            key: The top-level configuration key to retrieve (e.g., 'builder_config', 'proxmox_config').
            default: The default value to return if the key is not found. Defaults to None.

        Returns:
            The value associated with the key from the configuration data,
            or the `default` value if the key is not present.
        """
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value for a given key.

        This modifies the in-memory configuration data. To persist changes,
        call the `save()` method.

        Args:
            key: The top-level configuration key to set.
            value: The value to associate with the key.
        """
        self.data[key] = value
        logger.debug(f"Configuration key '{key}' set to: {value}")

    def save(self, data_to_save: Optional[Dict[str, Any]] = None) -> None:
        """
        Save the current (or provided) configuration data to the YAML file
        specified by `self.config_path`.

        Args:
            data_to_save: Optional. If provided, this dictionary will be saved.
                          If None, the current `self.data` will be saved.
                          Defaults to None.
        Raises:
            SystemExit: If an I/O error occurs during saving.
        """
        data: Dict[str, Any] = data_to_save if data_to_save is not None else self.data
        logger.info(f"Saving configuration to: {self.config_path}")
        try:
            with self.config_path.open('w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.debug("Configuration saved successfully.")
        except IOError as e:
            logger.error(f"I/O error saving configuration file {self.config_path}: {e}")
            sys.exit(1) # Critical error, exit
        except yaml.YAMLError as e:
            logger.error(f"Error serializing configuration to YAML at {self.config_path}: {e}")
            sys.exit(1) # Critical error, exit

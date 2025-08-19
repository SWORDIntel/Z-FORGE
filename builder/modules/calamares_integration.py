# z-forge/builder/modules/calamares_integration.py

"""
Calamares Integration Module for Z-Forge.

This module is responsible for setting up the Calamares installer within the
chroot environment. Calamares is a distribution-independent installer framework.
This module installs Calamares and its dependencies, copies custom Z-Forge
specific Calamares modules (e.g., for ZFS setup, Proxmox configuration) into
the appropriate Calamares directory, and configures Calamares settings,
including the sequence of installation steps (modules) and branding.
It also sets up a minimal desktop environment (XFCE with LightDM) to run
Calamares in the live ISO and creates a desktop launcher for it.
"""

import re
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging
import yaml
from builder.core.lockfile import BuildLockfile

class CalamaresIntegration:
    """
    Integrates the Calamares installer with custom Z-Forge modules and branding.

    The class handles:
    - Installation of Calamares and a lightweight desktop environment (XFCE).
    - Deployment of custom Calamares modules specific to Z-Forge.
    - Configuration of Calamares (e.g., module sequence, branding).
    - Creation of a desktop launcher for Calamares.
    """

    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        """
        Initialize the CalamaresIntegration module.

        Args:
            workspace: Path to the Z-Forge build workspace. Calamares will be
                       configured within `workspace/chroot`.
            config: The global build configuration dictionary. Used for any
                    Calamares-specific configurations or branding details.
        """
        self.workspace: Path = workspace
        self.config: Dict[str, Any] = config
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path: Path = workspace / "chroot"
        # It's crucial that custom Calamares modules are available at this path
        # relative to the Z-Forge project root during the build.
        self.custom_calamares_modules_source_dir: Path = Path("calamares/modules")

    def execute(self, resume_data: Optional[Dict[str, Any]] = None, lockfile: Optional[BuildLockfile] = None) -> Dict[str, Any]:
        """
        Execute the Calamares installation and configuration process.

        This is the main entry point. It orchestrates the installation of Calamares,
        deployment of custom modules, Calamares configuration, desktop environment
        setup, and launcher creation.

        Args:
            resume_data: Optional dictionary for resuming. (Not typically used
                         for this module as steps are usually run together).

        Returns:
            A dictionary containing the status of the Calamares integration.
            On success: {'status': 'success', 'calamares_version': str}
            On failure: {'status': 'error', 'error': str, 'module': str}
        """
        self.logger.info("Starting Calamares integration process...")

        try:
            # Step 1: Install Calamares and a basic desktop environment.
            self._install_calamares_and_desktop()

            # Step 2: Copy custom Z-Forge Calamares modules into the chroot.
            self._install_custom_calamares_modules()

            # Step 3: Configure Calamares settings (modules, sequence, branding).
            self._configure_calamares_settings()

            # Step 4: Set up the desktop environment for running Calamares (e.g., autologin).
            self._setup_live_desktop_environment()

            # Step 5: Create a desktop launcher for Calamares.
            self._create_calamares_launcher()

            calamares_version: str = self._get_calamares_version()
            self.logger.info(f"Calamares integration completed. Version: {calamares_version}")
            return {
                'status': 'success',
                'calamares_version': calamares_version
            }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"A command failed during Calamares integration: {e.cmd}, Return Code: {e.returncode}, Output: {e.output}, Stderr: {e.stderr}")
            return {
                'status': 'error',
                'error': f"Command failed: {' '.join(e.cmd)} - {e.stderr or e.output or str(e)}",
                'module': self.__class__.__name__
            }
        except Exception as e:
            self.logger.error(f"Calamares integration failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }

    def _run_chroot_command(self, command: List[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
        """Helper to run commands inside the chroot environment."""
        full_cmd = ["chroot", str(self.chroot_path)] + command
        self.logger.info(f"Executing in chroot: {' '.join(command)}")
        result = subprocess.run(full_cmd, check=check, capture_output=True, text=True, **kwargs)
        if result.stdout:
            self.logger.debug(f"Chroot command stdout: {result.stdout.strip()}")
        if result.stderr:
            self.logger.debug(f"Chroot command stderr: {result.stderr.strip()}")
        return result

    def _install_calamares_and_desktop(self) -> None:
        """
        Install Calamares, its dependencies, and a lightweight desktop environment (XFCE)
        into the chroot using APT.
        """
        self.logger.info("Installing Calamares and XFCE desktop environment in chroot...")

        # Ensure apt sources are appropriate for Calamares and XFCE.
        # The existing sources.list from debootstrap should be sufficient if it includes 'main'.
        # For this example, we assume the sources.list is already configured correctly by debootstrap module.
        # If Calamares required specific repositories (e.g., backports or custom), they would be added here.

        # List of packages to install:
        # - calamares: The installer framework.
        # - calamares-settings-debian: Debian-specific configurations/modules for Calamares.
        # - kde-standard & sddm: KDE Plasma desktop and SDDM display manager. (Replaces XFCE/LightDM)
        # - konsole: KDE's terminal emulator.
        # - firefox-esr: A web browser for the live environment.
        # - network-manager: For network configuration in the live environment (plasma-nm for applet).
        # - gparted: Partition editor.
        # - python3-pyqt5, python3-yaml, python3-jsonschema: Common dependencies for Calamares modules.
        packages_to_install: List[str] = [
            "calamares", "calamares-settings-debian",
            # "kde-standard", "sddm", # Already installed in live_environment.py
            "konsole", # KDE's terminal
            "firefox-esr", "network-manager", "plasma-nm", # Network management with KDE applet
            "gparted", "vim", "nano", "htop", # Standard system utilities
            "python3-pyqt5", "python3-yaml", "python3-jsonschema",
            # GTK dependencies for enhanced ZFS module
            "python3-gi", "python3-gi-cairo", "gir1.2-gtk-3.0",
            "gir1.2-pango-1.0", "python3-cairo",
            # QML dependencies for telemetry consent module
            "qml-module-qtquick2", "qml-module-qtquick-controls2",
            "qml-module-qtquick-layouts", "qml-module-qtquick-window2",
            # Hardware detection dependencies
            "pciutils", "usbutils", "dmidecode", "lshw", "hdparm",
            "smartmontools", "nvme-cli", "python3-pyudev",
            # RAID management tool dependencies  
            "mdadm", "lvm2"
        ]
        # Ensure no XFCE or LightDM packages are installed if they were in a previous version of this list
        # For example, by explicitly removing them or ensuring they are not in `packages_to_install`.
        # Since kde-standard and sddm are now installed by live_environment.py,
        # we only need to ensure Calamares and its direct GUI dependencies are here.

        # Using bash -c for a multi-line command to ensure proper execution order in chroot.
        install_script: str = f"""
set -e
apt-get update
apt-get install -y --no-install-recommends {' '.join(packages_to_install)}
apt-get clean
"""
        self._run_chroot_command(["bash", "-c", install_script])
        self.logger.info("Calamares and XFCE desktop environment installed successfully.")

    def _install_custom_calamares_modules(self) -> None:
        """
        Copy Z-Forge custom Calamares modules from the project's source directory
        into the Calamares modules directory within the chroot.
        """
        self.logger.info("Installing custom Z-Forge Calamares modules...")

        # Source directory for custom modules (expected in the Z-Forge project structure).
        # Example: project_root/calamares/modules/zfspartitionmodule/main.py
        # This path must exist on the build host.
        if not self.custom_calamares_modules_source_dir.exists() or \
           not self.custom_calamares_modules_source_dir.is_dir():
            self.logger.warning(
                f"Custom Calamares modules source directory not found or not a directory: "
                f"{self.custom_calamares_modules_source_dir.resolve()}. Skipping custom module installation."
            )
            # Depending on requirements, this could be a critical error.
            # For now, we'll allow proceeding without custom modules if the dir is missing.
            return

        # Destination directory for Calamares modules within the chroot.
        # Standard Calamares systems look for modules in /usr/lib/calamares/modules.
        calamares_modules_dest_chroot: Path = self.chroot_path / "usr/lib/calamares/modules"
        calamares_modules_dest_chroot.mkdir(parents=True, exist_ok=True)

        # Iterate over each custom module directory in the source.
        for module_src_dir in self.custom_calamares_modules_source_dir.iterdir():
            if module_src_dir.is_dir():
                module_name: str = module_src_dir.name
                self.logger.info(f"Installing custom Calamares module: {module_name}")

                module_dest_dir_chroot: Path = calamares_modules_dest_chroot / module_name
                # Use shutil.copytree for recursive copying of the module directory.
                # Ensure the destination directory does not exist before copytree or handle it.
                if module_dest_dir_chroot.exists():
                    shutil.rmtree(module_dest_dir_chroot) # Remove if exists to ensure fresh copy
                shutil.copytree(module_src_dir, module_dest_dir_chroot)

                # Make Python scripts within the copied module executable.
                # Calamares Python modules often need their main script to be executable.
                for py_file in module_dest_dir_chroot.glob("*.py"):
                    py_file.chmod(0o755) # rwxr-xr-x
                    self.logger.debug(f"Set executable bit on: {py_file}")
        self.logger.info("Custom Calamares modules installation completed.")

    def _configure_calamares_settings(self) -> None:
        """
        Configure Calamares settings by writing configuration files
        (e.g., `settings.conf`, module-specific configurations) within the chroot.
        """
        self.logger.info("Configuring Calamares settings in chroot...")
        calamares_config_dir_chroot: Path = self.chroot_path / "etc/calamares"
        calamares_modules_config_dir_chroot: Path = calamares_config_dir_chroot / "modules"

        calamares_config_dir_chroot.mkdir(parents=True, exist_ok=True)
        calamares_modules_config_dir_chroot.mkdir(parents=True, exist_ok=True)

        # Main Calamares settings (`settings.conf`).
        # This defines the overall behavior, module search paths, execution sequence, and branding.
        # 'modules-search': ['local'] tells Calamares to look for modules in its standard paths.
        # 'instances': Defines specific instances of modules if needed (e.g., multiple shellprocess runs).
        # 'sequence': Defines the order of pages and execution steps.
        # 'branding': Specifies the branding component to use.
        main_settings: Dict[str, Any] = {
            'modules-search': ['local'], # Standard search path
            'instances': [ # Examples for ZFS-specific modules if they were shellprocess based
                {'id': 'zfsbench', 'module': 'shellprocess', 'config': 'zfsbench.conf'}, # Assumes zfsbench.conf exists
                # Custom Python modules are usually just named in 'sequence'
            ],
            'sequence': [ # Defines the flow of the installer
                { # First phase: Welcome, Telemetry Consent, Locale, Keyboard, ZFS/Partitioning choice
                  # 'loadbuildspec' is a conceptual module needed early to load build_spec.yml settings
                  # (like security_hardening_profile, telemetry_endpoint_url, iso_version) into globalStorage.
                  # It would typically run in an 'init' phase or as one of the first 'show' modules if it has UI,
                  # or as a very early PythonJob if it's purely backend. For simplicity in this sequence,
                  # we assume its data is available by the time 'telemetryconsent' or later modules need it.
                  # A more robust setup would have an 'init' sequence for such tasks.
                    'show': ['welcome', 'hardwaredetect', 'telemetryconsent', 'locale', 'keyboard', 'raidcontroller', 'zfsrichconfig']
                },
                { # Second phase: Execution of tasks
                    'exec': [
                        # 'loadbuildspec', # Conceptual: if it's a job and needs to run before mount for some reason.
                                         # More likely, its data is loaded by an early Python module (non-job).
                        'hardwareconfig',  # Apply hardware-specific configurations
                        'mount',        # Mounts partitions (as defined by zfsrootselect or other partitioning modules).
                        'unpackfs',     # Extracts the SquashFS filesystem.
                        # Z-Forge specific modules / ZFS specific partitioning logic
                        # The 'zfsrootselect' module, if it's also a job module that *creates* partitions/pools,
                        # would need to run very early in 'exec', potentially before 'mount' if it does its own mounting.
                        # If 'zfsrootselect' (from show phase) only *selects* targets, then a ZFS partitioning
                        # job module needs to be here. Assuming 'zfsrootselect' (if it's a job) or a similar
                        # named job like 'zfspartition' would handle actual disk operations.
                        # For this example, let's assume 'zfsrootselect' from 'show' phase configures 'partition' job.
                        # And 'partition' job in Calamares is smart enough to handle ZFS based on what 'zfsrootselect' configured.
                        # Or, 'zfsrootselect' itself is a job module replacing 'partition'.
                        # Given the name, 'zfsrootselect' sounds like a view module. Let's assume a 'zfspartitionjob'
                        # would be needed if 'partition' can't handle ZFS.
                        # For the purpose of this integration, we'll replace 'partition' with 'zfsrootselect'
                        # and assume it's a job that does the work based on UI selections.
                        'zfsrootselect', # This now represents the job that applies ZFS partitioning/setup.
                                         # This might be too early if unpackfs targets these mounts.
                                         # Calamares sequences can be complex. Often, 'partition' is a job that
                                         # creates partitions, then 'mount' mounts them, then 'unpackfs' installs.
                                         # If 'zfsrootselect' is purely a view module, then a 'zfspartition' job
                                         # would be needed here.
                                         # Let's assume 'zfsrootselect' is a job that does partitioning.

                        'machineid',    # Sets up machine ID.
                        'fstab',        # Creates /etc/fstab (must run after ZFS datasets are mounted if they are root).
                        'locale',       # Configures system locale.
                        'keyboard',     # Configures system keyboard.
                        'localecfg',    # Persists locale config.
                        'users',        # Creates user accounts.
                        'displaymanager',# Configures display manager (LightDM).
                        'networkcfg',   # Configures network.
                        'securityhardening', # Apply security hardening measures.
                        'hwclock',      # Sets hardware clock.
                        # 'zfsboot',    # Example: ZFS bootloader specific configurations (if needed beyond grubcfg)
                        # 'proxmox',    # Example: Proxmox VE specific configurations
                        'initramfscfg', # Configures initramfs generation.
                        'initramfs',    # Generates initramfs (crucial for ZFS root).
                        'grubcfg',      # Configures GRUB.
                        'bootloader',   # Installs the bootloader (must support ZFS).
                        'opencoreinstall', # Install OpenCore for NVMe boot support if selected
                        'umount',       # Unmounts filesystems before finishing.
                        'telemetryjob'  # Send telemetry data as the very last step.
                    ]
                },
                { # Final phase
                    'show': ['finished']
                }
            ],
            # Conceptual 'loadbuildspec' module:
            # This module would be a PythonJob that runs very early (perhaps even in a dedicated 'init' sequence).
            # Its responsibility is to:
            # 1. Locate the build_spec.yml file on the ISO.
            # 2. Parse the YAML.
            # 3. Extract `iso_customization.iso_version`, `security_config.security_hardening_profile`,
            #    and `telemetry_config.telemetry_endpoint_url`.
            # 4. Insert these values into libcalamares.globalstorage using keys like:
            #    - "iso_version"
            #    - "security_hardening_profile"
            #    - "telemetry_endpoint_url"
            # This ensures these configurations are available to other modules (like telemetryjob, securityhardening).
            # If 'loadbuildspec' is a view module (e.g. part of welcome sequence to show ISO info),
            # it can still perform these actions. The key is that globalstorage is populated early.
            'branding': 'zforge', # Matches the branding component name
            'prompt-install': True, # Ask for confirmation before starting installation
            'dont-chroot': False,   # Perform operations in chroot (standard)
            'oem-setup': False,     # Not an OEM setup
            'disable-cancel': False, # Allow canceling installation
            'disable-cancel-during-exec': True # Prevent canceling during critical execution phase
        }
        settings_file_path: Path = calamares_config_dir_chroot / "settings.conf"
        with settings_file_path.open('w') as f:
            yaml.dump(main_settings, f, default_flow_style=False, sort_keys=False)
        self.logger.info(f"Calamares settings.conf written to {settings_file_path}")

        # Example: Configuration for a `shellprocess` module instance (e.g., zfsbench.conf)
        # This assumes a Calamares module named 'zfsbench.conf' is present in /etc/calamares/modules/
        # or a custom module path.
        zfs_bench_module_config: Dict[str, Any] = {
            'dontChroot': False, # Run script inside the target system chroot
            'timeout': 600,      # Timeout for the script in seconds
            'script': [          # List of commands to run
                {
                    'command': '/install/benchmarking/zfs_performance_test.sh', # Path to script on live ISO
                    'timeout': 600 # Specific timeout for this command
                }
                # Add more commands if needed for this shellprocess job
            ]
        }
        zfs_bench_conf_path: Path = calamares_modules_config_dir_chroot / "zfsbench.conf"
        with zfs_bench_conf_path.open('w') as f:
            yaml.dump(zfs_bench_module_config, f, default_flow_style=False)
        self.logger.info(f"Calamares zfsbench.conf module configuration written to {zfs_bench_conf_path}")
        
        # Hardware Detection Module Configuration
        hardware_detect_config: Dict[str, Any] = {
            'displayProfiles': True,  # Show detected hardware profiles to user
            'showRAIDControllers': True,  # Display RAID controller options
            'showStorageOptimizations': True,  # Show storage optimization options
            'enableOpenCore': True,  # Enable OpenCore installation options
            'hardwareDatabase': {
                'enableDatabaseLookup': True,
                'showOptimalSettings': True,
                'categories': [
                    'servers',
                    'workstations', 
                    'storage_systems',
                    'raid_controllers'
                ]
            }
        }
        hardware_detect_conf_path: Path = calamares_modules_config_dir_chroot / "hardwaredetect.conf"
        with hardware_detect_conf_path.open('w') as f:
            yaml.dump(hardware_detect_config, f, default_flow_style=False)
        self.logger.info(f"Hardware detection config written to {hardware_detect_conf_path}")
        
        # RAID Controller Configuration for ZFS
        raid_controller_config: Dict[str, Any] = {
            'detectControllers': True,
            'zfsMode': True,  # ZFS-focused configuration
            'showITModeWarning': True,  # Warn about IT mode requirement for ZFS
            'requireITMode': True,  # Enforce IT/HBA mode for ZFS
            'disableHardwareRAID': True,  # Disable hardware RAID options
            'managementTools': {
                'dell_perc': {
                    'tool': 'perccli',
                    'it_mode_cmd': 'perccli /c0 set personality=HBA',
                    'check_mode_cmd': 'perccli /c0 show'
                },
                'hp_smartarray': {
                    'tool': 'ssacli',
                    'it_mode_cmd': 'ssacli ctrl slot=0 modify hbamode=on',
                    'check_mode_cmd': 'ssacli ctrl all show'
                },
                'lsi_megaraid': {
                    'tool': 'megacli',
                    'it_mode_cmd': 'megacli -AdpSetProp -EnableJBOD -1 -a0',
                    'check_mode_cmd': 'megacli -AdpAllInfo -a0'
                },
                'adaptec': {
                    'tool': 'arcconf',
                    'it_mode_cmd': 'arcconf SETCONFIG 1 DIRECTATTACHEDMODE',
                    'check_mode_cmd': 'arcconf GETCONFIG 1'
                }
            },
            'zfsRecommendations': {
                'mode': 'IT/HBA',
                'reason': 'ZFS requires direct disk access for data integrity',
                'benefits': [
                    'ZFS manages redundancy and checksumming',
                    'Better performance with ZFS caching',
                    'Avoids double-caching issues',
                    'Enables ZFS self-healing'
                ]
            }
        }
        raid_conf_path: Path = calamares_modules_config_dir_chroot / "raidcontroller.conf"
        with raid_conf_path.open('w') as f:
            yaml.dump(raid_controller_config, f, default_flow_style=False)
        self.logger.info(f"RAID controller config for ZFS written to {raid_conf_path}")
        
        # Storage Configuration Module (ZFS-focused)
        storage_config: Dict[str, Any] = {
            'detectDriveTypes': ['nvme', 'sas', 'sata', 'usb'],
            'showDriveDetails': True,
            'zfsFocused': True,  # ZFS-specific optimizations
            'optimizationProfiles': {
                'nvme': {
                    'scheduler': 'none',
                    'nr_requests': 2048,
                    'zfs_use': 'primary_pool',  # Fast primary storage
                    'special_vdev': True  # Can be used for special/cache/log
                },
                'sas': {
                    'scheduler': 'mq-deadline',
                    'nr_requests': 256,
                    'read_ahead_kb': 512,
                    'zfs_use': 'primary_pool',  # Enterprise primary storage
                    'recommended_vdev': 'raidz2'  # Best for SAS arrays
                },
                'sata': {
                    'scheduler': 'mq-deadline',
                    'nr_requests': 128,
                    'read_ahead_kb': 256,
                    'zfs_use': 'secondary_pool',  # Bulk storage
                    'recommended_vdev': 'mirror'  # Best performance/redundancy
                }
            },
            'zfsRecommendations': {
                'sectorSize': {
                    'autoDetect': True,
                    'nvme': 4096,  # 4K sectors
                    'sas': 4096,   # Modern SAS uses 4K
                    'sata': 4096   # Modern SATA uses 4K
                },
                'poolGuidelines': {
                    'separatePools': 'Recommended for different disk types',
                    'mixedPools': 'Not recommended - performance issues',
                    'specialVdevs': 'Use fast NVMe for metadata/cache'
                }
            }
        }
        storage_conf_path: Path = calamares_modules_config_dir_chroot / "storageconfig.conf"
        with storage_conf_path.open('w') as f:
            yaml.dump(storage_config, f, default_flow_style=False)
        self.logger.info(f"Storage config written to {storage_conf_path}")
        
        # OpenCore Installation Module Configuration
        opencore_config: Dict[str, Any] = {
            'enabled': True,
            'version': '0.9.9',
            'installTargets': {
                'vFlash': {
                    'enabled': True,
                    'priority': 10,
                    'description': 'Dell vFlash/IDSDM embedded storage'
                },
                'usb': {
                    'enabled': True,
                    'priority': 7,
                    'description': 'USB storage device'
                },
                'secondary': {
                    'enabled': True,
                    'priority': 5,
                    'description': 'Secondary internal drive'
                },
                'sdcard': {
                    'enabled': True,
                    'priority': 6,
                    'description': 'Internal SD card storage'
                }
            },
            'features': {
                'nvmeSupport': True,
                'raidSupport': True,
                'chainloadZFS': True
            }
        }
        opencore_conf_path: Path = calamares_modules_config_dir_chroot / "opencoreinstall.conf"  
        with opencore_conf_path.open('w') as f:
            yaml.dump(opencore_config, f, default_flow_style=False)
        self.logger.info(f"OpenCore installation config written to {opencore_conf_path}")
        
        # ZFS Pool Configuration Module
        zfs_pool_config: Dict[str, Any] = {
            'enableZFS': True,
            'zfsVersion': '2.3.3',
            'poolLayouts': {
                'single': {
                    'name': 'Single Disk',
                    'description': 'No redundancy - for testing only',
                    'minDisks': 1,
                    'redundancy': 'none',
                    'warning': 'No data protection!'
                },
                'mirror': {
                    'name': 'Mirror (RAID1)',
                    'description': 'Best for 2-4 disks, excellent redundancy',
                    'minDisks': 2,
                    'redundancy': 'n-way mirror',
                    'recommended': True
                },
                'raidz1': {
                    'name': 'RAID-Z1 (RAID5)',
                    'description': 'Good for 3-5 disks, single parity',
                    'minDisks': 3,
                    'redundancy': '1 disk failure',
                    'optimal': [3, 5]
                },
                'raidz2': {
                    'name': 'RAID-Z2 (RAID6)',
                    'description': 'Good for 4-8 disks, double parity',
                    'minDisks': 4,
                    'redundancy': '2 disk failures',
                    'optimal': [4, 6, 8],
                    'recommended': True
                },
                'raidz3': {
                    'name': 'RAID-Z3',
                    'description': 'For 7+ disks, triple parity',
                    'minDisks': 7,
                    'redundancy': '3 disk failures',
                    'optimal': [7, 11]
                }
            },
            'advancedOptions': {
                'ashift': {
                    'description': 'Sector size (12=4K, 13=8K)',
                    'default': 12,
                    'detectAuto': True
                },
                'compression': {
                    'description': 'Data compression algorithm',
                    'default': 'lz4',
                    'options': ['off', 'lz4', 'gzip', 'zstd']
                },
                'encryption': {
                    'description': 'Native ZFS encryption',
                    'default': True,
                    'algorithm': 'aes-256-gcm'
                },
                'deduplication': {
                    'description': 'Block deduplication (requires lots of RAM)',
                    'default': False,
                    'warning': 'Requires 5GB RAM per TB of data!'
                }
            },
            'datasetLayout': {
                'root': {
                    'mountpoint': '/',
                    'canmount': 'noauto',
                    'compression': 'lz4'
                },
                'home': {
                    'mountpoint': '/home',
                    'canmount': 'on',
                    'compression': 'lz4'
                },
                'varlog': {
                    'mountpoint': '/var/log',
                    'canmount': 'on',
                    'compression': 'zstd',
                    'sync': 'disabled'
                },
                'proxmox': {
                    'mountpoint': '/var/lib/vz',
                    'canmount': 'on',
                    'compression': 'lz4',
                    'recordsize': '64K'
                }
            },
            'specialVdevs': {
                'cache': {
                    'description': 'L2ARC read cache (fast SSD)',
                    'enabled': True,
                    'autoDetect': 'nvme'
                },
                'log': {
                    'description': 'SLOG write cache (fast SSD with PLP)',
                    'enabled': True,
                    'requiresPLP': True,
                    'mirror': True
                },
                'special': {
                    'description': 'Metadata on fast storage',
                    'enabled': True,
                    'minSize': '10GB'
                }
            },
            'validation': {
                'checkControllerMode': True,
                'requireITMode': True,
                'warnMixedDiskTypes': True,
                'validateDiskHealth': True
            }
        }
        zfs_pool_conf_path: Path = calamares_modules_config_dir_chroot / "zfspoolconfig.conf"
        with zfs_pool_conf_path.open('w') as f:
            yaml.dump(zfs_pool_config, f, default_flow_style=False)
        self.logger.info(f"ZFS pool configuration written to {zfs_pool_conf_path}")

        # Create Z-Forge specific branding for Calamares.
        self._create_calamares_branding()
        self.logger.info("Calamares settings and branding configuration completed.")

    def _create_calamares_branding(self) -> None:
        """
        Create Z-Forge specific branding for Calamares.
        This includes a branding descriptor file (`branding.desc`) and
        any referenced images or QML slideshows.
        """
        # Branding directory within the chroot.
        branding_dir_chroot: Path = self.chroot_path / "usr/share/calamares/branding/zforge"
        # Standard Calamares looks in /usr/share/calamares/branding/<name>
        # Some configurations might use /etc/calamares/branding/<name>
        # We'll use /usr/share as it's more common for distributable branding.

        branding_dir_chroot.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Created Calamares branding directory: {branding_dir_chroot}")

        # Branding descriptor file (`branding.desc`).
        # This YAML file defines product names, logos, slideshows, and styling.
        branding_descriptor: Dict[str, Any] = {
            'componentName': 'zforge', # Must match the 'branding' key in settings.conf
            'welcomeStyleCalamares': False, # Use custom welcome or default Calamares style
            'welcomeExpandingLogo': True,   # If true, logo expands on welcome page
            'windowExpanding': 'normal',    # How the window expands (normal, fullscreen, etc.)
            'windowSize': '900,600',        # Default window size W,H
            'strings': { # Product-specific strings
                'productName': 'Z-Forge Proxmox VE Enterprise',
                'shortProductName': 'Z-Forge',
                'version': self.config.get('builder_config', {}).get('iso_version', '3.0'), # Get version from main config
                'shortVersion': f"v{self.config.get('builder_config', {}).get('iso_version', '3.0')}",
                'versionedName': f"Z-Forge Proxmox VE Enterprise v{self.config.get('builder_config', {}).get('iso_version', '3.0')}",
                'shortVersionedName': f"Z-Forge v{self.config.get('builder_config', {}).get('iso_version', '3.0')}",
                'bootloaderEntryName': 'Z-Forge Proxmox', # Name for bootloader entries
                'productUrl': 'https://github.com/z-forge', # Example URL
                'supportUrl': 'https://github.com/z-forge/issues', # Example URL
                'bugReportUrl': 'https://github.com/z-forge/issues', # Example URL
                'knownIssuesUrl': 'https://github.com/z-forge/issues' # Example URL
            },
            'images': { # Image filenames (expected within the branding_dir_chroot)
                'productLogo': 'logo.png',       # Main product logo
                'productIcon': 'icon.png',       # Window icon
                'productWelcome': 'welcome.png'  # Image for the welcome page
            },
            'slideshow': 'show.qml', # Path to QML slideshow file (relative to branding_dir_chroot)
            'style': { # Basic styling overrides
                'sidebarBackground': '#292F34', # Dark sidebar
                'sidebarText': '#FFFFFF',       # Light text on sidebar
                'sidebarTextSelect': '#292F34',  # Text color for selected item
                'sidebarTextHighlight': '#D35400'# Highlight color for selected item background/accent
            }
        }
        branding_desc_path: Path = branding_dir_chroot / "branding.desc"
        with branding_desc_path.open('w') as f:
            yaml.dump(branding_descriptor, f, default_flow_style=False, sort_keys=False)
        self.logger.info(f"Calamares branding.desc written to {branding_desc_path}")

        # Create placeholder images and QML slideshow file.
        # In a real build, these files would be copied from the Z-Forge project sources.
        # Example: Path("branding_assets/zforge/logo.png") -> branding_dir_chroot / "logo.png"
        for img_name in branding_descriptor['images'].values():
            (branding_dir_chroot / img_name).touch() # Create empty placeholder file
            self.logger.debug(f"Created placeholder branding image: {branding_dir_chroot / img_name}")

        qml_slideshow_path: Path = branding_dir_chroot / branding_descriptor['slideshow']
        # Basic QML slideshow structure
        qml_slideshow_content = """
import QtQuick 2.0
import Calamares.Slideshow 1.0

Presentation {
    Slide {
        name: "Welcome"
        source: "welcome_slide.qml" // Example reference to another QML file for the slide
    }
    // Add more slides here
}
"""
        qml_slideshow_path.write_text(qml_slideshow_content)
        # Create a dummy welcome_slide.qml
        (branding_dir_chroot / "welcome_slide.qml").write_text("""
import QtQuick 2.0
Item {
    Image {
        source: "welcome.png" // From branding.desc images
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
    }
    Column {
        anchors.centerIn: parent
        spacing: 10
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Welcome to Z-Forge Proxmox VE Enterprise Installer!"
            font.pixelSize: 28
            font.bold: true
            color: "white"
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Enterprise-ready with automatic hardware detection"
            font.pixelSize: 18
            color: "#D35400"
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Supports: Dell, HP, Supermicro servers • NVMe, SAS, RAID controllers"
            font.pixelSize: 16
            color: "#CCCCCC"
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Featuring ZFS 2.3.3 with full encryption support"
            font.pixelSize: 16
            color: "#CCCCCC"
        }
    }
}
""")
        self.logger.info(f"Placeholder QML slideshow created at {qml_slideshow_path}")
        self.logger.info("Calamares branding setup completed.")


    def _setup_live_desktop_environment(self) -> None:
        """
        Configure the KDE Plasma desktop environment for the live installer.
        This involves setting up SDDM for auto-login and ensuring Calamares
        can be launched automatically or easily by the user.
        """
        self.logger.info("Setting up live KDE desktop environment (SDDM auto-login)...")

        # Configure SDDM for auto-login as root to the Plasma session.
        # WARNING: Auto-login as root is insecure for a persistent system but acceptable for a live installer.
        sddm_conf_dir: Path = self.chroot_path / "etc/sddm.conf.d"
        sddm_conf_dir.mkdir(parents=True, exist_ok=True)
        sddm_conf_content: str = """[Autologin]
User=root
Session=plasma.desktop
Relogin=false

[Users]
HideUsers=
RememberLastUser=true
RememberLastSession=true

[General]
DisplayServer=x11
""" # Using X11 for broader compatibility in live env, Wayland could be an option.
        sddm_autologin_conf_path: Path = sddm_conf_dir / "autologin.conf"
        sddm_autologin_conf_path.write_text(sddm_conf_content)
        self.logger.info(f"SDDM configuration for auto-login written to {sddm_autologin_conf_path}")

        # Create a default .xinitrc for the root user to start KDE Plasma if SDDM fails
        # or if starting X manually (e.g., via startx).
        # For KDE, `startplasma-x11` or `startplasma-wayland` is used.
        xinitrc_content: str = """#!/bin/sh
# Start KDE Plasma session (X11)
export DESKTOP_SESSION=plasma
export XDG_SESSION_DESKTOP=KDE
export XDG_CURRENT_DESKTOP=KDE
exec startplasma-x11
"""
        xinitrc_path: Path = self.chroot_path / "root/.xinitrc"
        xinitrc_path.write_text(xinitrc_content)
        xinitrc_path.chmod(0o755) # Make it executable.
        self.logger.info(f"Root user .xinitrc for KDE Plasma created at {xinitrc_path}")

        # Autostart Calamares in KDE session
        autostart_dir_chroot: Path = self.chroot_path / "root/.config/autostart" # User-specific autostart
        # For system-wide autostart: /etc/xdg/autostart
        # Since we auto-login as root, user-specific is fine.
        autostart_dir_chroot.mkdir(parents=True, exist_ok=True)

        calamares_autostart_content: str = f"""[Desktop Entry]
Type=Application
Name=Z-Forge Installer
Comment=Launch Z-Forge Proxmox VE Installer
Exec=calamares_polkit_wrapper # Reuse the wrapper for privilege escalation
Icon=calamares
Terminal=false
X-KDE-Autostart-Phase=Setup # Ensures it starts at an appropriate time
"""
        calamares_autostart_file_path: Path = autostart_dir_chroot / "calamares-zforge-autostart.desktop"
        calamares_autostart_file_path.write_text(calamares_autostart_content)
        self.logger.info(f"Calamares autostart .desktop file created at {calamares_autostart_file_path}")
        self.logger.info("Live KDE desktop environment setup for Calamares completed.")


    def _create_calamares_launcher(self) -> None:
        """
        Create a .desktop file for launching Calamares from the KDE Plasma desktop
        or application menu in the live environment. This is a fallback if autostart fails or is disabled.
        """
        self.logger.info("Creating Calamares desktop launcher for KDE...")

        calamares_launcher_content: str = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=Install Z-Forge Proxmox VE
Comment=Install Z-Forge Proxmox VE to your hard disk
Exec=calamares_polkit_wrapper
Icon=calamares
Terminal=false
StartupNotify=true
Categories=System;Application; # Standard categories for system tools
Keywords=Installer;Z-Forge;Proxmox;
"""
        # Wrapper script (re-ensure it's created, content can be the same as before)
        calamares_wrapper_script_path_chroot = self.chroot_path / "usr/bin/calamares_polkit_wrapper"
        if not calamares_wrapper_script_path_chroot.exists():
            calamares_wrapper_script_content = """#!/bin/bash
if command -v pkexec >/dev/null 2>&1; then
    pkexec calamares
elif command -v kdesu >/dev/null 2>&1; then # kdesu is more KDE-native than gksudo
    kdesu calamares
elif command -v sudo >/dev/null 2>&1; then
    sudo calamares
else
    calamares
fi
"""
            calamares_wrapper_script_path_chroot.write_text(calamares_wrapper_script_content)
            calamares_wrapper_script_path_chroot.chmod(0o755)
            self.logger.info(f"Calamares wrapper script created/verified at {calamares_wrapper_script_path_chroot}")

        applications_dir_chroot: Path = self.chroot_path / "usr/share/applications"
        applications_dir_chroot.mkdir(parents=True, exist_ok=True)
        calamares_desktop_file_path: Path = applications_dir_chroot / "calamares-zforge.desktop"
        calamares_desktop_file_path.write_text(calamares_launcher_content)
        self.logger.info(f"Calamares .desktop file for KDE created at {calamares_desktop_file_path}")

        # KDE places desktop icons in ~/Desktop or what's configured by kdeglobals.
        # For root user, this is typically /root/Desktop.
        root_desktop_dir_chroot: Path = self.chroot_path / "root/Desktop"
        root_desktop_dir_chroot.mkdir(parents=True, exist_ok=True)
        # Ensure the target path for shutil.copy is the full file name
        shutil.copy(calamares_desktop_file_path, root_desktop_dir_chroot / "Install_Z-Forge.desktop")
        self.logger.info(f"Calamares launcher copied to root's Desktop for KDE at {root_desktop_dir_chroot}")
        self.logger.info("Calamares KDE desktop launcher creation completed.")


    def _get_calamares_version(self) -> str:
        """
        Get the installed Calamares version from within the chroot.

        Returns:
            A string representing the Calamares version, or "unknown" if
            it cannot be determined.
        """
        self.logger.info("Fetching installed Calamares version from chroot...")
        try:
            # Calamares typically supports a --version flag.
            result: subprocess.CompletedProcess = self._run_chroot_command(
                ["calamares", "--version"],
                check=True # Expects command to succeed
            )
            # The output might be multi-line or include more than just the version.
            # A common output is "Calamares 3.2.60" or similar.
            # We'll try to parse it or return the stripped stdout.
            version_output: str = result.stdout.strip()
            # Example parsing:
            match = re.search(r"Calamares\s+([\d\.]+)", version_output)
            if match:
                return match.group(1)
            return version_output # Return full output if parsing fails
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get Calamares version: {e.stderr}")
            return "unknown (command failed)"
        except FileNotFoundError: # If calamares is not in PATH within chroot
            self.logger.error("Failed to get Calamares version: 'calamares' command not found in chroot.")
            return "unknown (not found)"

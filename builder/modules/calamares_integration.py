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

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging
import yaml

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

    def execute(self, resume_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        # - xfce4 & xfce4-terminal: A lightweight desktop environment and terminal.
        # - lightdm & lightdm-gtk-greeter: A display manager and greeter for XFCE.
        # - firefox-esr: A web browser for the live environment.
        # - network-manager-gnome: For network configuration in the live environment.
        # - gparted: Partition editor (useful tool, Calamares might use its libs or own partitioner).
        # - python3-pyqt5, python3-yaml, python3-jsonschema: Common dependencies for Calamares modules.
        packages_to_install: List[str] = [
            "calamares", "calamares-settings-debian",
            "xfce4", "xfce4-terminal", "lightdm", "lightdm-gtk-greeter",
            "firefox-esr", "network-manager-gnome",
            "gparted", "vim", "nano", "htop", # Standard system utilities
            "python3-pyqt5", "python3-yaml", "python3-jsonschema"
        ]

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
                { # First phase: Welcome, Locale, Keyboard, Partitioning choice
                    'show': ['welcome', 'locale', 'keyboard', 'partition']
                },
                { # Second phase: Execution of tasks
                    'exec': [
                        'partition',    # Handles disk partitioning.
                        'mount',        # Mounts partitions.
                        'unpackfs',     # Extracts the SquashFS filesystem.
                        'machineid',    # Sets up machine ID.
                        'fstab',        # Creates /etc/fstab.
                        'locale',       # Configures system locale. (often a job, not just show)
                        'keyboard',     # Configures system keyboard. (job part)
                        'localecfg',    # Persists locale config.
                        # Z-Forge specific modules would go here:
                        # 'zfsbench',   # Example: Run ZFS benchmark (if defined as instance)
                        # 'zfspool',    # Example: Detect existing ZFS pools or configure new one
                        # 'zfstarget',  # Example: Select ZFS dataset for root
                        'users',        # Creates user accounts.
                        'displaymanager',# Configures display manager (LightDM).
                        'networkcfg',   # Configures network.
                        'hwclock',      # Sets hardware clock.
                        # 'zfsboot',    # Example: ZFS bootloader specific configurations
                        # 'proxmox',    # Example: Proxmox VE specific configurations
                        'initramfscfg', # Configures initramfs generation.
                        'initramfs',    # Generates initramfs.
                        'grubcfg',      # Configures GRUB.
                        'bootloader',   # Installs the bootloader.
                        'umount'        # Unmounts filesystems before finishing.
                    ]
                },
                { # Final phase
                    'show': ['finished']
                }
            ],
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
                'productName': 'Z-Forge Proxmox VE',
                'shortProductName': 'Z-Forge',
                'version': self.config.get('builder_config', {}).get('iso_version', '3.0'), # Get version from main config
                'shortVersion': f"v{self.config.get('builder_config', {}).get('iso_version', '3.0')}",
                'versionedName': f"Z-Forge Proxmox VE v{self.config.get('builder_config', {}).get('iso_version', '3.0')}",
                'shortVersionedName': f"Z-Forge v{self.config.get('builder_config', {}).get('iso_version', '3.0')}",
                'bootloaderEntryName': 'Z-Forge Proxmox', # Name for bootloader entries
                'productUrl': 'https://github.com/z-forge', # Example URL
                'supportUrl': 'https://github.com/z-forge/issues', # Example URL
                'bugReportUrl': 'https://github.com/z-forge/issues' # Example URL
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
    Text {
        anchors.centerIn: parent
        text: "Welcome to Z-Forge Proxmox VE Installer!"
        font.pixelSize: 24
        color: "white"
    }
}
""")
        self.logger.info(f"Placeholder QML slideshow created at {qml_slideshow_path}")
        self.logger.info("Calamares branding setup completed.")


    def _setup_live_desktop_environment(self) -> None:
        """
        Configure the lightweight XFCE desktop environment for the live installer.
        This typically involves setting up LightDM for auto-login to a specific user
        (e.g., a 'live' user, or 'root' for simplicity in installer environments).
        """
        self.logger.info("Setting up live desktop environment (LightDM auto-login for XFCE)...")

        # Configure LightDM for auto-login as root to the XFCE session.
        # This is common for live installer environments to simplify user experience.
        # WARNING: Auto-login as root is generally insecure for a persistent system
        # but acceptable for a transient live installer environment.
        lightdm_conf_content: str = """
[Seat:*]
autologin-guest=false
autologin-user=root  # Auto-login as root user
autologin-user-timeout=0 # No timeout for auto-login
autologin-session=xfce # Automatically start XFCE session

[Security]
allow-root=true # Explicitly allow root login via LightDM (may be needed)
"""
        lightdm_conf_path: Path = self.chroot_path / "etc/lightdm/lightdm.conf"
        lightdm_conf_path.parent.mkdir(parents=True, exist_ok=True) # Ensure /etc/lightdm exists
        lightdm_conf_path.write_text(lightdm_conf_content)
        self.logger.info(f"LightDM configuration for auto-login written to {lightdm_conf_path}")

        # Create a default .xinitrc for the root user to start XFCE if LightDM fails
        # or if starting X manually (e.g., via startx).
        xinitrc_content: str = """#!/bin/bash
# Start XFCE session
exec startxfce4
"""
        xinitrc_path: Path = self.chroot_path / "root/.xinitrc"
        xinitrc_path.write_text(xinitrc_content)
        xinitrc_path.chmod(0o755) # Make it executable.
        self.logger.info(f"Root user .xinitrc created at {xinitrc_path}")
        self.logger.info("Live desktop environment setup for Calamares completed.")

    def _create_calamares_launcher(self) -> None:
        """
        Create a .desktop file for launching Calamares from the XFCE desktop
        or application menu in the live environment.
        """
        self.logger.info("Creating Calamares desktop launcher...")

        # Content for the .desktop file.
        # Exec=pkexec calamares: Runs Calamares with root privileges using polkit.
        # This assumes polkit is configured to allow this without password in live session.
        # An alternative is `sudo calamares` or running Calamares directly if the
        # entire desktop session runs as root (as configured by auto-login).
        # If session is root, `Exec=calamares` might be enough. `pkexec` is safer if not root session.
        # Given autologin-user=root, `Exec=calamares` should be fine.
        # However, `pkexec calamares` is a common way Calamares is launched.
        calamares_launcher_content: str = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=Install Z-Forge Proxmox VE
Comment=Install Z-Forge Proxmox VE to your hard disk
Exec=calamares_polkit_wrapper # Use a wrapper for pkexec or direct sudo
Icon=calamares # Calamares usually installs an icon
Terminal=false
StartupNotify=true
Categories=System;
"""
        # Create a wrapper script for launching Calamares with privileges
        # This avoids issues with pkexec directly in .desktop file sometimes or provides flexibility
        calamares_wrapper_script_path_chroot = self.chroot_path / "usr/bin/calamares_polkit_wrapper"
        calamares_wrapper_script_content = """#!/bin/bash
# Wrapper to launch Calamares, ensuring it runs with root privileges.
# Tries pkexec first, falls back to gksudo/kdesudo (if available), then direct sudo.
if command -v pkexec >/dev/null 2>&1; then
    pkexec calamares
elif command -v gksudo >/dev/null 2>&1; then
    gksudo calamares
elif command -v kdesudo >/dev/null 2>&1; then
    kdesudo calamares
elif command -v sudo >/dev/null 2>&1; then
    sudo calamares
else
    # Fallback if no privilege escalation tool is found, try direct (might fail if not root)
    calamares
fi
"""
        calamares_wrapper_script_path_chroot.write_text(calamares_wrapper_script_content)
        calamares_wrapper_script_path_chroot.chmod(0o755)
        self.logger.info(f"Calamares wrapper script created at {calamares_wrapper_script_path_chroot}")


        # Path for the .desktop file in system applications directory.
        applications_dir_chroot: Path = self.chroot_path / "usr/share/applications"
        applications_dir_chroot.mkdir(parents=True, exist_ok=True)
        calamares_desktop_file_path: Path = applications_dir_chroot / "calamares-zforge.desktop"
        calamares_desktop_file_path.write_text(calamares_launcher_content)
        self.logger.info(f"Calamares .desktop file created at {calamares_desktop_file_path}")

        # Optionally, copy the .desktop file to the root user's Desktop for easy access.
        # This assumes the live session user is root, as configured in _setup_live_desktop_environment.
        root_desktop_dir_chroot: Path = self.chroot_path / "root/Desktop"
        root_desktop_dir_chroot.mkdir(parents=True, exist_ok=True)
        shutil.copy(calamares_desktop_file_path, root_desktop_dir_chroot / "Install_Z-Forge.desktop")
        self.logger.info(f"Calamares launcher copied to root's Desktop at {root_desktop_dir_chroot}")
        self.logger.info("Calamares desktop launcher creation completed.")

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

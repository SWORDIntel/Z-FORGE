import subprocess
from pathlib import Path
from typing import Dict, Optional
import logging
from builder.core.lockfile import BuildLockfile

class KDEThemeConfig:
    def __init__(self, workspace: Path, config: dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"

    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[BuildLockfile] = None) -> Dict:
        self.logger.info("Configuring KDE dark theme and conditional SDDM start...")

        # Create a script to be run by systemd to check for headless boot
        self._create_sddm_override_script()
        # Create KDE global theme configuration
        self._configure_kde_dark_theme()
        # Create script to apply theme for root user if not already globally set
        self._create_user_kde_theme_script()

        # Enable a service that will run the SDDM override script
        self._enable_sddm_override_service()

        return {'status': 'success'}

    def _create_sddm_override_script(self):
        """
        Creates a script that checks for a 'headless' kernel parameter.
        If 'headless' is present, it disables SDDM.
        Otherwise, it ensures SDDM is enabled.
        Also, applies dark theme settings.
        """
        script_content = """#!/bin/bash
# This script checks for 'headless=true' or 'zforge.headless=true' kernel parameter.
# If found, it ensures SDDM is not started. Otherwise, it ensures SDDM is started.
# It also applies KDE dark theme settings.

HEADLESS_BOOT=false
if grep -q -E '(^| )headless=true( |$)' /proc/cmdline || grep -q -E '(^| )zforge.headless=true( |$)' /proc/cmdline; then
    HEADLESS_BOOT=true
fi

if [ "$HEADLESS_BOOT" = true ]; then
    echo "Headless boot detected, disabling SDDM."
    systemctl disable sddm.service
    systemctl stop sddm.service || true # Try to stop if running, ignore error if not
else
    echo "Normal boot detected, ensuring SDDM is enabled."
    systemctl enable sddm.service
    # SDDM should be started by its own service dependencies if enabled
fi

# Apply KDE dark theme settings globally if possible, or for the root user
# This part might be better handled by placing config files directly,
# but we can also try to use kwriteconfig5 if available in chroot.

# Global theme settings (might require root and specific paths)
# These are usually set per-user, but we can try to set system-wide defaults.
# The actual application of themes for the logged-in user happens via KDE's mechanisms.
# We will primarily rely on placing config files.

# The actual theme application for the live user (root) will be handled by
# a script in /root/.config/plasma-workspace/env/ or similar.
# This script focuses on SDDM behavior.
"""
        script_path = self.chroot_path / "usr/local/bin/zforge_sddm_theme_manager.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        self.logger.info(f"SDDM override and theme manager script created at {script_path}")

    def _configure_kde_dark_theme(self):
        """
        Places KDE configuration files for a dark theme (Breeze Dark).
        These files will act as system-wide defaults or be copied to user's .config.
        """
        self.logger.info("Configuring KDE dark theme files...")

        # kdeglobals: Main theme settings
        kdeglobals_content = """[KDE]
LookFeelPackage=org.kde.breezedark.desktop

[General]
ColorScheme=BreezeDark
Name=BreezeDark
shadeSortColumn=true
widgetStyle=Breeze

[Icons]
Theme=breeze-dark
"""
        kdeglobals_dir = self.chroot_path / "etc/xdg"
        kdeglobals_dir.mkdir(parents=True, exist_ok=True)
        (kdeglobals_dir / "kdeglobals").write_text(kdeglobals_content)
        self.logger.info(f"Global kdeglobals configured at {kdeglobals_dir / 'kdeglobals'}")

        # Ensure the user's config directory will exist for the autostart/env script later
        user_config_autostart = self.chroot_path / "root/.config/autostart-scripts" # For scripts run at login
        user_config_env = self.chroot_path / "root/.config/plasma-workspace/env" # For scripts setting env vars
        user_config_autostart.mkdir(parents=True, exist_ok=True)
        user_config_env.mkdir(parents=True, exist_ok=True)


    def _create_user_kde_theme_script(self):
        """
        Creates a script that runs when the root user logs into KDE.
        This script ensures the dark theme is applied by copying global defaults
        or using kwriteconfig5 if necessary.
        """
        # This script will be placed in /root/.config/plasma-workspace/env/ to be sourced,
        # or /root/.config/autostart-scripts/ to be executed.
        # Using autostart-scripts is generally safer for commands.

        script_content = """#!/bin/bash
# Apply KDE dark theme for the current user (root) if not already set

# Path to user's kdeglobals
USER_KDEGLOBALS_DIR="$HOME/.config"
USER_KDEGLOBALS_FILE="$USER_KDEGLOBALS_DIR/kdeglobals"

# Path to system-wide kdeglobals (fallback)
SYSTEM_KDEGLOBALS_FILE="/etc/xdg/kdeglobals"

# Create user config dir if it doesn't exist
mkdir -p "$USER_KDEGLOBALS_DIR"

# If user kdeglobals doesn't exist or is missing LookFeelPackage, copy from system default
if [ ! -f "$USER_KDEGLOBALS_FILE" ] || ! grep -q "LookFeelPackage=org.kde.breezedark.desktop" "$USER_KDEGLOBALS_FILE"; then
    if [ -f "$SYSTEM_KDEGLOBALS_FILE" ]; then
        cp "$SYSTEM_KDEGLOBALS_FILE" "$USER_KDEGLOBALS_FILE"
        echo "Applied system default kdeglobals to user."
    else
        # Fallback to kwriteconfig5 if system file not found (should not happen with previous step)
        # Ensure kwriteconfig5 is available if this path is taken.
        if command -v kwriteconfig5 > /dev/null; then
            kwriteconfig5 --file "$USER_KDEGLOBALS_FILE" --group KDE --key LookFeelPackage org.kde.breezedark.desktop
            kwriteconfig5 --file "$USER_KDEGLOBALS_FILE" --group General --key ColorScheme BreezeDark
            kwriteconfig5 --file "$USER_KDEGLOBALS_FILE" --group General --key widgetStyle Breeze
            kwriteconfig5 --file "$USER_KDEGLOBALS_FILE" --group Icons --key Theme breeze-dark
            echo "Applied dark theme using kwriteconfig5."
        else
            echo "kwriteconfig5 command not found. Cannot apply theme programmatically."
        fi
    fi
fi

# Additional theme settings (example for Konsole)
KONSOLE_PROFILE_DIR="$HOME/.local/share/konsole"
mkdir -p "$KONSOLE_PROFILE_DIR"
KONSOLE_PROFILE_FILE="$KONSOLE_PROFILE_DIR/BreezeDarkZForge.profile" # Custom profile name
if [ ! -f "$KONSOLE_PROFILE_FILE" ]; then
    echo "[Appearance]" > "$KONSOLE_PROFILE_FILE"
    echo "ColorScheme=Breeze" >> "$KONSOLE_PROFILE_FILE" # Breeze scheme is dark in Breeze Dark theme
    echo "" >> "$KONSOLE_PROFILE_FILE"
    echo "[General]" >> "$KONSOLE_PROFILE_FILE"
    echo "Name=BreezeDarkZForge" >> "$KONSOLE_PROFILE_FILE"
    echo "Parent=FALLBACK/" >> "$KONSOLE_PROFILE_FILE"

    # Set as default Konsole profile
    KONSOLERC_FILE="$HOME/.config/konsolerc"
    if command -v kwriteconfig5 > /dev/null; then
        kwriteconfig5 --file "$KONSOLERC_FILE" --group "Desktop Entry" --key DefaultProfile "BreezeDarkZForge.profile"
        echo "Set BreezeDarkZForge as default Konsole profile."
    else
        # Manual setting if kwriteconfig5 is not there
        if [ -f "$KONSOLERC_FILE" ]; then
            if grep -q "DefaultProfile=" "$KONSOLERC_FILE"; then
                sed -i 's/DefaultProfile=.*/DefaultProfile=BreezeDarkZForge.profile/' "$KONSOLERC_FILE"
            else
                echo "DefaultProfile=BreezeDarkZForge.profile" >> "$KONSOLERC_FILE"
            fi
        else
            echo "[Desktop Entry]" > "$KONSOLERC_FILE"
            echo "DefaultProfile=BreezeDarkZForge.profile" >> "$KONSOLERC_FILE"
        fi
    fi
fi
"""
        # Place it in autostart-scripts to be executed
        script_path = self.chroot_path / "root/.config/autostart-scripts/apply_zforge_theme.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        self.logger.info(f"User KDE theme application script created at {script_path}")


    def _enable_sddm_override_service(self):
        """
        Creates and enables a systemd service to run the SDDM override script at boot.
        """
        service_content = f"""[Unit]
Description=Z-Forge SDDM and Theme Manager
DefaultDependencies=no
After=local-fs.target systemd-logind.service # Run after filesystems are up and before login manager typically starts
Before=display-manager.service sddm.service getty.target graphical.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/zforge_sddm_theme_manager.sh
StandardOutput=journal+console
StandardError=journal+console
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target graphical.target
"""
        service_path = self.chroot_path / "etc/systemd/system/zforge-sddm-theme-manager.service"
        service_path.parent.mkdir(parents=True, exist_ok=True)
        service_path.write_text(service_content)
        self.logger.info(f"Z-Forge SDDM/Theme Manager service file created at {service_path}")

        # Enable the service (this creates a symlink in the chroot's systemd preset dir)
        # The actual enabling is done by systemctl enable in chroot or by systemd preset mechanisms.
        # For now, just placing the file is enough. It will be enabled if systemd is told to.
        # We can also explicitly enable it here.
        try:
            subprocess.run(
                ["chroot", str(self.chroot_path), "systemctl", "enable", "zforge-sddm-theme-manager.service"],
                check=True, capture_output=True, text=True
            )
            self.logger.info("zforge-sddm-theme-manager.service enabled successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to enable zforge-sddm-theme-manager.service: {e.stderr}")
            # This might not be critical if build system handles presets later.

def add_kde_theme_module_to_build(builder_instance):
    """
    Helper function to instantiate and execute the KDEThemeConfig module.
    This function would be called from the main builder script.
    """
    kde_theme_config = KDEThemeConfig(builder_instance.workspace, builder_instance.config)
    result = kde_theme_config.execute()
    if result['status'] == 'error':
        raise Exception(f"KDEThemeConfig module failed: {result.get('error', 'Unknown error')}")
    logging.info("KDEThemeConfig module executed successfully.")

"""
To integrate this module into the Z-Forge build process:

1.  Save this code as `builder/modules/kde_theme_config.py`.
2.  In the main builder script (e.g., `builder/z-forge.py` or wherever modules are loaded):
    - Import `KDEThemeConfig` from this file.
    - Instantiate `KDEThemeConfig` with `workspace` and `config`.
    - Call its `execute()` method at an appropriate stage, likely after `LiveEnvironment`
      and `CalamaresIntegration` but before `ISOGeneration`.
    - Ensure the module is listed in `build_spec.yml` if module loading is dynamic:
      ```yaml
      modules:
        # ... other modules
        - name: KDEThemeConfig
          enabled: true
        # ... other modules
      ```
3.  Ensure `kwriteconfig5` (from `kwriteconfig` package) and `plasma-desktop` (for `org.kde.breezedark.desktop`)
    are installed in the chroot. `kde-standard` should cover this.
    The `live_environment.py` already adds `kde-standard`.
"""

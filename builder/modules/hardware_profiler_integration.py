#!/usr/bin/env python3
"""
Hardware Profiler Integration Module for Z-Forge
Adds hardware profiling tools to the LiveCD
"""

import shutil
from pathlib import Path
from typing import Dict, Optional, Any
import logging

class HardwareProfilerIntegration:
    """
    Integrates hardware profiling tools into the Live environment
    """
    
    def __init__(self, workspace: Path, config: Dict[str, Any]) -> None:
        """
        Initialize the Hardware Profiler Integration module
        
        Args:
            workspace: Build workspace path
            config: Build configuration
        """
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = workspace / "chroot"
        self.live_path = workspace / "live"
        
    def execute(self, resume_data: Optional[Dict[str, Any]] = None, 
                lockfile: Optional[Any] = None) -> Dict[str, Any]:
        """
        Execute hardware profiler integration
        """
        self.logger.info("Starting Hardware Profiler Integration...")
        
        try:
            # Copy profiler scripts to live environment
            self._install_profiler_scripts()
            
            # Create desktop shortcuts
            self._create_desktop_shortcuts()
            
            # Add to system menu
            self._add_to_menu()
            
            # Install dependencies
            self._install_dependencies()
            
            # Create documentation
            self._create_documentation()
            
            self.logger.info("Hardware Profiler Integration completed successfully")
            
            return {
                'status': 'success',
                'profiler_installed': True
            }
            
        except Exception as e:
            self.logger.error(f"Hardware Profiler Integration failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _install_profiler_scripts(self):
        """Install profiler scripts to the live environment"""
        self.logger.info("Installing profiler scripts...")
        
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        
        # Scripts to install
        scripts = [
            "profile_target_hardware.sh",
            "livecd_hardware_profiler.sh",
            "optimize_nvme_universal.sh",
            "optimize_intel_750.sh"
        ]
        
        # Copy to chroot
        target_dir = self.chroot_path / "usr/local/bin"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for script in scripts:
            source = scripts_dir / script
            if source.exists():
                target = target_dir / script
                shutil.copy2(source, target)
                target.chmod(0o755)
                self.logger.debug(f"Installed {script}")
        
        # Also copy to live environment
        if self.live_path.exists():
            live_target = self.live_path / "usr/local/bin"
            live_target.mkdir(parents=True, exist_ok=True)
            
            for script in scripts:
                source = scripts_dir / script
                if source.exists():
                    target = live_target / script
                    shutil.copy2(source, target)
                    target.chmod(0o755)
    
    def _create_desktop_shortcuts(self):
        """Create desktop shortcuts for the profiler"""
        self.logger.info("Creating desktop shortcuts...")
        
        desktop_file_content = """[Desktop Entry]
Version=1.0
Type=Application
Name=Hardware Profiler
GenericName=System Hardware Profiler
Comment=Profile system hardware for custom ISO build
Exec=/usr/local/bin/livecd_hardware_profiler.sh
Icon=computer
Terminal=false
Categories=System;Settings;
Keywords=hardware;profile;optimize;benchmark;
StartupNotify=true
"""
        
        # Create in chroot
        applications_dir = self.chroot_path / "usr/share/applications"
        applications_dir.mkdir(parents=True, exist_ok=True)
        
        desktop_file = applications_dir / "zforge-hardware-profiler.desktop"
        desktop_file.write_text(desktop_file_content)
        desktop_file.chmod(0o644)
        
        # Create autostart entry
        autostart_dir = self.chroot_path / "etc/xdg/autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        
        autostart_content = """[Desktop Entry]
Version=1.0
Type=Application
Name=Z-FORGE Hardware Profiler Welcome
Exec=/usr/local/bin/show_profiler_welcome.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        
        autostart_file = autostart_dir / "zforge-profiler-welcome.desktop"
        autostart_file.write_text(autostart_content)
        autostart_file.chmod(0o644)
        
        # Create welcome script
        welcome_script = self.chroot_path / "usr/local/bin/show_profiler_welcome.sh"
        welcome_script.write_text("""#!/bin/bash
# Show welcome message on first boot

SHOWN_FILE="$HOME/.config/zforge_profiler_shown"

if [[ ! -f "$SHOWN_FILE" ]]; then
    mkdir -p "$(dirname "$SHOWN_FILE")"
    touch "$SHOWN_FILE"
    
    if command -v zenity >/dev/null 2>&1; then
        zenity --info --width=400 --title="Z-FORGE Hardware Profiler" \\
               --text="Welcome to Z-FORGE LiveCD!\\n\\nYou can profile this system's hardware to create a custom optimized ISO.\\n\\nLook for 'Hardware Profiler' in the system menu or on the desktop."
    fi
fi
""")
        welcome_script.chmod(0o755)
    
    def _add_to_menu(self):
        """Add profiler to system menu"""
        self.logger.info("Adding to system menu...")
        
        # Create menu directory file
        menu_dir_content = """[Desktop Entry]
Version=1.0
Type=Directory
Name=Z-FORGE Tools
Comment=Z-FORGE system tools
Icon=applications-system
"""
        
        menu_dirs = self.chroot_path / "usr/share/desktop-directories"
        menu_dirs.mkdir(parents=True, exist_ok=True)
        
        dir_file = menu_dirs / "zforge-tools.directory"
        dir_file.write_text(menu_dir_content)
        dir_file.chmod(0o644)
    
    def _install_dependencies(self):
        """Install required packages for the profiler"""
        self.logger.info("Installing profiler dependencies...")
        
        # Required packages
        packages = [
            "dmidecode",      # Hardware detection
            "pciutils",       # lspci
            "usbutils",       # lsusb
            "hdparm",         # Disk info
            "smartmontools",  # SMART data
            "ethtool",        # Network info
            "zenity",         # GUI dialogs
            "bc"              # Calculator for scripts
        ]
        
        # Create package list file
        pkg_list = self.chroot_path / "tmp/profiler_packages.txt"
        pkg_list.write_text("\n".join(packages))
        
        # Install packages (will be handled by package management module)
        self.logger.info(f"Package list created: {pkg_list}")
    
    def _create_documentation(self):
        """Create documentation for the profiler"""
        self.logger.info("Creating documentation...")
        
        docs_dir = self.chroot_path / "usr/share/doc/zforge-profiler"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create README
        readme_content = """Z-FORGE Hardware Profiler
=========================

The Z-FORGE Hardware Profiler analyzes your system hardware and generates
an optimized build configuration for creating custom ISOs.

Usage from LiveCD
-----------------
1. Boot the Z-FORGE LiveCD
2. Click "Hardware Profiler" on the desktop or in the system menu
3. The profiler will analyze your hardware
4. Save the profile to a USB drive
5. Use the profile on your build system to create a custom ISO

Manual Usage
------------
Run as root for full hardware detection:
    sudo profile_target_hardware.sh

This creates:
- hardware_profile_*.yaml - Machine-readable profile
- hardware_profile_*_report.txt - Human-readable report  
- build_custom_iso.sh - Build script for custom ISO

What Gets Profiled
------------------
- CPU: Model, features, optimal compiler flags
- Memory: Size, type, speed, ZFS ARC recommendations
- Storage: Drives, types, NVMe optimizations
- Network: Interfaces, drivers, speeds
- GPU: Vendor, model, driver requirements
- System: Manufacturer, model, special features

Optimizations Applied
---------------------
Based on the detected hardware, the profiler recommends:
- Compiler optimization flags (-march, -mtune)
- ZFS pool configuration (ashift, compression)
- Kernel parameters and modules
- Memory tuning (swappiness, ARC size)
- Storage optimizations (schedulers, queues)
- Build parallelization settings

Building Custom ISO
-------------------
1. Copy the profile directory to your build machine
2. Run: ./build_custom_iso.sh
3. The script will use optimal settings for your hardware

Advanced Options
----------------
- profile_target_hardware.sh [output_dir] - Specify output directory
- Set ZFORGE_DIR environment variable to point to Z-FORGE repository

Security Note
-------------
The profiler collects hardware information only. No personal data
or file contents are included in the profile.

Support
-------
For issues or questions, visit: https://github.com/your-org/z-forge
"""
        
        readme_file = docs_dir / "README.md"
        readme_file.write_text(readme_content)
        readme_file.chmod(0o644)
        
        # Create man page
        man_dir = self.chroot_path / "usr/share/man/man1"
        man_dir.mkdir(parents=True, exist_ok=True)
        
        man_content = r""".TH ZFORGE-PROFILER 1 "2025-07-21" "Z-FORGE" "Z-FORGE Manual"
.SH NAME
zforge-profiler \- Profile system hardware for custom ISO builds
.SH SYNOPSIS
.B profile_target_hardware.sh
[output_directory]
.br
.B livecd_hardware_profiler.sh
.SH DESCRIPTION
The Z-FORGE Hardware Profiler analyzes system hardware and generates
optimized build configurations for creating custom ISOs tailored to
specific machines.
.SH OPTIONS
.TP
.I output_directory
Directory where profile files will be saved (default: ./zforge_profile)
.SH FILES
.TP
.I hardware_profile_*.yaml
Machine-readable hardware profile
.TP
.I hardware_profile_*_report.txt
Human-readable hardware report
.TP
.I build_custom_iso.sh
Generated build script with optimizations
.SH EXAMPLES
.TP
Profile current system:
.B sudo profile_target_hardware.sh
.TP
Profile and save to specific directory:
.B sudo profile_target_hardware.sh /mnt/usb/profiles
.SH SEE ALSO
.BR zforge (1),
.BR dmidecode (8),
.BR lspci (8)
.SH AUTHOR
Z-FORGE Development Team
"""
        
        man_file = man_dir / "zforge-profiler.1"
        man_file.write_text(man_content)
        man_file.chmod(0o644)
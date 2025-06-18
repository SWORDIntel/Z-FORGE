#!/usr/bin/env python3
# z-forge/builder/utils/terminal_ui.py

"""
Terminal User Interface
Provides terminal-based GUI for Z-Forge builder options
"""

import os
import sys
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    import npyscreen
except ImportError:
    # If npyscreen not available, create fallback implementation
    npyscreen = None

class TerminalUI:
    """Terminal user interface for Z-Forge"""

    def __init__(self):
        """Initialize terminal UI"""
        self.use_npyscreen = npyscreen is not None

    def display_banner(self, banner_text: str) -> None:
        """
        Display a banner with the provided text

        Args:
            banner_text: Text to display in banner
        """

        print("\033[1;34m") # Blue color
        print(banner_text)
        print("\033[0m")    # Reset color

    def get_build_options(self) -> Dict[str, Any]:
        """
        Show option selection interface and return chosen options

        Returns:
            Dict of build options
        """

        if self.use_npyscreen:
            return self._npyscreen_get_options()
        else:
            return self._basic_get_options()

    def _npyscreen_get_options(self) -> Dict[str, Any]:
        """Use npyscreen library for TUI interface"""

        class BuildOptionsForm(npyscreen.Form):
            def create(self):
                self.name = "Z-Forge Builder Options"

                # Action selection
                self.action = self.add(npyscreen.TitleSelectOne, name="Select Action:",
                                      values=["New Build", "Resume Build", "Verify Existing ISO"],
                                      scroll_exit=True)

                # Debian release
                self.release = self.add(npyscreen.TitleSelectOne, name="Debian Release:",
                                       values=["bookworm", "testing"],
                                       scroll_exit=True)

                # Proxmox version
                self.proxmox = self.add(npyscreen.TitleSelectOne, name="Proxmox Version:",
                                       values=["latest (8.x)", "specific"],
                                       scroll_exit=True)

                # Configuration file
                self.config = self.add(npyscreen.TitleFilename, name="Configuration File:",
                                      value="build_spec.yml")

                # Output file
                self.output = self.add(npyscreen.TitleFilename, name="Output ISO File:",
                                      value="zforge-proxmox-v3.iso")

            def afterEditing(self):
                self.parentApp.setNextForm(None)

        class BuildOptionsApp(npyscreen.NPSAppManaged):
            def onStart(self):
                self.form = self.addForm("MAIN", BuildOptionsForm)

        # Launch app
        app = BuildOptionsApp()
        app.run()

        # Get results from form
        actions = ["new_build", "resume_build", "verify_iso"]
        releases = ["bookworm", "testing"]

        return {
            'action': actions[app.form.action.value[0]],
            'debian_release': releases[app.form.release.value[0]],
            'proxmox_version': "latest" if app.form.proxmox.value[0] == 0 else "other",
            'config_file': app.form.config.value,
            'output_file': app.form.output.value
        }

    def _basic_get_options(self) -> Dict[str, Any]:
        """Use basic terminal input for options when npyscreen isn't available"""

        print("Z-Forge Builder Options")
        print("-----------------------")
        print("")

        # Action selection
        print("Select Action:")
        print("1. New Build")
        print("2. Resume Build")
        print("3. Verify Existing ISO")

        while True:
            try:
                action_choice = int(input("Enter option (1-3): "))
                if 1 <= action_choice <= 3:
                    break
                print("Please enter a number between 1 and 3")
            except ValueError:
                print("Please enter a number")

        actions = ["new_build", "resume_build", "verify_iso"]
        action = actions[action_choice - 1]

        # Debian release
        print("\nSelect Debian Release:")
        print("1. Bookworm")
        print("2. Testing")

        while True:
            try:
                release_choice = int(input("Enter option (1-2): "))
                if 1 <= release_choice <= 2:
                    break
                print("Please enter a number between 1 and 2")
            except ValueError:
                print("Please enter a number")

        releases = ["bookworm", "testing"]
        debian_release = releases[release_choice - 1]

        # Configuration file
        default_config = "build_spec.yml"
        config_file = input(f"\nConfiguration File [{default_config}]: ").strip()
        if not config_file:
            config_file = default_config

        # Output file
        default_output = "zforge-proxmox-v3.iso"
        output_file = input(f"\nOutput ISO File [{default_output}]: ").strip()
        if not output_file:
            output_file = default_output

        return {
            'action': action,
            'debian_release': debian_release,
            'proxmox_version': "latest",
            'config_file': config_file,
            'output_file': output_file
        }

    def show_progress(self, message: str, progress: float) -> None:
        """
        Display a progress bar

        Args:
            message: Message to display above progress bar
            progress: Progress value (0.0-1.0)
        """

        # Terminal width
        width = os.get_terminal_size().columns - 10

        # Progress bar characters
        filled = int(width * progress)
        empty = width - filled

        # Build bar
        bar = '[' + '=' * filled + ' ' * empty + ']'

        # Calculate percentage
        percent = int(progress * 100)

        # Clear line and print progress
        print(f"\r{message}:", end="")
        print(f"\r{message}: {bar} {percent}%", end="")

        # Flush output
        sys.stdout.flush()

        # If complete, add newline
        if progress >= 1.0:
            print()

    def prompt_confirmation(self, message: str) -> bool:
        """
        Ask user for yes/no confirmation

        Args:
            message: Confirmation message to display

        Returns:
            True if confirmed, False otherwise
        """

        while True:
            response = input(f"{message} (y/n): ").lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            print("Please answer 'y' or 'n'")

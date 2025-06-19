#!/usr/bin/env python3
# **calamares/modules/zfsrootselect/main.py**
""" ZFS Root Selection Module Allows user to select target dataset for installation with optional encryption """

import libcalamares
from libcalamares.utils import gettext_path, gettext_languages
import subprocess
import os
from typing import Dict, List, Optional

# **UI imports for custom widget**
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

def pretty_name():
    return "Select Installation Target"

def run():
    """Show UI for selecting ZFS dataset"""
    # Get detected pools from previous module
    pool_info = libcalamares.globalstorage.value("zfs_pools")
    if not pool_info:
        return ("No pools available", "No ZFS pools were detected in the previous step.")

    # Create custom selection dialog
    dialog = ZFSTargetSelector(pool_info)
    dialog.run()
    selected = dialog.get_selected()

    if not selected:
        return ("No selection", "You must select a target for installation.")

    # Store selection
    libcalamares.globalstorage.insert("install_pool", selected['pool'])
    libcalamares.globalstorage.insert("install_dataset", selected['dataset'])
    libcalamares.globalstorage.insert("install_mode", selected['mode'])

    # Store encryption settings
    libcalamares.globalstorage.insert("encryption_enabled", selected['encryption_enabled'])
    if selected['encryption_enabled']:
        libcalamares.globalstorage.insert("encryption_password", selected['encryption_password'])
        libcalamares.globalstorage.insert("encryption_algorithm", selected['encryption_algorithm'])

    # Log selection (without password)
    encryption_info = {k: v for k, v in selected.items() if k != 'encryption_password'}
    libcalamares.utils.debug(f"Selected: {encryption_info}")

    return None

class ZFSTargetSelector:
    """Custom GTK dialog for ZFS target selection with encryption options"""

    def __init__(self, pool_info: Dict):
        self.pool_info = pool_info
        self.selected = None
        self.builder = Gtk.Builder()
        # Build UI
        self.build_ui()

    def build_ui(self):
        """Construct the selection interface"""
        # Main window
        self.window = Gtk.Window(title="Select ZFS Installation Target")
        self.window.set_default_size(800, 650)  # Increased height for encryption options
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Main container
        vbox = Gtk.VBox(spacing=10)
        vbox.set_margin_left(20)
        vbox.set_margin_right(20)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)

        # Header
        header = Gtk.Label()
        header.set_markup("Select ZFS Pool and Dataset for Installation\n"
                         "Choose where to install Proxmox VE")
        header.set_alignment(0, 0.5)
        vbox.pack_start(header, False, False, 0)

        # Pool list
        pool_frame = Gtk.Frame(label="Available ZFS Pools")
        pool_scroll = Gtk.ScrolledWindow()
        pool_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        pool_scroll.set_min_content_height(200)

        # Create tree view for pools
        self.pool_store = Gtk.ListStore(str, str, str, str)  # name, status, health, info
        self.pool_tree = Gtk.TreeView(model=self.pool_store)

        # Add columns
        for i, title in enumerate(["Pool Name", "Status", "Health", "Information"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_resizable(True)
            self.pool_tree.append_column(column)

        # Populate pools
        for pool_name, info in self.pool_info.items():
            existing = "Has Proxmox" if any(r['is_proxmox'] for r in info['existing_roots']) else "Empty"
            self.pool_store.append([
                pool_name,
                info['pool_status'],
                info['pool_health'],
                existing
            ])

        pool_scroll.add(self.pool_tree)
        pool_frame.add(pool_scroll)
        vbox.pack_start(pool_frame, True, True, 0)

        # Installation mode selection
        mode_frame = Gtk.Frame(label="Installation Mode")
        mode_vbox = Gtk.VBox(spacing=5)
        mode_vbox.set_margin_left(10)
        mode_vbox.set_margin_right(10)
        mode_vbox.set_margin_top(10)
        mode_vbox.set_margin_bottom(10)

        # Radio buttons for mode
        self.mode_new = Gtk.RadioButton.new_with_label_from_widget(
            None, "Create new root dataset (recommended for clean install)"
        )
        self.mode_replace = Gtk.RadioButton.new_with_label_from_widget(
            self.mode_new, "Replace existing Proxmox installation (preserves pool layout)"
        )
        self.mode_alongside = Gtk.RadioButton.new_with_label_from_widget(
            self.mode_new, "Install alongside existing (dual-boot configuration)"
        )

        mode_vbox.pack_start(self.mode_new, False, False, 0)
        mode_vbox.pack_start(self.mode_replace, False, False, 0)
        mode_vbox.pack_start(self.mode_alongside, False, False, 0)
        mode_frame.add(mode_vbox)
        vbox.pack_start(mode_frame, False, False, 0)

        # Dataset name entry
        dataset_frame = Gtk.Frame(label="Target Dataset")
        dataset_hbox = Gtk.HBox(spacing=10)
        dataset_hbox.set_margin_left(10)
        dataset_hbox.set_margin_right(10)
        dataset_hbox.set_margin_top(10)
        dataset_hbox.set_margin_bottom(10)

        dataset_label = Gtk.Label("Dataset name:")
        self.dataset_entry = Gtk.Entry()
        self.dataset_entry.set_text("ROOT/proxmox")
        self.dataset_entry.set_width_chars(30)

        dataset_hbox.pack_start(dataset_label, False, False, 0)
        dataset_hbox.pack_start(self.dataset_entry, True, True, 0)
        dataset_frame.add(dataset_hbox)
        vbox.pack_start(dataset_frame, False, False, 0)

        # ===== ENCRYPTION OPTIONS =====
        encryption_frame = Gtk.Frame(label="Full Disk Encryption")
        encryption_vbox = Gtk.VBox(spacing=10)
        encryption_vbox.set_margin_left(10)
        encryption_vbox.set_margin_right(10)
        encryption_vbox.set_margin_top(10)
        encryption_vbox.set_margin_bottom(10)

        # Enable encryption checkbox
        self.encryption_check = Gtk.CheckButton(label="Enable Full Disk Encryption")
        encryption_vbox.pack_start(self.encryption_check, False, False, 0)

        # Password fields
        password_hbox = Gtk.HBox(spacing=10)
        password_label = Gtk.Label("Password:")
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_width_chars(30)
        password_hbox.pack_start(password_label, False, False, 0)
        password_hbox.pack_start(self.password_entry, True, True, 0)
        encryption_vbox.pack_start(password_hbox, False, False, 0)

        # Confirm password
        confirm_hbox = Gtk.HBox(spacing=10)
        confirm_label = Gtk.Label("Confirm Password:")
        self.confirm_entry = Gtk.Entry()
        self.confirm_entry.set_visibility(False)
        self.confirm_entry.set_width_chars(30)
        confirm_hbox.pack_start(confirm_label, False, False, 0)
        confirm_hbox.pack_start(self.confirm_entry, True, True, 0)
        encryption_vbox.pack_start(confirm_hbox, False, False, 0)

        # Encryption algorithm
        algorithm_hbox = Gtk.HBox(spacing=10)
        algorithm_label = Gtk.Label("Encryption Algorithm:")
        self.algorithm_combo = Gtk.ComboBoxText()
        for algo in ["aes-256-gcm", "aes-256-ccm", "chacha20-poly1305"]:
            self.algorithm_combo.append_text(algo)
        self.algorithm_combo.set_active(0)  # Default to aes-256-gcm
        algorithm_hbox.pack_start(algorithm_label, False, False, 0)
        algorithm_hbox.pack_start(self.algorithm_combo, True, True, 0)
        encryption_vbox.pack_start(algorithm_hbox, False, False, 0)

        encryption_frame.add(encryption_vbox)
        vbox.pack_start(encryption_frame, False, False, 0)

        # Password match indicator
        self.encryption_status = Gtk.Label()
        self.encryption_status.set_markup("")
        vbox.pack_start(self.encryption_status, False, False, 0)

        # Warning label
        self.warning_label = Gtk.Label()
        self.warning_label.set_markup("")
        vbox.pack_start(self.warning_label, False, False, 0)

        # Button box
        button_box = Gtk.HButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.END)
        button_box.set_spacing(10)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", self.on_cancel)
        self.next_button = Gtk.Button(label="Next")
        self.next_button.connect("clicked", self.on_next)
        self.next_button.set_sensitive(False)

        button_box.pack_start(cancel_button, False, False, 0)
        button_box.pack_start(self.next_button, False, False, 0)
        vbox.pack_start(button_box, False, False, 0)

        # Connect signals
        self.pool_tree.get_selection().connect("changed", self.on_pool_selected)
        self.mode_new.connect("toggled", self.on_mode_changed)
        self.mode_replace.connect("toggled", self.on_mode_changed)
        self.mode_alongside.connect("toggled", self.on_mode_changed)
        self.dataset_entry.connect("changed", self.validate_selection)

        # Encryption signals
        self.encryption_check.connect("toggled", self.on_encryption_toggled)
        self.password_entry.connect("changed", self.validate_selection)
        self.confirm_entry.connect("changed", self.validate_selection)
        self.algorithm_combo.connect("changed", self.validate_selection)

        # Initialize encryption widget states
        self.on_encryption_toggled(self.encryption_check)

        # Add to window
        self.window.add(vbox)
        self.window.show_all()

    def on_pool_selected(self, selection):
        """Handle pool selection"""
        model, treeiter = selection.get_selected()
        if treeiter:
            self.validate_selection()

    def on_mode_changed(self, widget):
        """Handle mode change"""
        if not widget.get_active():
            return

        # Update dataset name based on mode
        if self.mode_new.get_active():
            self.dataset_entry.set_text("ROOT/proxmox")
        elif self.mode_alongside.get_active():
            self.dataset_entry.set_text("ROOT/proxmox-new")

        self.validate_selection()

    def on_encryption_toggled(self, widget):
        """Handle encryption toggle"""
        enabled = widget.get_active()

        # Update sensitivity of encryption widgets
        self.password_entry.set_sensitive(enabled)
        self.confirm_entry.set_sensitive(enabled)
        self.algorithm_combo.set_sensitive(enabled)

        # Clear password fields when disabling encryption
        if not enabled:
            self.password_entry.set_text("")
            self.confirm_entry.set_text("")
            self.encryption_status.set_markup("")

        self.validate_selection()

    def validate_selection(self, widget=None):
        """Validate current selection and update UI"""
        # Get selected pool
        selection = self.pool_tree.get_selection()
        model, treeiter = selection.get_selected()

        if not treeiter:
            self.next_button.set_sensitive(False)
            return

        pool_name = model[treeiter][0]
        pool_data = self.pool_info[pool_name]
        dataset_name = self.dataset_entry.get_text().strip()

        # Validate dataset name
        if not dataset_name or '/' not in dataset_name:
            self.warning_label.set_markup(
                "<span foreground='red'>Dataset name must be in format: pool/dataset</span>"
            )
            self.next_button.set_sensitive(False)
            return

        # Check for conflicts
        if self.mode_replace.get_active():
            # Must select existing Proxmox dataset
            has_proxmox = any(r['is_proxmox'] for r in pool_data['existing_roots'])
            if not has_proxmox:
                self.warning_label.set_markup(
                    "<span foreground='red'>No existing Proxmox installation found to replace</span>"
                )
                self.next_button.set_sensitive(False)
                return

        # Check if dataset already exists
        full_dataset = f"{pool_name}/{dataset_name.split('/', 1)[1] if '/' in dataset_name else dataset_name}"
        exists = any(r['dataset'] == full_dataset for r in pool_data['existing_roots'])
        if exists and self.mode_new.get_active():
            self.warning_label.set_markup(
                "<span foreground='red'>Dataset already exists. Choose a different name or mode.</span>"
            )
            self.next_button.set_sensitive(False)
            return

        # Validate encryption settings
        encryption_valid = True
        if self.encryption_check.get_active():
            password = self.password_entry.get_text()
            confirm = self.confirm_entry.get_text()

            if not password:
                self.encryption_status.set_markup(
                    "<span foreground='red'>Encryption password cannot be empty</span>"
                )
                encryption_valid = False
            elif password != confirm:
                self.encryption_status.set_markup(
                    "<span foreground='red'>Passwords do not match</span>"
                )
                encryption_valid = False
            elif len(password) < 8:
                self.encryption_status.set_markup(
                    "<span foreground='orange'>Warning: Password is less than 8 characters</span>"
                )
                # Still valid, just a warning
                encryption_valid = True
            else:
                self.encryption_status.set_markup(
                    "<span foreground='green'>✓ Passwords match</span>"
                )
        else:
            self.encryption_status.set_markup("")

        # All good
        if encryption_valid:
            self.warning_label.set_markup("<span foreground='green'>✓ Valid selection</span>")
            self.next_button.set_sensitive(True)
        else:
            self.next_button.set_sensitive(False)

    def on_next(self, widget):
        """Handle next button"""
        # Get selections
        selection = self.pool_tree.get_selection()
        model, treeiter = selection.get_selected()
        pool_name = model[treeiter][0]
        dataset_name = self.dataset_entry.get_text().strip()

        if self.mode_new.get_active():
            mode = "new"
        elif self.mode_replace.get_active():
            mode = "replace"
        else:
            mode = "alongside"

        # Get encryption settings
        encryption_enabled = self.encryption_check.get_active()
        encryption_password = self.password_entry.get_text() if encryption_enabled else ""
        encryption_algorithm = self.algorithm_combo.get_active_text() if encryption_enabled else ""

        self.selected = {
            'pool': pool_name,
            'dataset': dataset_name,
            'mode': mode,
            'encryption_enabled': encryption_enabled,
            'encryption_password': encryption_password,
            'encryption_algorithm': encryption_algorithm
        }

        self.window.destroy()

    def on_cancel(self, widget):
        """Handle cancel"""
        self.selected = None
        self.window.destroy()

    def run(self):
        """Run the dialog"""
        Gtk.main()

    def get_selected(self):
        """Get the selection result"""
        return self.selected

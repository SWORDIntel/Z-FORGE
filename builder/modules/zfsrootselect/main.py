#!/usr/bin/env python3
# calamares/modules/zfsrootselect/main.py

"""
ZFS Root Selection Module
Allows user to select target dataset for installation
"""

import libcalamares
from libcalamares.utils import gettext_path, gettext_languages
import subprocess
import os
from typing import Dict, List, Optional

# UI imports for custom widget
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
        return ("No pools available",
                "No ZFS pools were detected in the previous step.")
    
    # Create custom selection dialog
    dialog = ZFSTargetSelector(pool_info)
    dialog.run()
    
    selected = dialog.get_selected()
    if not selected:
        return ("No selection",
                "You must select a target for installation.")
    
    # Store selection
    libcalamares.globalstorage.insert("install_pool", selected['pool'])
    libcalamares.globalstorage.insert("install_dataset", selected['dataset'])
    libcalamares.globalstorage.insert("install_mode", selected['mode'])
    
    # Log selection
    libcalamares.utils.debug(f"Selected: {selected}")
    
    return None

class ZFSTargetSelector:
    """Custom GTK dialog for ZFS target selection"""
    
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
        self.window.set_default_size(800, 600)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        
        # Main container
        vbox = Gtk.VBox(spacing=10)
        vbox.set_margin_left(20)
        vbox.set_margin_right(20)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        
        # Header
        header = Gtk.Label()
        header.set_markup("<b>Select ZFS Pool and Dataset for Installation</b>\n"
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
            None, 
            "Create new root dataset (recommended for clean install)"
        )
        self.mode_replace = Gtk.RadioButton.new_with_label_from_widget(
            self.mode_new,
            "Replace existing Proxmox installation (preserves pool layout)"
        )
        self.mode_alongside = Gtk.RadioButton.new_with_label_from_widget(
            self.mode_new,
            "Install alongside existing (dual-boot configuration)"
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
        
        # Warning label
        self.warning_label = Gtk.Label()
        self.warning_label.set_markup("<span color='red'></span>")
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
                "<span color='red'>Dataset name must be in format: pool/dataset</span>"
            )
            self.next_button.set_sensitive(False)
            return
        
        # Check for conflicts
        if self.mode_replace.get_active():
            # Must select existing Proxmox dataset
            has_proxmox = any(r['is_proxmox'] for r in pool_data['existing_roots'])
            if not has_proxmox:
                self.warning_label.set_markup(
                    "<span color='red'>No existing Proxmox installation found to replace</span>"
                )
                self.next_button.set_sensitive(False)
                return
        
        # Check if dataset already exists
        full_dataset = f"{pool_name}/{dataset_name.split('/', 1)[1] if '/' in dataset_name else dataset_name}"
        exists = any(r['dataset'] == full_dataset for r in pool_data['existing_roots'])
        
        if exists and self.mode_new.get_active():
            self.warning_label.set_markup(
                "<span color='red'>Dataset already exists. Choose a different name or mode.</span>"
            )
            self.next_button.set_sensitive(False)
            return
        
        # All good
        self.warning_label.set_markup("<span color='green'>✓ Valid selection</span>")
        self.next_button.set_sensitive(True)
    
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
        
        self.selected = {
            'pool': pool_name,
            'dataset': dataset_name,
            'mode': mode
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

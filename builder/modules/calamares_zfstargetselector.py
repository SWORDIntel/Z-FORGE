#!/usr/bin/env python3
# **calamares/modules/zfsrootselect/main.py**
""" ZFS Root Selection Module Allows user to select target dataset for installation with optional encryption """

import libcalamares
from libcalamares.utils import gettext_path, gettext_languages
import subprocess
import os
import json # Added for lsblk parsing
from typing import Dict, List, Optional

from builder.utils.zfs_command_builder import build_zpool_create_command

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

        # ===== Pool Mode Selection (Existing vs New) =====
        pool_mode_hbox = Gtk.HBox(spacing=10)
        pool_mode_hbox.set_homogeneous(True) # Make radio buttons take equal space

        self.mode_use_existing_pool_radio = Gtk.RadioButton.new_with_label(None, "Use Existing ZFS Pool")
        self.mode_use_existing_pool_radio.connect("toggled", self.on_pool_mode_changed)
        pool_mode_hbox.pack_start(self.mode_use_existing_pool_radio, True, True, 0)

        self.mode_create_new_pool_radio = Gtk.RadioButton.new_with_label_from_widget(self.mode_use_existing_pool_radio, "Create New ZFS Pool")
        self.mode_create_new_pool_radio.connect("toggled", self.on_pool_mode_changed)
        pool_mode_hbox.pack_start(self.mode_create_new_pool_radio, True, True, 0)

        vbox.pack_start(pool_mode_hbox, False, False, 5)

        # ===== Container for New Pool Creation UI =====
        self.new_pool_vbox = Gtk.VBox(spacing=10)
        # Disk Selection for New Pool
        new_pool_disks_frame = Gtk.Frame(label="Select Disks for New Pool")
        new_pool_disks_scroll = Gtk.ScrolledWindow()
        new_pool_disks_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        new_pool_disks_scroll.set_min_content_height(150) # Adjust as needed

        # Columns: Select (Toggle), Device, Model, Size
        self.new_pool_disk_store = Gtk.ListStore(bool, str, str, str)
        self.disk_selection_treeview = Gtk.TreeView(model=self.new_pool_disk_store)

        # Col 0: Selection Toggle
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_disk_selection_toggled)
        column_toggle = Gtk.TreeViewColumn("Select", renderer_toggle, active=0)
        self.disk_selection_treeview.append_column(column_toggle)

        for i, title in enumerate(["Device", "Model", "Size"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i + 1) # Offset by 1 due to toggle col
            column.set_resizable(True)
            self.disk_selection_treeview.append_column(column)

        # TODO: Populate self.new_pool_disk_store with available disks (from a globalstorage var or helper)
        # Example: self.new_pool_disk_store.append([False, "/dev/sda", "Samsung SSD 870 EVO", "500GB"])

        new_pool_disks_scroll.add(self.disk_selection_treeview)
        new_pool_disks_frame.add(new_pool_disks_scroll)
        self.new_pool_vbox.pack_start(new_pool_disks_frame, True, True, 0)

        # RAID Type for New Pool
        new_pool_raid_hbox = Gtk.HBox(spacing=10)
        new_pool_raid_label = Gtk.Label("RAID Type:")
        self.new_pool_raid_type_combo = Gtk.ComboBoxText()
        raid_types = ["stripe", "mirror", "raidz1", "raidz2", "raidz3"]
        for r_type in raid_types:
            self.new_pool_raid_type_combo.append_text(r_type)
        self.new_pool_raid_type_combo.set_active(0) # Default to stripe
        self.new_pool_raid_type_combo.connect("changed", self.on_new_pool_config_changed)
        new_pool_raid_hbox.pack_start(new_pool_raid_label, False, False, 0)
        new_pool_raid_hbox.pack_start(self.new_pool_raid_type_combo, True, True, 0)
        self.new_pool_vbox.pack_start(new_pool_raid_hbox, False, False, 0)

        # New Pool Name
        new_pool_name_hbox = Gtk.HBox(spacing=10)
        new_pool_name_label = Gtk.Label("New Pool Name:")
        self.new_pool_name_entry = Gtk.Entry()
        self.new_pool_name_entry.set_text("rpool") # Common default for root pool
        self.new_pool_name_entry.connect("changed", self.on_new_pool_config_changed)
        new_pool_name_hbox.pack_start(new_pool_name_label, False, False, 0)
        new_pool_name_hbox.pack_start(self.new_pool_name_entry, True, True, 0)
        self.new_pool_vbox.pack_start(new_pool_name_hbox, False, False, 0)

        vbox.pack_start(self.new_pool_vbox, False, False, 5) # Pack it hidden initially


        # Workload Profile Selection (self.workload_frame already defined)
        self.workload_frame = Gtk.Frame(label="Workload Profile & ZFS Properties") # Renamed for clarity
        workload_hbox = Gtk.HBox(spacing=10)
        workload_hbox.set_margin_left(10)
        workload_hbox.set_margin_right(10)
        workload_hbox.set_margin_top(10)
        workload_hbox.set_margin_bottom(10)

        workload_label = Gtk.Label("Select a profile:") # This label is inside the frame
        self.workload_combo = Gtk.ComboBoxText()
        self.workload_profiles = ["General Desktop", "Virtual Machine Host", "Bulk File Storage/NAS", "Custom"]
        for profile in self.workload_profiles:
            self.workload_combo.append_text(profile)
        self.workload_combo.set_active(0)
        self.workload_combo.connect("changed", self.on_workload_profile_changed)

        workload_hbox.pack_start(workload_label, False, False, 0)
        workload_hbox.pack_start(self.workload_combo, True, True, 0)
        self.workload_frame.add(workload_hbox) # Add HBox to the Frame
        vbox.pack_start(self.workload_frame, False, False, 5)

        # Pool list (self.pool_frame already defined)
        self.pool_frame = Gtk.Frame(label="Available ZFS Pools")
        pool_scroll = Gtk.ScrolledWindow()
        pool_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        pool_scroll.set_min_content_height(200)

        # Create tree view for pools
        self.pool_store = Gtk.ListStore(str, str, str, str)
        self.pool_tree = Gtk.TreeView(model=self.pool_store)

        for i, title in enumerate(["Pool Name", "Status", "Health", "Information"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_resizable(True)
            self.pool_tree.append_column(column)

        if self.pool_info: # Check if pool_info is not None
            for pool_name, info in self.pool_info.items():
                existing = "Has Proxmox" if any(r['is_proxmox'] for r in info['existing_roots']) else "Empty"
                self.pool_store.append([
                    pool_name,
                    info['pool_status'],
                    info['pool_health'],
                    existing
                ])

        pool_scroll.add(self.pool_tree)
        self.pool_frame.add(pool_scroll)
        vbox.pack_start(self.pool_frame, True, True, 0)

        # Installation mode selection (self.mode_frame already defined)
        self.mode_frame = Gtk.Frame(label="Installation Mode (on selected existing pool)")
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

        # ===== ADVANCED ZFS SETTINGS EXPANDER =====
        self.advanced_expander = Gtk.Expander(label="Advanced ZFS Settings")
        self.advanced_expander.set_expanded(False) # Collapsed by default
        self.advanced_expander.connect("notify::expanded", self.on_advanced_expander_toggled)

        advanced_vbox = Gtk.VBox(spacing=6)
        advanced_vbox.set_margin_left(10) # Indent content
        advanced_vbox.set_margin_right(10)
        advanced_vbox.set_margin_top(6)
        advanced_vbox.set_margin_bottom(6)
        self.advanced_expander.add(advanced_vbox) # Add VBox to Expander

        # --- ashift ---
        ashift_hbox = Gtk.HBox(spacing=10)
        ashift_label = Gtk.Label("ashift:")
        self.ashift_combo = Gtk.ComboBoxText()
        self.ashift_options = ["Auto-detect", "9", "12", "13"]
        for opt in self.ashift_options:
            self.ashift_combo.append_text(opt)
        self.ashift_combo.set_active(0)
        self.ashift_combo.connect("changed", self.on_advanced_setting_changed)
        ashift_hbox.pack_start(ashift_label, False, False, 0)
        ashift_hbox.pack_start(self.ashift_combo, True, True, 0)
        self.ashift_help_button = Gtk.Button(label=" (?)")
        self.ashift_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.ashift_help_button.set_tooltip_text(
            "ashift determines the block size alignment for the pool (2^ashift). "
            "'Auto-detect' is strongly recommended. Setting this incorrectly can severely "
            "degrade performance and is permanent. Common values for modern drives are "
            "12 (4K sectors) or 13 (8K sectors). Consult OpenZFS documentation for your specific hardware."
        )
        ashift_hbox.pack_start(self.ashift_help_button, False, False, 0)
        advanced_vbox.pack_start(ashift_hbox, False, False, 0)

        self.ashift_warning_label = Gtk.Label()
        self.ashift_warning_label.set_line_wrap(True)
        self.ashift_warning_label.set_markup("")
        advanced_vbox.pack_start(self.ashift_warning_label, False, False, 5)

        # --- Compression ---
        compression_hbox = Gtk.HBox(spacing=10)
        comp_label = Gtk.Label("Compression:")
        self.compression_algo_combo = Gtk.ComboBoxText()
        self.compression_options = ["lz4", "zstd", "gzip", "off"]
        for opt in self.compression_options:
            self.compression_algo_combo.append_text(opt)
        self.compression_algo_combo.set_active(0) # lz4 default
        self.compression_algo_combo.connect("changed", self.on_advanced_setting_changed)
        compression_hbox.pack_start(comp_label, False, False, 0)
        compression_hbox.pack_start(self.compression_algo_combo, True, True, 0)
        self.compression_algo_help_button = Gtk.Button(label=" (?)")
        self.compression_algo_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.compression_algo_help_button.set_tooltip_text(
            "Selects the compression algorithm for the ZFS datasets. `lz4` is fast and generally recommended. "
            "`zstd` offers better compression at higher CPU cost (see Zstd Level). `gzip` is older and slower. "
            "`off` disables compression. See OpenZFS docs for benchmarks."
        )
        compression_hbox.pack_start(self.compression_algo_help_button, False, False, 0)
        advanced_vbox.pack_start(compression_hbox, False, False, 0)


        self.zstd_level_hbox = Gtk.HBox(spacing=10) # HBox for Zstd level
        zstd_label = Gtk.Label("Zstd Level:")
        self.zstd_level_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 19, 1)
        self.zstd_level_scale.set_value(3) # Default Zstd level
        self.zstd_level_scale.set_digits(0)
        self.zstd_level_scale.set_hexpand(True)
        self.zstd_level_scale.connect("value-changed", self.on_advanced_setting_changed)
        self.zstd_level_hbox.pack_start(zstd_label, False, False, 0)
        self.zstd_level_hbox.pack_start(self.zstd_level_scale, True, True, 0)
        self.zstd_level_help_button = Gtk.Button(label=" (?)")
        self.zstd_level_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.zstd_level_help_button.set_tooltip_text(
             "Zstd compression level (1-19). Higher levels use more CPU for potentially better compression ratio. "
             "Levels 1-3 are fast, 4-9 good balance. Levels 10+ have significant CPU cost. Test your workload!"
        )
        self.zstd_level_hbox.pack_start(self.zstd_level_help_button, False, False, 0)
        advanced_vbox.pack_start(self.zstd_level_hbox, False, False, 0)


        self.compression_helper_label = Gtk.Label()
        self.compression_helper_label.set_line_wrap(True)
        self.compression_helper_label.set_markup("")
        advanced_vbox.pack_start(self.compression_helper_label, False, False, 5)

        # --- Core Filesystem Properties (Grid) ---
        props_grid = Gtk.Grid()
        props_grid.set_column_spacing(10)
        props_grid.set_row_spacing(5)

        # Record Size
        rs_label = Gtk.Label("Record Size:")
        self.recordsize_combo = Gtk.ComboBoxText()
        self.recordsize_options = ["Default (128K)", "16K", "64K", "256K", "512K", "1M"]
        for opt in self.recordsize_options:
            self.recordsize_combo.append_text(opt)
        self.recordsize_combo.set_active(0)
        self.recordsize_combo.connect("changed", self.on_advanced_setting_changed)
        props_grid.attach(rs_label, 0, 0, 1, 1)
        props_grid.attach(self.recordsize_combo, 1, 0, 1, 1)
        self.recordsize_help_button = Gtk.Button(label=" (?)")
        self.recordsize_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.recordsize_help_button.set_tooltip_text(
            "`recordsize` (or block size) for files. Default 128K is good for general use. "
            "Databases might prefer smaller (e.g., 16K-64K for random I/O). "
            "Large sequential files (video, backups) might benefit from larger (e.g., 1M). "
            "Mismatched recordsize to workload can impact performance."
        )
        props_grid.attach(self.recordsize_help_button, 2, 0, 1, 1)


        # atime
        atime_label = Gtk.Label("atime:")
        self.atime_combo = Gtk.ComboBoxText()
        self.atime_options = ["relatime", "off", "on"]
        for opt in self.atime_options:
            self.atime_combo.append_text(opt)
        self.atime_combo.set_active(0) # relatime default
        self.atime_combo.connect("changed", self.on_advanced_setting_changed)
        props_grid.attach(atime_label, 0, 1, 1, 1)
        props_grid.attach(self.atime_combo, 1, 1, 1, 1)
        self.atime_help_button = Gtk.Button(label=" (?)")
        self.atime_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.atime_help_button.set_tooltip_text(
            "Controls how access times are updated. `relatime` (default) updates if previous atime is older than mtime/ctime. "
            "`off` provides a performance boost by not updating atime, good for servers/VMs. `on` updates atime on every access."
        )
        props_grid.attach(self.atime_help_button, 2, 1, 1, 1)

        # xattr
        xattr_label = Gtk.Label("xattr:")
        self.xattr_combo = Gtk.ComboBoxText()
        self.xattr_options = ["sa", "posix"]
        for opt in self.xattr_options:
            self.xattr_combo.append_text(opt)
        self.xattr_combo.set_active(0) # sa default
        self.xattr_combo.connect("changed", self.on_advanced_setting_changed)
        props_grid.attach(xattr_label, 0, 2, 1, 1)
        props_grid.attach(self.xattr_combo, 1, 2, 1, 1)
        self.xattr_help_button = Gtk.Button(label=" (?)")
        self.xattr_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.xattr_help_button.set_tooltip_text(
            "`sa` (System Attribute based) stores small xattrs directly in the inode, efficient for ACLs/SELinux. "
            "`posix` stores them in hidden subdirectories, more compatible but can be slower."
        )
        props_grid.attach(self.xattr_help_button, 2, 2, 1, 1)

        # dnodesize
        dnodesize_label = Gtk.Label("dnodesize:")
        self.dnodesize_combo = Gtk.ComboBoxText()
        self.dnodesize_options = ["auto", "legacy"]
        for opt in self.dnodesize_options:
            self.dnodesize_combo.append_text(opt)
        self.dnodesize_combo.set_active(0) # auto default
        self.dnodesize_combo.connect("changed", self.on_advanced_setting_changed)
        props_grid.attach(dnodesize_label, 0, 3, 1, 1)
        props_grid.attach(self.dnodesize_combo, 1, 3, 1, 1)
        self.dnodesize_help_button = Gtk.Button(label=" (?)")
        self.dnodesize_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.dnodesize_help_button.set_tooltip_text(
            "Size of dnodes. `auto` is usually best. `legacy` uses an older, smaller dnode size. "
            "Relevant for xattr=sa, as larger dnodes can store more SA xattrs."
        )
        props_grid.attach(self.dnodesize_help_button, 2, 3, 1, 1)


        advanced_vbox.pack_start(props_grid, False, False, 5)

        # --- ARC Max Size ---
        arc_hbox = Gtk.HBox(spacing=10)
        arc_label = Gtk.Label("ARC Max Size (GB):")
        # Adjustment: min=0 (auto), max=sensible limit (e.g. 512GB or 1024GB), step=1GB
        arc_adjustment = Gtk.Adjustment(value=0, lower=0, upper=512, step_increment=1, page_increment=8, page_size=0)
        self.arc_max_gb_spinbutton = Gtk.SpinButton(adjustment=arc_adjustment, climb_rate=1, digits=0)
        self.arc_max_gb_spinbutton.connect("value-changed", self.on_advanced_setting_changed)
        arc_hbox.pack_start(arc_label, False, False, 0)
        arc_hbox.pack_start(self.arc_max_gb_spinbutton, True, True, 0)
        self.arc_max_help_button = Gtk.Button(label=" (?)")
        self.arc_max_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.arc_max_help_button.set_tooltip_text(
            "Maximum size of the Adaptive Replacement Cache (ARC) in Gigabytes. ARC is ZFS's primary disk cache in RAM. "
            "0 GB means 'auto' (typically 50% of system RAM). Manual tuning is for specific needs. "
            "Too small can hurt performance; too large can starve applications of RAM."
        )
        arc_hbox.pack_start(self.arc_max_help_button, False, False, 0)
        advanced_vbox.pack_start(arc_hbox, False, False, 0)


        self.arc_warning_label = Gtk.Label()
        self.arc_warning_label.set_line_wrap(True)
        self.arc_warning_label.set_markup("0 GB means auto (typically 50% of RAM). Check ZFS docs for details.")
        advanced_vbox.pack_start(self.arc_warning_label, False, False, 5)

        # --- L2ARC Devices ---
        l2arc_hbox = Gtk.HBox(spacing=10)
        l2arc_label = Gtk.Label("L2ARC Device(s):")
        self.l2arc_devices_entry = Gtk.Entry()
        self.l2arc_devices_entry.set_placeholder_text("/dev/sdx /dev/sdy (optional, space-separated)")
        self.l2arc_devices_entry.connect("changed", self.on_advanced_setting_changed)
        l2arc_hbox.pack_start(l2arc_label, False, False, 0)
        l2arc_hbox.pack_start(self.l2arc_devices_entry, True, True, 0)
        self.l2arc_devices_help_button = Gtk.Button(label=" (?)")
        self.l2arc_devices_help_button.set_relief(Gtk.ReliefStyle.NONE)
        self.l2arc_devices_help_button.set_tooltip_text(
            "Secondary ARC (L2ARC) devices. Enter space-separated paths to fast SSD partitions (e.g., /dev/sdb1 /dev/sdc1). "
            "L2ARC caches MAINLY metadata and RANDOM SMALL blocks by default (not large sequential reads). "
            "It can improve performance for specific workloads but adds complexity and uses some RAM. "
            "Ensure devices are dedicated and persistent."
        )
        l2arc_hbox.pack_start(self.l2arc_devices_help_button, False, False, 0)
        advanced_vbox.pack_start(l2arc_hbox, False, False, 0)


        self.l2arc_warning_label = Gtk.Label()
        self.l2arc_warning_label.set_line_wrap(True)
        self.l2arc_warning_label.set_markup(
            "<small>Enter space-separated full device paths (e.g., /dev/nvme0n1pSpecial /dev/disk/by-id/...). "
            "Ensure these are fast SSDs not used for other purposes. Incorrect devices can degrade performance or cause data loss on L2ARC.</small>"
        )
        advanced_vbox.pack_start(self.l2arc_warning_label, False, False, 5)

        # Initially update visibility of zstd slider and helper texts
        self._update_compression_ui_elements()
        self._update_ashift_warning()
        self._update_arc_warning() # Initial call for ARC warning

        vbox.pack_start(self.advanced_expander, False, False, 5) # Added padding

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

        # ===== CONFIGURATION SUMMARY PANEL =====
        self.summary_frame = Gtk.Frame(label="Configuration Summary")
        summary_vbox = Gtk.VBox() # Use a VBox for potential multiple labels or controls later
        summary_vbox.set_margin_left(10)
        summary_vbox.set_margin_right(10)
        summary_vbox.set_margin_top(10)
        summary_vbox.set_margin_bottom(10)
        self.summary_label = Gtk.Label(label="Summary will appear here.")
        self.summary_label.set_line_wrap(True)
        self.summary_label.set_xalign(0) # Align text to the left
        self.summary_label.set_selectable(True)
        summary_vbox.pack_start(self.summary_label, True, True, 0)
        self.summary_frame.add(summary_vbox)
        vbox.pack_start(self.summary_frame, False, False, 10) # Add some padding before buttons

        # Warning label for overall validation (already exists, might be repurposed or kept separate)
        self.warning_label = Gtk.Label()
        self.warning_label.set_markup("")
        vbox.pack_start(self.warning_label, False, False, 0)


        # Button box
        self.button_box = Gtk.HButtonBox() # Made it self.button_box
        self.button_box.set_layout(Gtk.ButtonBoxStyle.END)
        self.button_box.set_spacing(10)

        self.reset_button = Gtk.Button(label="Reset to Recommended Defaults")
        self.reset_button.connect("clicked", self.on_reset_to_defaults_clicked)
        # Pack reset button on the start/left side of the end-aligned box
        self.button_box.pack_start(self.reset_button, False, False, 0)


        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", self.on_cancel)
        self.next_button = Gtk.Button(label="Next")
        self.next_button.connect("clicked", self.on_next)
        self.next_button.set_sensitive(False)

        # Standard end-aligned buttons
        self.button_box.pack_end(self.next_button, False, False, 0)
        self.button_box.pack_end(cancel_button, False, False, 0)

        vbox.pack_start(self.button_box, False, False, 0)

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

        # Initial population of summary panel and UI state
        self._update_summary_panel()
        self.on_pool_mode_changed(self.mode_use_existing_pool_radio) # Set initial visibility

        # Add to window
        self.window.add(vbox)
        self.window.show_all()

    def _populate_available_disks(self):
        """Populates the disk selection treeview with available disks."""
        self.new_pool_disk_store.clear()
        try:
            # Using path for device name as it's more reliable for ZFS. Name can be like 'sda'.
            cmd = ["lsblk", "-dJO", "name,path,model,size,type,tran", "--exclude", "7,1"]
            libcalamares.utils.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            libcalamares.utils.debug(f"lsblk output: {data}")

            # Get paths of disks already in use by imported ZFS pools
            # This is a simplified check. A more robust check would involve parsing `zpool status -vLP`
            # or checking mount points more thoroughly.
            disks_in_existing_pools = set()
            if self.pool_info:
                 for pool_name, p_info in self.pool_info.items():
                    if 'vdevs' in p_info: # Assuming zfspooledetect provides vdev info
                        for vdev in p_info['vdevs']:
                            # This is highly dependent on zfspooledetect output structure
                            if 'path' in vdev and vdev['path']:
                                disks_in_existing_pools.add(os.path.realpath(vdev['path'])) # Use realpath to resolve symlinks
                            elif 'name' in vdev and vdev['name']: # Fallback if path not available
                                disks_in_existing_pools.add(os.path.realpath(f"/dev/{vdev['name']}"))


            libcalamares.utils.debug(f"Disks in existing ZFS pools: {disks_in_existing_pools}")

            for device in data.get("blockdevices", []):
                if device.get("type") == "disk":
                    dev_path = device.get("path", f"/dev/{device.get('name')}")

                    # Basic check to exclude root disk of live system (very simplistic)
                    # A more robust check would involve checking mount points from Calamares's system information.
                    if dev_path == "/dev/sda" and os.path.exists("/live/medium"): # Example common live media path
                        libcalamares.utils.debug(f"Skipping likely live media disk: {dev_path}")
                        continue

                    # Exclude disks already part of an imported ZFS pool
                    if os.path.realpath(dev_path) in disks_in_existing_pools:
                        libcalamares.utils.debug(f"Skipping disk {dev_path} already in an imported ZFS pool.")
                        continue

                    model = device.get("model", "N/A")
                    size = device.get("size", "N/A")
                    # Path is more reliable than name for ZFS.
                    self.new_pool_disk_store.append([False, dev_path, model, size])

            if not len(self.new_pool_disk_store):
                 self.warning_label.set_markup("<span foreground='orange'>No suitable disks found for new pool creation. Check connected drives.</span>")


        except FileNotFoundError:
            libcalamares.utils.error("lsblk command not found. Cannot list disks.")
            self.warning_label.set_markup("<span foreground='red'>Error: lsblk command not found. Disk listing unavailable.</span>")
        except subprocess.CalledProcessError as e:
            libcalamares.utils.error(f"lsblk command failed: {e.stderr}")
            self.warning_label.set_markup(f"<span foreground='red'>Error running lsblk: {e.stderr}. Disk listing unavailable.</span>")
        except json.JSONDecodeError as e:
            libcalamares.utils.error(f"Failed to parse lsblk JSON output: {e}")
            self.warning_label.set_markup("<span foreground='red'>Error parsing disk information. Disk listing unavailable.</span>")
        except Exception as e:
            libcalamares.utils.error(f"An unexpected error occurred while populating disks: {e}")
            self.warning_label.set_markup("<span foreground='red'>An unexpected error occurred. Disk listing unavailable.</span>")


    def on_disk_selection_toggled(self, renderer, path_str): # path is string here
        """Handle disk selection toggle in the new pool disk tree."""
        iter_ = self.new_pool_disk_store.get_iter_from_string(path_str)
        if iter_:
            current_state = self.new_pool_disk_store.get_value(iter_, 0)
            self.new_pool_disk_store.set_value(iter_, 0, not current_state)
            self.validate_selection()
            self._update_summary_panel()

    def on_new_pool_config_changed(self, widget):
        """Handle changes in new pool RAID type or name."""
        self.validate_selection()
        self._update_summary_panel()

    def on_pool_mode_changed(self, widget):
        """Handle toggling between using existing pool and creating a new one."""
        if not widget.get_active():
            return

        if self.mode_create_new_pool_radio.get_active():
            libcalamares.utils.debug("Switched to Create New Pool mode.")
            self._populate_available_disks() # Populate disks when switching to this mode
            self.new_pool_vbox.show()
            if self.pool_frame: self.pool_frame.hide()
            if self.mode_frame: self.mode_frame.hide()
            self.workload_frame.set_label("New Pool: Workload Profile & ZFS Properties")

        elif self.mode_use_existing_pool_radio.get_active():
            libcalamares.utils.debug("Switched to Use Existing Pool mode.")
            self.new_pool_vbox.hide()
            if self.pool_frame: self.pool_frame.show()
            if self.mode_frame: self.mode_frame.show()
            self.workload_frame.set_label("Workload Profile & ZFS Properties (for selected pool/dataset)")

        self.validate_selection()
        self._update_summary_panel()


    def on_reset_to_defaults_clicked(self, widget):
        """Resets all ZFS configuration options to 'General Desktop' profile defaults."""
        libcalamares.utils.debug("Reset to Recommended Defaults clicked.")
        try:
            general_desktop_idx = self.workload_profiles.index("General Desktop")
            self.workload_combo.set_active(general_desktop_idx)
        except ValueError:
            libcalamares.utils.warning("Could not find 'General Desktop' profile to reset.")
            # Fallback: set active to 0 if profile list changed, or do nothing
            if len(self.workload_profiles) > 0:
                 self.workload_combo.set_active(0)

        # The on_workload_profile_changed handler will take care of resetting
        # individual settings and updating the UI, including the summary panel.
        # self._update_summary_panel() # on_workload_profile_changed calls validate_selection, which should call summary

    def _update_summary_panel(self):
        """Updates the configuration summary panel."""
        summary_lines = []
        warnings = []

        # Profile
        profile = self.workload_combo.get_active_text()
        summary_lines.append(f"<b>Workload Profile:</b> {profile}")

        if self.mode_create_new_pool_radio.get_active():
            summary_lines.append("<b>Pool Creation Mode:</b> Create New Pool")
            new_pool_name = self.new_pool_name_entry.get_text()
            raid_type = self.new_pool_raid_type_combo.get_active_text()
            selected_disks = []
            disk_count = 0
            for row in self.new_pool_disk_store:
                if row[0]: # if selected
                    selected_disks.append(row[1]) # device path
                    disk_count +=1

            summary_lines.append(f"  <b>New Pool Name:</b> {new_pool_name if new_pool_name else '<i>Not set</i>'}")
            summary_lines.append(f"  <b>RAID Type:</b> {raid_type} ({disk_count} disk(s) selected)")
            if selected_disks:
                # Only list first few disks if many are selected, for brevity
                display_disks = selected_disks[:3] + ["..."] if len(selected_disks) > 3 else selected_disks
                summary_lines.append(f"  <b>Selected Disks:</b> {', '.join(display_disks)}")
            else: # This case should be caught by validate_selection, but good for summary too
                summary_lines.append("  <b>Selected Disks:</b> <i>None</i>")
                # warnings.append("<span foreground='red'>Error: No disks selected for new pool.</span>") # Already in validate_selection

            # RAID validation messages for summary (can mirror validate_selection or be simpler)
            min_disks_map = {"mirror": 2, "raidz1": 2, "raidz2": 3, "raidz3": 4} # Practical minimums for summary
            if raid_type != "stripe" and disk_count < min_disks_map.get(raid_type, 999):
                 warnings.append(f"<span foreground='orange'>Warning: {raid_type.upper()} typically needs at least {min_disks_map.get(raid_type)} disks.</span>")


        else: # Using existing pool
            summary_lines.append("<b>Pool Creation Mode:</b> Use Existing Pool")
            # Add details about selected existing pool if available
            selection = self.pool_tree.get_selection()
            model, treeiter = selection.get_selected()
            if treeiter:
                pool_name = model[treeiter][0]
                summary_lines.append(f"  <b>Selected Existing Pool:</b> {pool_name}")
            else:
                summary_lines.append("  <b>Selected Existing Pool:</b> <i>None selected</i>")


        # Advanced Settings (apply to new or existing, based on context)
        # Show if expander is open, or if profile is custom, or if creating new pool (always relevant for new pool)
        if self.advanced_expander.get_expanded() or profile != "General Desktop" or self.mode_create_new_pool_radio.get_active():
            summary_lines.append("<u>ZFS Properties:</u>") # Changed heading for clarity

            # ashift (Applies to new pool creation)
            ashift_val = self.ashift_combo.get_active_text()
            summary_lines.append(f"  <b>ashift:</b> {ashift_val}")
            if ashift_val != "Auto-detect":
                warnings.append("<i>Reminder: Manual ashift is permanent. Ensure it matches hardware.</i>")

            # Compression
            comp_algo = self.compression_algo_combo.get_active_text()
            comp_text = f"  <b>Compression:</b> {comp_algo}"
            if comp_algo == "zstd":
                zstd_level = self.zstd_level_scale.get_value_as_int()
                comp_text += f" (Level: {zstd_level})"
                if zstd_level > 10:
                    warnings.append(f"<span foreground='orange'>Warning: High Zstd level ({zstd_level}) has significant CPU cost.</span>")
            summary_lines.append(comp_text)

            # Core Properties (Applies to datasets on new or existing pool)
            summary_lines.append(f"    <b>Record Size:</b> {self.recordsize_combo.get_active_text()}")
            summary_lines.append(f"    <b>atime:</b> {self.atime_combo.get_active_text()}")
            summary_lines.append(f"    <b>xattr:</b> {self.xattr_combo.get_active_text()}")
            summary_lines.append(f"    <b>dnodesize:</b> {self.dnodesize_combo.get_active_text()}")

            # ARC (Applies to new pool, or system-wide if existing)
            arc_gb = self.arc_max_gb_spinbutton.get_value_as_int()
            arc_text = "Auto (default)" if arc_gb == 0 else f"{arc_gb} GB"
            summary_lines.append(f"    <b>ARC Max Size:</b> {arc_text}")
            if arc_gb > 0 and arc_gb < 4 :
                 warnings.append("<span foreground='orange'>Warning: ARC size less than 4GB might be too restrictive.</span>")

            # L2ARC (Applies to new pool)
            if self.mode_create_new_pool_radio.get_active():
                l2arc_devs = self.l2arc_devices_entry.get_text().strip()
                l2arc_text = "Not configured" if not l2arc_devs else l2arc_devs
                summary_lines.append(f"    <b>L2ARC Devices:</b> {l2arc_text}")
                if l2arc_devs:
                    if not all(dev.startswith("/dev/") for dev in l2arc_devs.split()):
                         warnings.append("<span foreground='red'>Error: L2ARC device paths seem invalid.</span>")

        # Combine summary and warnings
        full_summary_text = "\n".join(summary_lines)
        if warnings:
            full_summary_text += "\n\n<b>Notices & Warnings:</b>\n" + "\n".join(warnings)

        self.summary_label.set_markup(f"<small>{full_summary_text}</small>")


    def _update_ashift_warning(self):
        if self.ashift_combo.get_active_text() != "Auto-detect":
            self.ashift_warning_label.set_markup(
                "<span foreground='orange'><b>Warning:</b> Setting ashift manually is an advanced operation. "
                "Incorrect values (e.g., ashift=9 for 4Kn drives) can severely degrade performance "
                "and are generally not recoverable post-pool creation. "
                "Use 'Auto-detect' unless you are certain.</span>"
            )
        else:
            self.ashift_warning_label.set_markup("")

    def _update_compression_ui_elements(self):
        selected_compression = self.compression_algo_combo.get_active_text()
        self.zstd_level_hbox.set_visible(selected_compression == "zstd")

        if selected_compression == "zstd":
            level = int(self.zstd_level_scale.get_value())
            if level <= 3:
                helper_text = "<b>Zstd Level {}:</b> Good balance of speed and compression. Recommended for general use.".format(level)
            elif level <= 9:
                helper_text = "<b>Zstd Level {}:</b> Better compression, moderate CPU usage.".format(level)
            elif level <= 15:
                helper_text = "<b>Zstd Level {}:</b> High compression, significant CPU usage.".format(level)
            else: # 16-19
                helper_text = "<b>Zstd Level {}:</b> Very high compression, very high CPU usage. Use with caution.".format(level)
            self.compression_helper_label.set_markup(helper_text)
        elif selected_compression == "lz4":
            self.compression_helper_label.set_markup(
                "<b>LZ4:</b> Fast compression, good for general use and VMs. Default for many systems."
            )
        elif selected_compression == "gzip":
            self.compression_helper_label.set_markup(
                "<b>gzip (default level 6):</b> Good compression ratio, but slower than lz4 or zstd. "
                "Consider zstd for better performance at similar ratios."
            )
        elif selected_compression == "off":
            self.compression_helper_label.set_markup(
                "<b>Compression Off:</b> No compression. Suitable for already compressed data (e.g., media files)."
            )
        else:
            self.compression_helper_label.set_markup("")

    def _update_arc_warning(self):
        arc_val = self.arc_max_gb_spinbutton.get_value_as_int()
        if arc_val == 0:
            self.arc_warning_label.set_markup(
                "<small><b>Auto Mode (0 GB):</b> ZFS will typically use 50% of system RAM for ARC. This is often optimal. "
                "Manually setting ARC size is for specific tuning needs.</small>"
            )
        else:
            # This is a very rough estimation. Real available RAM is complex.
            # total_ram_gb = GLib.mem_profile().application_bytes / (1024**3) if hasattr(GLib, 'mem_profile') else 16 # Fallback
            # if arc_val > total_ram_gb * 0.75: # Warn if > 75% of (estimated) total RAM
            #     warning_text = f"<b>Warning:</b> Setting ARC to {arc_val}GB is high relative to estimated system RAM. " \
            #                    "Excessive ARC can lead to system instability or OOM issues. Ensure sufficient free RAM for other applications."
            #     self.arc_warning_label.set_markup(f"<span foreground='orange'>{warning_text}</span>")
            # else:
            self.arc_warning_label.set_markup(
                f"<small>ARC Max Size set to <b>{arc_val} GB</b>. Ensure this is a sensible value for your system's RAM and workload. "
                "Changes require a reboot to take full effect for some ZFS implementations.</small>"
            )

    def on_advanced_setting_changed(self, widget):
        """Handle changes in any advanced setting widget."""
        self._update_ashift_warning()
        self._update_compression_ui_elements()
        self._update_arc_warning()
        # L2ARC warning is static for now, could add validation if entry has text.
        self._update_summary_panel() # Update summary on any advanced change

        # If any advanced setting is changed, switch profile to "Custom"
        if self.workload_combo.get_active_text() != "Custom":
            custom_idx = -1
            for i, profile_name in enumerate(self.workload_profiles):
                if profile_name == "Custom":
                    custom_idx = i
                    break
            if custom_idx != -1:
                # Temporarily disconnect handler to prevent recursion if set_active triggers it
                self.workload_combo.disconnect_by_func(self.on_workload_profile_changed)
                self.workload_combo.set_active(custom_idx)
                self.workload_combo.connect("changed", self.on_workload_profile_changed)
                # Ensure expander is open if a setting is changed.
                if not self.advanced_expander.get_expanded(): # Check before forcing
                    self.advanced_expander.set_expanded(True) # This might re-trigger if not careful

        self.validate_selection()


    def on_workload_profile_changed(self, combo):
        """Handle workload profile selection change."""
        selected_profile = combo.get_active_text()
        libcalamares.utils.debug(f"Workload profile changed to: {selected_profile}")

        is_custom = (selected_profile == "Custom")

        # Temporarily disconnect advanced_setting_changed from all controls
        # to prevent "Custom" profile from being re-selected due to programmatic changes.
        # This is a bit verbose, ideally group these controls or have a flag.
        all_advanced_controls = [
            self.ashift_combo, self.compression_algo_combo, self.zstd_level_scale,
            self.recordsize_combo, self.atime_combo, self.xattr_combo, self.dnodesize_combo,
            self.arc_max_gb_spinbutton, self.l2arc_devices_entry
        ]
        for control in all_advanced_controls:
            if hasattr(control, 'handler_is_connected') and control.handler_is_connected(self.on_advanced_setting_changed_handler_id):
                 control.disconnect(self.on_advanced_setting_changed_handler_id)
            elif hasattr(control, '_signal_id_advanced_setting'): # Custom attribute to store handler ID
                 if control.handler_is_connected(control._signal_id_advanced_setting):
                    control.disconnect(control._signal_id_advanced_setting)


        if not is_custom:
            self.advanced_expander.set_expanded(False)
            # Apply predefined settings
            if selected_profile == "General Desktop":
                self.ashift_combo.set_active(self.ashift_options.index("Auto-detect"))
                self.compression_algo_combo.set_active(self.compression_options.index("lz4"))
                self.zstd_level_scale.set_value(3)
                self.recordsize_combo.set_active(self.recordsize_options.index("Default (128K)"))
                self.atime_combo.set_active(self.atime_options.index("relatime"))
                self.xattr_combo.set_active(self.xattr_options.index("sa"))
                self.dnodesize_combo.set_active(self.dnodesize_options.index("auto"))
                self.arc_max_gb_spinbutton.set_value(0) # Auto
                self.l2arc_devices_entry.set_text("")
            elif selected_profile == "Virtual Machine Host":
                self.ashift_combo.set_active(self.ashift_options.index("Auto-detect"))
                self.compression_algo_combo.set_active(self.compression_options.index("lz4"))
                self.zstd_level_scale.set_value(3)
                self.recordsize_combo.set_active(self.recordsize_options.index("64K"))
                self.atime_combo.set_active(self.atime_options.index("off"))
                self.xattr_combo.set_active(self.xattr_options.index("sa"))
                self.dnodesize_combo.set_active(self.dnodesize_options.index("auto"))
                self.arc_max_gb_spinbutton.set_value(0) # Auto, or a sensible portion like 8GB-16GB if RAM is known
                self.l2arc_devices_entry.set_text("") # L2ARC for VMs can be very beneficial
            elif selected_profile == "Bulk File Storage/NAS":
                self.ashift_combo.set_active(self.ashift_options.index("Auto-detect"))
                self.compression_algo_combo.set_active(self.compression_options.index("zstd"))
                self.zstd_level_scale.set_value(6)
                self.recordsize_combo.set_active(self.recordsize_options.index("1M"))
                self.atime_combo.set_active(self.atime_options.index("off"))
                self.xattr_combo.set_active(self.xattr_options.index("sa"))
                self.dnodesize_combo.set_active(self.dnodesize_options.index("auto"))
                self.arc_max_gb_spinbutton.set_value(0) # Auto, or a larger portion if RAM is plentiful
                self.l2arc_devices_entry.set_text("")
        else: # Custom profile selected
            self.advanced_expander.set_expanded(True)
            # On "Custom", we don't change settings, user has full control.
            # Ensure all controls within expander are sensitive
            # Make sure all controls within expander are sensitive
            for child_widget in self.advanced_expander.get_child().get_children():
                 # This includes HBoxes and the Grid. For finer control:
                 # Iterate through actual input widgets (combos, scale)
                if hasattr(child_widget, 'set_sensitive'): # Check if it's a Gtk.Widget
                    child_widget.set_sensitive(True)
                # For HBoxes containing other widgets, iterate its children
                if isinstance(child_widget, Gtk.Box):
                    for sub_child in child_widget.get_children():
                        if hasattr(sub_child, 'set_sensitive'):
                             sub_child.set_sensitive(True)
                if isinstance(child_widget, Gtk.Grid):
                     for sub_child in child_widget.get_children():
                        if hasattr(sub_child, 'set_sensitive'):
                             sub_child.set_sensitive(True)


        self._update_ashift_warning()
        self._update_compression_ui_elements()
        self._update_arc_warning() # Ensure ARC warning is also updated with profile changes
        self._update_summary_panel() # Update summary when profile changes
        self.validate_selection()

    def on_advanced_expander_toggled(self, expander, param):
        """Handle expander state change."""
        is_expanded = expander.get_expanded()
        libcalamares.utils.debug(f"Advanced settings expander {'expanded' if is_expanded else 'collapsed'}.")

        current_profile = self.workload_combo.get_active_text()
        if is_expanded and current_profile != "Custom":
            # User manually expanded, switch to Custom profile
            custom_idx = -1
            for i, profile_name in enumerate(self.workload_profiles):
                if profile_name == "Custom":
                    custom_idx = i
                    break
            if custom_idx != -1:
                self.workload_combo.set_active(custom_idx) # This will trigger on_workload_profile_changed
        elif not is_expanded and current_profile == "Custom":
            # User collapsed while on Custom. This is fine, settings are preserved.
            # Or, one could argue to switch to a default profile, but that might be annoying.
            pass

        self._update_summary_panel() # Update summary when expander state changes
        self.validate_selection() # Re-validate if needed


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
        self._update_summary_panel() # Update summary if pool selection changes things (e.g. existing datasets) - TBD

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
        self._update_summary_panel() # Encryption status might be part of summary

    def validate_selection(self, widget=None):
        """Validate current selection and update UI"""
        # This function needs to be mode-aware.
        self._update_summary_panel() # Keep summary fresh with validation changes.

        if self.mode_create_new_pool_radio.get_active():
            # Validation for new pool creation
            new_pool_name = self.new_pool_name_entry.get_text().strip()
            if not new_pool_name:
                self.warning_label.set_markup("<span foreground='red'>New pool name cannot be empty.</span>")
                self.next_button.set_sensitive(False)
                return
            # Basic ZFS pool name validation (alphanumeric, underscores, hyphens, periods)
            # Must start with a letter, cannot end with a hyphen.
            if not new_pool_name[0].isalpha() or not all(c.isalnum() or c in ['_', '-', '.'] for c in new_pool_name) or new_pool_name.endswith('-'):
                 self.warning_label.set_markup(f"<span foreground='red'>Invalid pool name: '{new_pool_name}'. Use letters, numbers, _, -, . and start with a letter.</span>")
                 self.next_button.set_sensitive(False)
                 return

            selected_disks_count = sum(1 for row in self.new_pool_disk_store if row[0])
            if selected_disks_count == 0:
                self.warning_label.set_markup("<span foreground='red'>No disks selected for the new pool.</span>")
                self.next_button.set_sensitive(False)
                return

            raid_type = self.new_pool_raid_type_combo.get_active_text()
            min_disks = {
                "stripe": 1, "mirror": 2,
                "raidz1": 3, # Common recommendation: N+1, N>=2 (so 2 data + 1 parity)
                "raidz2": 4, # Common recommendation: N+2, N>=2 (so 2 data + 2 parity is min, better 3+ data) -> using slightly higher practical minimums
                "raidz3": 5  # Common recommendation: N+3, N>=2 (so 2 data + 3 parity is min, better 3+ data)
            }

            if selected_disks_count < min_disks.get(raid_type, 999): # Use 999 if raid_type not in map (should not happen)
                self.warning_label.set_markup(
                    f"<span foreground='red'>{raid_type.upper()} requires at least {min_disks.get(raid_type)} disk(s). "
                    f"Selected: {selected_disks_count}.</span>"
                )
                self.next_button.set_sensitive(False)
                return

            # Dataset name for new pool (can be simpler, e.g., always "ROOT/proxmox")
            dataset_name = self.dataset_entry.get_text().strip()
            if not dataset_name or '/' not in dataset_name : # Basic check
                 self.warning_label.set_markup("<span foreground='red'>Root dataset name for new pool must be in format: parent/child (e.g., ROOT/proxmox).</span>")
                 self.next_button.set_sensitive(False)
                 return

        else: # Using existing pool
            selection = self.pool_tree.get_selection()
            model, treeiter = selection.get_selected()

            if not treeiter:
                self.warning_label.set_markup("<span foreground='red'>No existing ZFS pool selected.</span>")
                self.next_button.set_sensitive(False)
                return

            pool_name = model[treeiter][0]
            pool_data = self.pool_info[pool_name] # Ensure pool_info is valid
            dataset_name = self.dataset_entry.get_text().strip()

            if not dataset_name or '/' not in dataset_name:
                self.warning_label.set_markup("<span foreground='red'>Target dataset name must be in format: pool/dataset (e.g., ROOT/proxmox).</span>")
                self.next_button.set_sensitive(False)
                return

            if self.mode_replace.get_active():
                has_proxmox = any(r['is_proxmox'] for r in pool_data.get('existing_roots', []))
                if not has_proxmox:
                    self.warning_label.set_markup("<span foreground='red'>No existing Proxmox installation found to replace in selected pool.</span>")
                    self.next_button.set_sensitive(False)
                    return

            full_dataset_path = f"{pool_name}/{dataset_name.split('/', 1)[1] if '/' in dataset_name else dataset_name}"
            exists = any(r['dataset'] == full_dataset_path for r in pool_data.get('existing_roots', []))
            if exists and self.mode_new.get_active(): # mode_new is "Create new root dataset on existing pool"
                self.warning_label.set_markup("<span foreground='red'>Dataset already exists on selected pool. Choose different name or mode.</span>")
                self.next_button.set_sensitive(False)
                return

        # Common validation: Encryption (applies to both new and existing pool scenarios)
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
        # Determine operation mode (new_pool or existing_pool)
        if self.mode_create_new_pool_radio.get_active():
            libcalamares.globalstorage.insert("zfs_operation_mode", "new_pool")

            # --- Collect data for new pool creation ---
            collected_pool_name = self.new_pool_name_entry.get_text().strip()
            collected_raid_type = self.new_pool_raid_type_combo.get_active_text()

            selected_disks = []
            for row in self.new_pool_disk_store:
                if row[0]: # If selected
                    selected_disks.append(row[1]) # Get device path

            ashift_text = self.ashift_combo.get_active_text()
            collected_ashift = int(ashift_text) if ashift_text != "Auto-detect" else None

            # Pool properties (currently only ashift is explicitly set at pool level by build_zpool_create_command)
            pool_props = {} # Empty for now, can be extended

            # Root filesystem options
            root_fs_opts = {}
            comp_algo = self.compression_algo_combo.get_active_text()
            if comp_algo == "zstd":
                zstd_level = self.zstd_level_scale.get_value_as_int()
                root_fs_opts["compression"] = f"zstd-{zstd_level}"
            else:
                root_fs_opts["compression"] = comp_algo

            record_size_text = self.recordsize_combo.get_active_text()
            if record_size_text == "Default (128K)":
                root_fs_opts["recordsize"] = "128K"
            else:
                root_fs_opts["recordsize"] = record_size_text

            root_fs_opts["atime"] = self.atime_combo.get_active_text()
            root_fs_opts["xattr"] = self.xattr_combo.get_active_text()
            root_fs_opts["dnodesize"] = self.dnodesize_combo.get_active_text()

            encryption_enabled = self.encryption_check.get_active()
            if encryption_enabled:
                root_fs_opts["encryption"] = "on" # Standard ZFS property
                # build_zpool_create_command doesn't handle keyformat/keylocation directly for root_fs_opts.
                # These are usually handled by `zfs create -o keyformat=passphrase ...` after pool.
                # For `zpool create`, encryption is simpler: just `-O encryption=on`.
                # The password needs to be handled by Calamares during the `zpool create` or subsequent `zfs load-key`.
                # We will store these separately for Calamares to use.
                libcalamares.globalstorage.insert("zfs_encryption_keyformat", "passphrase")
                libcalamares.globalstorage.insert("zfs_encryption_keylocation", "prompt")


            # L2ARC devices
            l2arc_devices_str = self.l2arc_devices_entry.get_text().strip()
            collected_l2arc_devices = l2arc_devices_str.split() if l2arc_devices_str else []

            # SLOG devices (not in UI yet)
            collected_slog_devices = []

            # altroot - Calamares usually provides this as a job parameter (e.g. globalStorage['rootMountPoint'])
            # For command generation testing, a placeholder.
            # In a real scenario, this should be the actual target chroot path.
            altroot_path = libcalamares.globalstorage.value("rootMountPoint") or "/mnt"


            # Mountpoint for the pool's root dataset.
            # For a root pool, this is typically '/', meaning it will be mounted at altroot_path.
            # If self.dataset_entry is "ROOT/pve", the actual root dataset of the pool is just the pool itself.
            # Child datasets are created later.
            # The mountpoint for the pool itself. If datasets within it have their own mountpoints,
            # this can be 'none' or 'legacy'. For a root filesystem, it's often '/'.
            pool_mountpoint = "/" # This will make the pool's root dataset mount at altroot_path

            try:
                zpool_command_args = build_zpool_create_command(
                    pool_name=collected_pool_name,
                    raid_type=collected_raid_type,
                    disks=selected_disks,
                    ashift=collected_ashift,
                    properties=pool_props, # Pool level -o
                    root_fs_options=root_fs_opts, # Root dataset -O
                    mountpoint=pool_mountpoint,
                    altroot=altroot_path,
                    log_devices=collected_slog_devices, # SLOG
                    cache_devices=collected_l2arc_devices # L2ARC
                )
                libcalamares.globalstorage.insert("zfs_new_pool_command", zpool_command_args)
                libcalamares.utils.debug(f"Generated zpool create command: {' '.join(zpool_command_args)}")

            except ValueError as e:
                libcalamares.utils.error(f"Error building zpool command: {e}")
                # This should ideally not happen if validate_selection is robust
                # but good to have a fallback.
                self.warning_label.set_markup(f"<span foreground='red'>Error: {e}</span>")
                self.next_button.set_sensitive(False)
                return # Prevent window close

            libcalamares.globalstorage.insert("zfs_new_pool_name", collected_pool_name)
            # The 'install_dataset' for a new pool refers to the intended root filesystem dataset path *within* the new pool.
            # e.g. if new pool is 'rpool' and dataset_entry is 'ROOT/pve', then install_dataset is 'rpool/ROOT/pve'
            # However, zpool create only creates 'rpool'. 'ROOT/pve' must be created by subsequent zfs create commands.
            # For now, store the user's intended root dataset path relative to the new pool.
            install_dataset_on_new_pool = self.dataset_entry.get_text().strip()
            libcalamares.globalstorage.insert("zfs_install_dataset_relative", install_dataset_on_new_pool)


            # Store global settings that also apply to new pool scenario
            libcalamares.globalstorage.insert("zfs_arc_max_gb", int(self.arc_max_gb_spinbutton.get_value()))
            libcalamares.globalstorage.insert("zfs_encryption_enabled", encryption_enabled)
            if encryption_enabled:
                libcalamares.globalstorage.insert("zfs_encryption_password", self.password_entry.get_text())
            else:
                libcalamares.globalstorage.insert("zfs_encryption_password", "")

            # For the main 'selected' dict to return to Calamares core for summary
            self.selected = {
                'pool': collected_pool_name, # The new pool name
                'dataset': f"{collected_pool_name}/{install_dataset_on_new_pool.split('/',1)[1] if '/' in install_dataset_on_new_pool else install_dataset_on_new_pool}", # Full path for install
                'mode': "new_pool", # Custom mode indicating new pool
                'encryption_enabled': encryption_enabled,
                # Not storing password in self.selected for security in logs
                'encryption_algorithm': self.algorithm_combo.get_active_text() if encryption_enabled else ""
            }

        else: # Use Existing Pool Mode
            libcalamares.globalstorage.insert("zfs_operation_mode", "existing_pool")

            selection = self.pool_tree.get_selection()
            model, treeiter = selection.get_selected()
            if not treeiter: # Should be caught by validate_selection
                self.window.destroy() # Or show error
                return

            pool_name = model[treeiter][0]
            dataset_name_suffix = self.dataset_entry.get_text().strip() # e.g. ROOT/proxmox

            # Construct full dataset path
            # If dataset_name_suffix contains '/', it's like "parent/child", use the part after first '/'
            # Otherwise, assume it's a direct child of the pool_name.
            # This logic might need refinement based on how users are expected to input dataset names.
            # For now, assume dataset_entry is relative to the pool root if it doesn't contain the pool name.
            if '/' in dataset_name_suffix:
                 actual_dataset_name = dataset_name_suffix # e.g. ROOT/proxmox
            else: # E.g. user types 'mydata' -> pool_name/mydata
                 actual_dataset_name = dataset_name_suffix

            full_dataset_path = f"{pool_name}/{actual_dataset_name}"


            install_mode = "new" # Default for existing pool is creating a new dataset
            if self.mode_replace.get_active():
                install_mode = "replace"
            elif self.mode_alongside.get_active():
                install_mode = "alongside"

            encryption_enabled = self.encryption_check.get_active()

            self.selected = {
                'pool': pool_name,
                'dataset': full_dataset_path, # This is the key Calamares uses for partitioning.
                'mode': install_mode,
                'encryption_enabled': encryption_enabled,
                'encryption_password': self.password_entry.get_text() if encryption_enabled else "", # For globalstorage
                'encryption_algorithm': self.algorithm_combo.get_active_text() if encryption_enabled else ""
            }
            # Store legacy globalstorage items for existing pool installs
            libcalamares.globalstorage.insert("install_pool", self.selected['pool'])
            libcalamares.globalstorage.insert("install_dataset", self.selected['dataset']) # Full path
            libcalamares.globalstorage.insert("install_mode", self.selected['mode'])
            libcalamares.globalstorage.insert("encryption_enabled", self.selected['encryption_enabled'])
            if self.selected['encryption_enabled']:
                libcalamares.globalstorage.insert("encryption_password", self.selected['encryption_password'])
                libcalamares.globalstorage.insert("encryption_algorithm", self.selected['encryption_algorithm'])
            else: # Clear them if disabled
                 libcalamares.globalstorage.insert("encryption_password", "")
                 libcalamares.globalstorage.insert("encryption_algorithm", "")


            # Global settings also apply here
            libcalamares.globalstorage.insert("zfs_arc_max_gb", int(self.arc_max_gb_spinbutton.get_value()))
            # For existing pools, encryption settings on datasets are more complex (inherit, on, off, new keys)
            # The current UI implies setting encryption on the new dataset being created.
            # If encryption is enabled, it means the new dataset should be encrypted.
            libcalamares.globalstorage.insert("zfs_encryption_keyformat", "passphrase" if encryption_enabled else "")
            libcalamares.globalstorage.insert("zfs_encryption_keylocation", "prompt" if encryption_enabled else "")


        libcalamares.utils.debug(f"ZFSTargetSelector final selection for Calamares: {self.selected}")
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

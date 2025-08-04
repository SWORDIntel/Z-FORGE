#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Rich ZFS Configuration GUI Widget

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
import subprocess
import json
from typing import Dict, List, Any, Optional, Tuple

class ZFSRichConfigWidget(Gtk.Box):
    """
    Rich ZFS configuration widget with comprehensive options
    """
    
    def __init__(self, global_storage, hardware_info: Dict[str, Any]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        self.gs = global_storage
        self.hardware_info = hardware_info
        self.available_disks = self._detect_disks()
        
        # Configuration state
        self.boot_pool_config = {}
        self.data_pools = []
        self.dataset_configs = {}
        self.compression_defaults = self._get_compression_defaults()
        
        # Build UI
        self._build_ui()
        
    def _build_ui(self):
        """Build the main UI"""
        # Header
        header = Gtk.Label()
        header.set_markup("<b>Advanced ZFS Configuration</b>")
        header.set_margin_bottom(10)
        self.pack_start(header, False, False, 0)
        
        # Notebook for different sections
        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        
        # Boot Pool tab
        boot_pool_box = self._create_boot_pool_tab()
        self.notebook.append_page(boot_pool_box, Gtk.Label(label="Boot Pool"))
        
        # Data Pools tab
        data_pools_box = self._create_data_pools_tab()
        self.notebook.append_page(data_pools_box, Gtk.Label(label="Data Pools"))
        
        # Datasets tab
        datasets_box = self._create_datasets_tab()
        self.notebook.append_page(datasets_box, Gtk.Label(label="Datasets"))
        
        # Advanced Options tab
        advanced_box = self._create_advanced_tab()
        self.notebook.append_page(advanced_box, Gtk.Label(label="Advanced"))
        
        # Summary tab
        summary_box = self._create_summary_tab()
        self.notebook.append_page(summary_box, Gtk.Label(label="Summary"))
        
        self.pack_start(self.notebook, True, True, 0)
        
        # Show all
        self.show_all()
    
    def _create_boot_pool_tab(self) -> Gtk.Box:
        """Create boot pool configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_left(20)
        box.set_margin_right(20)
        box.set_margin_top(20)
        
        # Boot pool explanation
        info = Gtk.Label()
        info.set_markup("<i>The boot pool contains kernel and initramfs. It should be small (2-10GB) and use compatible features.</i>")
        info.set_line_wrap(True)
        info.set_margin_bottom(10)
        box.pack_start(info, False, False, 0)
        
        # Pool name
        name_box = Gtk.Box(spacing=10)
        name_box.pack_start(Gtk.Label(label="Boot Pool Name:"), False, False, 0)
        self.boot_pool_name = Gtk.Entry()
        self.boot_pool_name.set_text("bpool")
        self.boot_pool_name.set_width_chars(20)
        name_box.pack_start(self.boot_pool_name, False, False, 0)
        box.pack_start(name_box, False, False, 0)
        
        # Boot drive selection
        box.pack_start(Gtk.Label(label="Select Boot Drive(s):"), False, False, 0)
        
        # Disk selection with details
        self.boot_disk_store = Gtk.ListStore(bool, str, str, str, str)  # selected, device, size, type, model
        self.boot_disk_view = Gtk.TreeView(model=self.boot_disk_store)
        
        # Columns
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self._on_boot_disk_toggled)
        col_select = Gtk.TreeViewColumn("Select", renderer_toggle, active=0)
        self.boot_disk_view.append_column(col_select)
        
        for i, title in enumerate(["Device", "Size", "Type", "Model"], 1):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.boot_disk_view.append_column(column)
        
        # Populate disks
        for disk in self.available_disks:
            self.boot_disk_store.append([
                False,
                disk["device"],
                disk["size"],
                disk["type"],
                disk["model"]
            ])
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(150)
        scroll.add(self.boot_disk_view)
        box.pack_start(scroll, True, True, 0)
        
        # Boot pool layout
        layout_box = Gtk.Box(spacing=10)
        layout_box.pack_start(Gtk.Label(label="Layout:"), False, False, 0)
        self.boot_layout = Gtk.ComboBoxText()
        for layout in ["single", "mirror", "raidz1"]:
            self.boot_layout.append_text(layout)
        self.boot_layout.set_active(1)  # Default to mirror
        layout_box.pack_start(self.boot_layout, False, False, 0)
        box.pack_start(layout_box, False, False, 0)
        
        # Boot pool options
        options_frame = Gtk.Frame(label="Boot Pool Options")
        options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        options_box.set_margin_left(10)
        options_box.set_margin_right(10)
        options_box.set_margin_top(10)
        options_box.set_margin_bottom(10)
        
        # Compression for boot pool
        comp_box = Gtk.Box(spacing=10)
        comp_box.pack_start(Gtk.Label(label="Compression:"), False, False, 0)
        self.boot_compression = Gtk.ComboBoxText()
        for comp in ["off", "lz4", "zstd", "gzip"]:
            self.boot_compression.append_text(comp)
        self.boot_compression.set_active(1)  # Default to lz4
        comp_box.pack_start(self.boot_compression, False, False, 0)
        options_box.pack_start(comp_box, False, False, 0)
        
        # Encryption for boot pool
        self.boot_encrypt = Gtk.CheckButton(label="Enable encryption (requires passphrase at boot)")
        options_box.pack_start(self.boot_encrypt, False, False, 0)
        
        options_frame.add(options_box)
        box.pack_start(options_frame, False, False, 0)
        
        return box
    
    def _create_data_pools_tab(self) -> Gtk.Box:
        """Create data pools configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_left(20)
        box.set_margin_right(20)
        box.set_margin_top(20)
        
        # Info
        info = Gtk.Label()
        info.set_markup("<i>Configure one or more data pools. You can separate fast and slow storage, or create specialized pools.</i>")
        info.set_line_wrap(True)
        box.pack_start(info, False, False, 0)
        
        # Pool list
        self.pool_store = Gtk.ListStore(str, str, str, str)  # name, layout, disks, compression
        self.pool_view = Gtk.TreeView(model=self.pool_store)
        
        for i, title in enumerate(["Pool Name", "Layout", "Disks", "Compression"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.pool_view.append_column(column)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(150)
        scroll.add(self.pool_view)
        box.pack_start(scroll, True, True, 0)
        
        # Buttons
        button_box = Gtk.Box(spacing=10)
        add_btn = Gtk.Button(label="Add Pool")
        add_btn.connect("clicked", self._on_add_pool)
        button_box.pack_start(add_btn, False, False, 0)
        
        edit_btn = Gtk.Button(label="Edit Pool")
        edit_btn.connect("clicked", self._on_edit_pool)
        button_box.pack_start(edit_btn, False, False, 0)
        
        remove_btn = Gtk.Button(label="Remove Pool")
        remove_btn.connect("clicked", self._on_remove_pool)
        button_box.pack_start(remove_btn, False, False, 0)
        
        box.pack_start(button_box, False, False, 0)
        
        # Pool configuration area
        self.pool_config_frame = Gtk.Frame(label="Pool Configuration")
        self.pool_config_box = None
        box.pack_start(self.pool_config_frame, True, True, 0)
        
        return box
    
    def _create_datasets_tab(self) -> Gtk.Box:
        """Create datasets configuration tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_left(20)
        box.set_margin_right(20)
        box.set_margin_top(20)
        
        # Info
        info = Gtk.Label()
        info.set_markup("<i>Configure datasets with specific properties for different workloads.</i>")
        info.set_line_wrap(True)
        box.pack_start(info, False, False, 0)
        
        # Pool selector
        pool_box = Gtk.Box(spacing=10)
        pool_box.pack_start(Gtk.Label(label="Select Pool:"), False, False, 0)
        self.dataset_pool_combo = Gtk.ComboBoxText()
        pool_box.pack_start(self.dataset_pool_combo, False, False, 0)
        box.pack_start(pool_box, False, False, 0)
        
        # Dataset tree
        self.dataset_store = Gtk.TreeStore(str, str, str, str, str)  # name, mountpoint, compression, recordsize, special
        self.dataset_view = Gtk.TreeView(model=self.dataset_store)
        
        for i, title in enumerate(["Dataset", "Mountpoint", "Compression", "Record Size", "Special"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.dataset_view.append_column(column)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(200)
        scroll.add(self.dataset_view)
        box.pack_start(scroll, True, True, 0)
        
        # Buttons
        button_box = Gtk.Box(spacing=10)
        add_btn = Gtk.Button(label="Add Dataset")
        add_btn.connect("clicked", self._on_add_dataset)
        button_box.pack_start(add_btn, False, False, 0)
        
        edit_btn = Gtk.Button(label="Edit Dataset")
        edit_btn.connect("clicked", self._on_edit_dataset)
        button_box.pack_start(edit_btn, False, False, 0)
        
        remove_btn = Gtk.Button(label="Remove Dataset")
        remove_btn.connect("clicked", self._on_remove_dataset)
        button_box.pack_start(remove_btn, False, False, 0)
        
        box.pack_start(button_box, False, False, 0)
        
        # Workload templates
        template_frame = Gtk.Frame(label="Workload Templates")
        template_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        template_box.set_margin_left(10)
        template_box.set_margin_right(10)
        template_box.set_margin_top(10)
        template_box.set_margin_bottom(10)
        
        templates = [
            ("System Root", "OS files, small files", {"compression": "lz4", "recordsize": "128K"}),
            ("Home Directories", "User files", {"compression": "zstd-3", "recordsize": "128K"}),
            ("Virtual Machines", "VM storage", {"compression": "lz4", "recordsize": "64K", "sync": "standard"}),
            ("Databases", "Database files", {"compression": "lz4", "recordsize": "16K", "primarycache": "metadata"}),
            ("Media Storage", "Large media files", {"compression": "off", "recordsize": "1M"}),
            ("Logs", "Log files", {"compression": "zstd-9", "recordsize": "128K", "sync": "disabled"}),
            ("Containers", "Container images", {"compression": "zstd", "recordsize": "128K", "dedup": "off"})
        ]
        
        for name, desc, props in templates:
            btn = Gtk.Button(label=f"{name} - {desc}")
            btn.connect("clicked", lambda w, p=props, n=name: self._apply_dataset_template(n, p))
            template_box.pack_start(btn, False, False, 0)
        
        template_frame.add(template_box)
        box.pack_start(template_frame, False, False, 0)
        
        return box
    
    def _create_advanced_tab(self) -> Gtk.Box:
        """Create advanced options tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_left(20)
        box.set_margin_right(20)
        box.set_margin_top(20)
        
        # Special vdevs
        special_frame = Gtk.Frame(label="Special vdevs")
        special_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        special_box.set_margin_left(10)
        special_box.set_margin_right(10)
        special_box.set_margin_top(10)
        special_box.set_margin_bottom(10)
        
        # L2ARC
        l2arc_box = Gtk.Box(spacing=10)
        self.enable_l2arc = Gtk.CheckButton(label="Enable L2ARC (read cache)")
        l2arc_box.pack_start(self.enable_l2arc, False, False, 0)
        self.l2arc_disks = Gtk.ComboBoxText()
        l2arc_box.pack_start(self.l2arc_disks, False, False, 0)
        special_box.pack_start(l2arc_box, False, False, 0)
        
        # SLOG
        slog_box = Gtk.Box(spacing=10)
        self.enable_slog = Gtk.CheckButton(label="Enable SLOG (write cache - requires PLP)")
        slog_box.pack_start(self.enable_slog, False, False, 0)
        self.slog_disks = Gtk.ComboBoxText()
        slog_box.pack_start(self.slog_disks, False, False, 0)
        special_box.pack_start(slog_box, False, False, 0)
        
        # Special allocation
        special_alloc_box = Gtk.Box(spacing=10)
        self.enable_special = Gtk.CheckButton(label="Enable special allocation class (metadata on SSD)")
        special_alloc_box.pack_start(self.enable_special, False, False, 0)
        self.special_disks = Gtk.ComboBoxText()
        special_alloc_box.pack_start(self.special_disks, False, False, 0)
        special_box.pack_start(special_alloc_box, False, False, 0)
        
        special_frame.add(special_box)
        box.pack_start(special_frame, False, False, 0)
        
        # Hardware-specific tuning
        hw_frame = Gtk.Frame(label="Hardware-Specific Tuning")
        hw_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hw_box.set_margin_left(10)
        hw_box.set_margin_right(10)
        hw_box.set_margin_top(10)
        hw_box.set_margin_bottom(10)
        
        # Display detected hardware
        hw_info = self._get_hardware_summary()
        hw_label = Gtk.Label()
        hw_label.set_markup(f"<b>Detected Hardware:</b>\n{hw_info}")
        hw_label.set_line_wrap(True)
        hw_box.pack_start(hw_label, False, False, 0)
        
        # Compression recommendations
        comp_label = Gtk.Label()
        comp_text = self._get_compression_recommendation()
        comp_label.set_markup(f"<b>Compression Recommendation:</b>\n{comp_text}")
        comp_label.set_line_wrap(True)
        hw_box.pack_start(comp_label, False, False, 0)
        
        hw_frame.add(hw_box)
        box.pack_start(hw_frame, False, False, 0)
        
        # ZFS module parameters
        module_frame = Gtk.Frame(label="ZFS Module Parameters")
        module_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        module_box.set_margin_left(10)
        module_box.set_margin_right(10)
        module_box.set_margin_top(10)
        module_box.set_margin_bottom(10)
        
        # ARC size
        arc_box = Gtk.Box(spacing=10)
        arc_box.pack_start(Gtk.Label(label="ARC Max Size:"), False, False, 0)
        self.arc_max = Gtk.SpinButton()
        self.arc_max.set_range(0, 256)
        self.arc_max.set_value(0)  # 0 = auto
        self.arc_max.set_increments(1, 10)
        arc_box.pack_start(self.arc_max, False, False, 0)
        arc_box.pack_start(Gtk.Label(label="GB (0 = auto)"), False, False, 0)
        module_box.pack_start(arc_box, False, False, 0)
        
        module_frame.add(module_box)
        box.pack_start(module_frame, False, False, 0)
        
        return box
    
    def _create_summary_tab(self) -> Gtk.Box:
        """Create configuration summary tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_left(20)
        box.set_margin_right(20)
        box.set_margin_top(20)
        
        # Summary text view
        self.summary_buffer = Gtk.TextBuffer()
        self.summary_view = Gtk.TextView(buffer=self.summary_buffer)
        self.summary_view.set_editable(False)
        self.summary_view.set_wrap_mode(Gtk.WrapMode.WORD)
        
        scroll = Gtk.ScrolledWindow()
        scroll.add(self.summary_view)
        box.pack_start(scroll, True, True, 0)
        
        # Update button
        update_btn = Gtk.Button(label="Update Summary")
        update_btn.connect("clicked", self._update_summary)
        box.pack_start(update_btn, False, False, 0)
        
        return box
    
    def _detect_disks(self) -> List[Dict[str, Any]]:
        """Detect available disks"""
        disks = []
        try:
            # Use lsblk to get disk information
            result = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MODEL,TRAN,ROTA"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for device in data.get("blockdevices", []):
                    if device.get("type") == "disk":
                        disk_type = "HDD" if device.get("rota") == "1" else "SSD"
                        if device.get("tran") == "nvme":
                            disk_type = "NVMe"
                        
                        disks.append({
                            "device": f"/dev/{device['name']}",
                            "size": device.get("size", "Unknown"),
                            "type": disk_type,
                            "model": device.get("model", "Unknown").strip(),
                            "transport": device.get("tran", "Unknown")
                        })
        except Exception as e:
            print(f"Error detecting disks: {e}")
        
        return disks
    
    def _get_compression_defaults(self) -> Dict[str, str]:
        """Get hardware-aware compression defaults"""
        cpu_count = self.hardware_info.get("cpu", {}).get("cores", 4)
        cpu_model = self.hardware_info.get("cpu", {}).get("model", "").lower()
        memory_gb = self.hardware_info.get("memory", {}).get("total_gb", 8)
        
        defaults = {}
        
        # High-performance systems
        if cpu_count >= 16 and memory_gb >= 32:
            defaults["general"] = "zstd-3"
            defaults["databases"] = "lz4"
            defaults["vms"] = "lz4"
            defaults["logs"] = "zstd-9"
        # Mid-range systems
        elif cpu_count >= 8 and memory_gb >= 16:
            defaults["general"] = "lz4"
            defaults["databases"] = "lz4"
            defaults["vms"] = "lz4"
            defaults["logs"] = "zstd-6"
        # Low-end systems
        else:
            defaults["general"] = "lz4"
            defaults["databases"] = "off"
            defaults["vms"] = "off"
            defaults["logs"] = "lz4"
        
        # Intel QuickAssist Technology
        if "xeon" in cpu_model and "qat" in cpu_model:
            defaults["general"] = "gzip-9"  # QAT accelerated
        
        return defaults
    
    def _get_hardware_summary(self) -> str:
        """Get hardware summary for display"""
        vendor = self.hardware_info.get("system", {}).get("vendor", "Unknown")
        model = self.hardware_info.get("system", {}).get("model", "Unknown")
        cpu = self.hardware_info.get("cpu", {}).get("model", "Unknown")
        cores = self.hardware_info.get("cpu", {}).get("cores", "Unknown")
        memory = self.hardware_info.get("memory", {}).get("total_gb", "Unknown")
        
        return f"System: {vendor} {model}\nCPU: {cpu} ({cores} cores)\nMemory: {memory}GB"
    
    def _get_compression_recommendation(self) -> str:
        """Get compression recommendation based on hardware"""
        defaults = self.compression_defaults
        
        text = f"General purpose: {defaults.get('general', 'lz4')}\n"
        text += f"Databases: {defaults.get('databases', 'lz4')}\n"
        text += f"Virtual Machines: {defaults.get('vms', 'lz4')}\n"
        text += f"Log files: {defaults.get('logs', 'zstd-6')}"
        
        return text
    
    def _on_boot_disk_toggled(self, widget, path):
        """Handle boot disk selection toggle"""
        self.boot_disk_store[path][0] = not self.boot_disk_store[path][0]
    
    def _on_add_pool(self, widget):
        """Add a new data pool"""
        # Show pool configuration dialog
        dialog = PoolConfigDialog(self.get_toplevel(), self.available_disks, self.compression_defaults)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            pool_config = dialog.get_configuration()
            if pool_config:
                self.data_pools.append(pool_config)
                self._update_pool_list()
        
        dialog.destroy()
    
    def _on_edit_pool(self, widget):
        """Edit selected pool"""
        selection = self.pool_view.get_selection()
        model, treeiter = selection.get_selected()
        
        if treeiter:
            pool_name = model[treeiter][0]
            # Find pool config
            for i, pool in enumerate(self.data_pools):
                if pool["name"] == pool_name:
                    dialog = PoolConfigDialog(
                        self.get_toplevel(), 
                        self.available_disks, 
                        self.compression_defaults,
                        pool
                    )
                    response = dialog.run()
                    
                    if response == Gtk.ResponseType.OK:
                        self.data_pools[i] = dialog.get_configuration()
                        self._update_pool_list()
                    
                    dialog.destroy()
                    break
    
    def _on_remove_pool(self, widget):
        """Remove selected pool"""
        selection = self.pool_view.get_selection()
        model, treeiter = selection.get_selected()
        
        if treeiter:
            pool_name = model[treeiter][0]
            self.data_pools = [p for p in self.data_pools if p["name"] != pool_name]
            self._update_pool_list()
    
    def _update_pool_list(self):
        """Update the pool list view"""
        self.pool_store.clear()
        for pool in self.data_pools:
            self.pool_store.append([
                pool["name"],
                pool["vdev_config"]["layout"],
                str(len(pool["vdev_config"]["disks"])),
                pool.get("compression", "lz4")
            ])
        
        # Update dataset pool combo
        self.dataset_pool_combo.remove_all()
        self.dataset_pool_combo.append_text("bpool")  # Boot pool
        for pool in self.data_pools:
            self.dataset_pool_combo.append_text(pool["name"])
    
    def _on_add_dataset(self, widget):
        """Add a new dataset"""
        pool_name = self.dataset_pool_combo.get_active_text()
        if not pool_name:
            return
        
        dialog = DatasetConfigDialog(self.get_toplevel(), pool_name, self.compression_defaults)
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            dataset_config = dialog.get_configuration()
            if dataset_config:
                if pool_name not in self.dataset_configs:
                    self.dataset_configs[pool_name] = []
                self.dataset_configs[pool_name].append(dataset_config)
                self._update_dataset_tree()
        
        dialog.destroy()
    
    def _on_edit_dataset(self, widget):
        """Edit selected dataset"""
        # Implementation similar to edit pool
        pass
    
    def _on_remove_dataset(self, widget):
        """Remove selected dataset"""
        # Implementation similar to remove pool
        pass
    
    def _update_dataset_tree(self):
        """Update dataset tree view"""
        self.dataset_store.clear()
        pool_name = self.dataset_pool_combo.get_active_text()
        
        if pool_name and pool_name in self.dataset_configs:
            for dataset in self.dataset_configs[pool_name]:
                self._add_dataset_to_tree(None, dataset)
    
    def _add_dataset_to_tree(self, parent_iter, dataset):
        """Add dataset to tree recursively"""
        special = []
        if dataset.get("recordsize") != "128K":
            special.append(f"recordsize={dataset['recordsize']}")
        if dataset.get("sync") != "standard":
            special.append(f"sync={dataset['sync']}")
        
        iter = self.dataset_store.append(parent_iter, [
            dataset["name"],
            dataset.get("mountpoint", "inherit"),
            dataset.get("compression", "inherit"),
            dataset.get("recordsize", "128K"),
            ", ".join(special)
        ])
        
        # Add children
        for child in dataset.get("children", []):
            self._add_dataset_to_tree(iter, child)
    
    def _apply_dataset_template(self, name: str, properties: Dict[str, Any]):
        """Apply a dataset template"""
        pool_name = self.dataset_pool_combo.get_active_text()
        if not pool_name:
            return
        
        # Create dataset with template properties
        dataset = {
            "name": name.lower().replace(" ", "_"),
            "mountpoint": f"/{name.lower().replace(' ', '_')}",
            **properties
        }
        
        if pool_name not in self.dataset_configs:
            self.dataset_configs[pool_name] = []
        self.dataset_configs[pool_name].append(dataset)
        self._update_dataset_tree()
    
    def _update_summary(self, widget):
        """Update configuration summary"""
        summary = "=== ZFS Configuration Summary ===\n\n"
        
        # Boot pool
        summary += "Boot Pool:\n"
        boot_disks = [row[1] for row in self.boot_disk_store if row[0]]
        if boot_disks:
            summary += f"  Name: {self.boot_pool_name.get_text()}\n"
            summary += f"  Layout: {self.boot_layout.get_active_text()}\n"
            summary += f"  Disks: {', '.join(boot_disks)}\n"
            summary += f"  Compression: {self.boot_compression.get_active_text()}\n"
            summary += f"  Encryption: {'Yes' if self.boot_encrypt.get_active() else 'No'}\n"
        else:
            summary += "  Not configured\n"
        
        summary += "\n"
        
        # Data pools
        summary += "Data Pools:\n"
        if self.data_pools:
            for pool in self.data_pools:
                summary += f"  {pool['name']}:\n"
                summary += f"    Layout: {pool['vdev_config']['layout']}\n"
                summary += f"    Disks: {len(pool['vdev_config']['disks'])}\n"
                summary += f"    Compression: {pool.get('compression', 'lz4')}\n"
        else:
            summary += "  None configured\n"
        
        summary += "\n"
        
        # Datasets
        summary += "Datasets:\n"
        for pool_name, datasets in self.dataset_configs.items():
            summary += f"  Pool {pool_name}:\n"
            for dataset in datasets:
                summary += f"    {dataset['name']}: {dataset.get('compression', 'inherit')}"
                if dataset.get('recordsize'):
                    summary += f", recordsize={dataset['recordsize']}"
                summary += "\n"
        
        self.summary_buffer.set_text(summary)
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get the complete ZFS configuration"""
        # Get boot pool configuration
        boot_disks = [row[1] for row in self.boot_disk_store if row[0]]
        
        if not boot_disks:
            return None
        
        boot_pool = {
            "name": self.boot_pool_name.get_text() or "bpool",
            "vdev_config": {
                "layout": self.boot_layout.get_active_text() or "mirror",
                "disks": boot_disks
            },
            "compression": self.boot_compression.get_active_text() or "lz4",
            "encryption": {
                "enabled": self.boot_encrypt.get_active(),
                "keylocation": "prompt",
                "keyformat": "passphrase"
            },
            "ashift": "auto"
        }
        
        # Build complete configuration
        config = {
            "boot_pool": boot_pool,
            "data_pools": self.data_pools,
            "datasets": self.dataset_configs,
            "compression_defaults": self.compression_defaults,
            "special_vdevs": {}
        }
        
        # Add special vdevs if configured
        if self.enable_l2arc.get_active():
            config["special_vdevs"]["l2arc"] = {
                "disks": [self.l2arc_disks.get_active_text()]
            }
        
        if self.enable_slog.get_active():
            config["special_vdevs"]["slog"] = {
                "disks": [self.slog_disks.get_active_text()],
                "mirror": True
            }
        
        if self.enable_special.get_active():
            config["special_vdevs"]["special"] = {
                "disks": [self.special_disks.get_active_text()],
                "mirror": True
            }
        
        # ARC configuration
        if self.arc_max.get_value() > 0:
            config["arc_max_gb"] = int(self.arc_max.get_value())
        
        return config


class PoolConfigDialog(Gtk.Dialog):
    """Dialog for configuring a data pool"""
    
    def __init__(self, parent, available_disks, compression_defaults, existing_config=None):
        super().__init__(title="Configure Data Pool", parent=parent)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        self.available_disks = available_disks
        self.compression_defaults = compression_defaults
        self.existing_config = existing_config
        
        self._build_ui()
        
        if existing_config:
            self._load_existing_config()
    
    def _build_ui(self):
        """Build dialog UI"""
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_left(20)
        box.set_margin_right(20)
        box.set_margin_top(20)
        
        # Pool name
        name_box = Gtk.Box(spacing=10)
        name_box.pack_start(Gtk.Label(label="Pool Name:"), False, False, 0)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_width_chars(20)
        name_box.pack_start(self.name_entry, False, False, 0)
        box.pack_start(name_box, False, False, 0)
        
        # Layout selection
        layout_box = Gtk.Box(spacing=10)
        layout_box.pack_start(Gtk.Label(label="Layout:"), False, False, 0)
        self.layout_combo = Gtk.ComboBoxText()
        for layout in ["stripe", "mirror", "raidz1", "raidz2", "raidz3", "draid"]:
            self.layout_combo.append_text(layout)
        self.layout_combo.set_active(1)  # Default to mirror
        layout_box.pack_start(self.layout_combo, False, False, 0)
        box.pack_start(layout_box, False, False, 0)
        
        # Disk selection
        box.pack_start(Gtk.Label(label="Select Disks:"), False, False, 0)
        
        self.disk_store = Gtk.ListStore(bool, str, str, str, str)
        self.disk_view = Gtk.TreeView(model=self.disk_store)
        
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self._on_disk_toggled)
        col_select = Gtk.TreeViewColumn("Select", renderer_toggle, active=0)
        self.disk_view.append_column(col_select)
        
        for i, title in enumerate(["Device", "Size", "Type", "Model"], 1):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.disk_view.append_column(column)
        
        for disk in self.available_disks:
            self.disk_store.append([
                False,
                disk["device"],
                disk["size"],
                disk["type"],
                disk["model"]
            ])
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(200)
        scroll.add(self.disk_view)
        box.pack_start(scroll, True, True, 0)
        
        # Compression
        comp_box = Gtk.Box(spacing=10)
        comp_box.pack_start(Gtk.Label(label="Compression:"), False, False, 0)
        self.compression_combo = Gtk.ComboBoxText()
        for comp in ["off", "lz4", "zstd", "zstd-3", "zstd-6", "zstd-9", "gzip", "gzip-9"]:
            self.compression_combo.append_text(comp)
        self.compression_combo.set_active_text(self.compression_defaults.get("general", "lz4"))
        comp_box.pack_start(self.compression_combo, False, False, 0)
        box.pack_start(comp_box, False, False, 0)
        
        # Encryption
        self.encrypt_check = Gtk.CheckButton(label="Enable encryption")
        box.pack_start(self.encrypt_check, False, False, 0)
        
        # Deduplication
        dedup_box = Gtk.Box(spacing=10)
        dedup_box.pack_start(Gtk.Label(label="Deduplication:"), False, False, 0)
        self.dedup_combo = Gtk.ComboBoxText()
        for dedup in ["off", "on", "verify"]:
            self.dedup_combo.append_text(dedup)
        self.dedup_combo.set_active(0)  # Default off
        dedup_box.pack_start(self.dedup_combo, False, False, 0)
        box.pack_start(dedup_box, False, False, 0)
        
        box.show_all()
    
    def _on_disk_toggled(self, widget, path):
        """Handle disk selection toggle"""
        self.disk_store[path][0] = not self.disk_store[path][0]
    
    def _load_existing_config(self):
        """Load existing configuration"""
        config = self.existing_config
        self.name_entry.set_text(config["name"])
        self.layout_combo.set_active_text(config["vdev_config"]["layout"])
        self.compression_combo.set_active_text(config.get("compression", "lz4"))
        self.encrypt_check.set_active(config.get("encryption", {}).get("enabled", False))
        self.dedup_combo.set_active_text(config.get("dedup", "off"))
        
        # Mark selected disks
        selected_disks = config["vdev_config"]["disks"]
        for row in self.disk_store:
            if row[1] in selected_disks:
                row[0] = True
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get pool configuration"""
        name = self.name_entry.get_text()
        if not name:
            return None
        
        selected_disks = [row[1] for row in self.disk_store if row[0]]
        if not selected_disks:
            return None
        
        return {
            "name": name,
            "vdev_config": {
                "layout": self.layout_combo.get_active_text(),
                "disks": selected_disks
            },
            "compression": self.compression_combo.get_active_text(),
            "encryption": {
                "enabled": self.encrypt_check.get_active(),
                "keylocation": "prompt",
                "keyformat": "passphrase"
            },
            "dedup": self.dedup_combo.get_active_text(),
            "ashift": "auto"
        }


class DatasetConfigDialog(Gtk.Dialog):
    """Dialog for configuring a dataset"""
    
    def __init__(self, parent, pool_name, compression_defaults):
        super().__init__(title=f"Configure Dataset on {pool_name}", parent=parent)
        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        self.pool_name = pool_name
        self.compression_defaults = compression_defaults
        
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog UI"""
        box = self.get_content_area()
        box.set_spacing(10)
        box.set_margin_left(20)
        box.set_margin_right(20)
        box.set_margin_top(20)
        
        # Dataset name
        name_box = Gtk.Box(spacing=10)
        name_box.pack_start(Gtk.Label(label="Dataset Name:"), False, False, 0)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_width_chars(30)
        name_box.pack_start(self.name_entry, False, False, 0)
        box.pack_start(name_box, False, False, 0)
        
        # Mountpoint
        mount_box = Gtk.Box(spacing=10)
        mount_box.pack_start(Gtk.Label(label="Mountpoint:"), False, False, 0)
        self.mount_entry = Gtk.Entry()
        self.mount_entry.set_width_chars(30)
        mount_box.pack_start(self.mount_entry, False, False, 0)
        box.pack_start(mount_box, False, False, 0)
        
        # Compression
        comp_box = Gtk.Box(spacing=10)
        comp_box.pack_start(Gtk.Label(label="Compression:"), False, False, 0)
        self.compression_combo = Gtk.ComboBoxText()
        for comp in ["inherit", "off", "lz4", "zstd", "zstd-3", "zstd-6", "zstd-9", "gzip"]:
            self.compression_combo.append_text(comp)
        self.compression_combo.set_active(0)  # Default inherit
        comp_box.pack_start(self.compression_combo, False, False, 0)
        box.pack_start(comp_box, False, False, 0)
        
        # Record size
        record_box = Gtk.Box(spacing=10)
        record_box.pack_start(Gtk.Label(label="Record Size:"), False, False, 0)
        self.recordsize_combo = Gtk.ComboBoxText()
        for size in ["inherit", "4K", "8K", "16K", "32K", "64K", "128K", "256K", "512K", "1M"]:
            self.recordsize_combo.append_text(size)
        self.recordsize_combo.set_active_text("128K")
        record_box.pack_start(self.recordsize_combo, False, False, 0)
        box.pack_start(record_box, False, False, 0)
        
        # Sync
        sync_box = Gtk.Box(spacing=10)
        sync_box.pack_start(Gtk.Label(label="Sync:"), False, False, 0)
        self.sync_combo = Gtk.ComboBoxText()
        for sync in ["standard", "always", "disabled"]:
            self.sync_combo.append_text(sync)
        self.sync_combo.set_active(0)
        sync_box.pack_start(self.sync_combo, False, False, 0)
        box.pack_start(sync_box, False, False, 0)
        
        # Quota
        quota_box = Gtk.Box(spacing=10)
        quota_box.pack_start(Gtk.Label(label="Quota:"), False, False, 0)
        self.quota_entry = Gtk.Entry()
        self.quota_entry.set_placeholder_text("e.g., 100G")
        self.quota_entry.set_width_chars(20)
        quota_box.pack_start(self.quota_entry, False, False, 0)
        box.pack_start(quota_box, False, False, 0)
        
        box.show_all()
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get dataset configuration"""
        name = self.name_entry.get_text()
        if not name:
            return None
        
        config = {
            "name": name,
            "mountpoint": self.mount_entry.get_text() or f"/{name}"
        }
        
        # Only add non-default values
        if self.compression_combo.get_active_text() != "inherit":
            config["compression"] = self.compression_combo.get_active_text()
        
        if self.recordsize_combo.get_active_text() != "inherit":
            config["recordsize"] = self.recordsize_combo.get_active_text()
        
        if self.sync_combo.get_active_text() != "standard":
            config["sync"] = self.sync_combo.get_active_text()
        
        if self.quota_entry.get_text():
            config["quota"] = self.quota_entry.get_text()
        
        return config
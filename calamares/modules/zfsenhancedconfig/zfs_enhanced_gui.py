#!/usr/bin/env python3
"""
Enhanced ZFS Configuration GUI Widget for Calamares
Provides advanced ZFS pool configuration with visual feedback
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango
import json
import subprocess
import math
from typing import Dict, List, Optional, Tuple

class ZFSEnhancedConfigWidget(Gtk.Box):
    """
    Enhanced ZFS configuration widget for Calamares integration
    """
    
    def __init__(self, globalstorage):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        self.gs = globalstorage
        
        # Initialize data structures
        self.selected_disks = []
        self.available_disks = []
        self.pool_config = {
            'name': 'tank',
            'raid_type': 'mirror',
            'ashift': 12,
            'compression': 'lz4',
            'encryption': False,
            'workload': 'general'
        }
        
        # Check for existing configuration
        existing_config = self.gs.value("zfsPoolConfig")
        if existing_config:
            self.pool_config.update(existing_config)
            self.selected_disks = existing_config.get('disks', [])
        
        self.setup_ui()
        self.load_available_disks()
        
    def setup_ui(self):
        """Build the enhanced UI"""
        
        # Header with pool name
        header_box = self.create_header()
        self.pack_start(header_box, False, False, 0)
        
        # Main content area with visual designer
        content_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        
        # Left side - Disk selection and RAID config
        left_box = self.create_disk_selector()
        content_paned.pack1(left_box, resize=True, shrink=False)
        
        # Right side - Visual pool representation and settings
        right_notebook = self.create_settings_notebook()
        content_paned.pack2(right_notebook, resize=True, shrink=False)
        
        content_paned.set_position(500)
        self.pack_start(content_paned, True, True, 0)
        
        # Show all widgets
        self.show_all()
        
    def create_header(self) -> Gtk.Box:
        """Create header with pool name and status"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_homogeneous(False)
        
        # Pool name entry
        name_label = Gtk.Label(label="Pool Name:")
        name_label.set_markup("<b>Pool Name:</b>")
        header_box.pack_start(name_label, False, False, 0)
        
        self.name_entry = Gtk.Entry()
        self.name_entry.set_text(self.pool_config['name'])
        self.name_entry.set_max_length(63)  # ZFS pool name limit
        self.name_entry.connect("changed", self.on_pool_name_changed)
        header_box.pack_start(self.name_entry, False, False, 0)
        
        # Status indicator
        self.status_label = Gtk.Label()
        self.update_status("Ready to configure pool")
        header_box.pack_end(self.status_label, False, False, 0)
        
        return header_box
        
    def create_disk_selector(self) -> Gtk.Box:
        """Create disk selection interface with visual feedback"""
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Available disks section
        disks_label = Gtk.Label()
        disks_label.set_markup("<b>Available Disks</b>")
        disks_label.set_alignment(0, 0.5)
        left_box.pack_start(disks_label, False, False, 0)
        
        # Disk list with details
        disk_scroll = Gtk.ScrolledWindow()
        disk_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        disk_scroll.set_min_content_height(200)
        
        self.disk_store = Gtk.ListStore(bool, str, str, str, str, str)  # selected, device, size, model, type, health
        self.disk_view = Gtk.TreeView(model=self.disk_store)
        
        # Checkbox column
        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.connect("toggled", self.on_disk_toggled)
        toggle_column = Gtk.TreeViewColumn("Select", toggle_renderer, active=0)
        self.disk_view.append_column(toggle_column)
        
        # Disk info columns
        for i, title in enumerate(["Device", "Size", "Model", "Type", "Health"], 1):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_resizable(True)
            self.disk_view.append_column(column)
        
        disk_scroll.add(self.disk_view)
        left_box.pack_start(disk_scroll, True, True, 0)
        
        # RAID configuration
        raid_frame = Gtk.Frame(label="RAID Configuration")
        raid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        raid_box.set_margin_top(10)
        raid_box.set_margin_bottom(10)
        raid_box.set_margin_left(10)
        raid_box.set_margin_right(10)
        
        # RAID type selection with visual indicators
        raid_types = [
            ("stripe", "Stripe (RAID 0)", "No redundancy, maximum performance", 1),
            ("mirror", "Mirror (RAID 1)", "Full redundancy, good performance", 2),
            ("raidz1", "RAIDZ1 (RAID 5)", "1 disk redundancy, balanced", 3),
            ("raidz2", "RAIDZ2 (RAID 6)", "2 disk redundancy, safe", 4),
            ("raidz3", "RAIDZ3", "3 disk redundancy, very safe", 5)
        ]
        
        self.raid_buttons = {}
        first_button = None
        for raid_type, label, tooltip, min_disks in raid_types:
            if first_button is None:
                button = Gtk.RadioButton.new_with_label(None, label)
                first_button = button
            else:
                button = Gtk.RadioButton.new_with_label_from_widget(first_button, label)
            
            button.set_tooltip_text(f"{tooltip}\nMinimum disks: {min_disks}")
            button.connect("toggled", self.on_raid_type_changed, raid_type)
            self.raid_buttons[raid_type] = button
            raid_box.pack_start(button, False, False, 0)
        
        # Set default
        if self.pool_config['raid_type'] in self.raid_buttons:
            self.raid_buttons[self.pool_config['raid_type']].set_active(True)
        
        raid_frame.add(raid_box)
        left_box.pack_start(raid_frame, False, False, 0)
        
        # Disk recommendations
        self.recommendation_label = Gtk.Label()
        self.recommendation_label.set_line_wrap(True)
        self.recommendation_label.set_margin_top(10)
        self.update_recommendations()
        left_box.pack_start(self.recommendation_label, False, False, 0)
        
        return left_box
        
    def create_settings_notebook(self) -> Gtk.Notebook:
        """Create notebook with visual pool designer and settings"""
        notebook = Gtk.Notebook()
        
        # Visual Designer tab
        designer_box = self.create_visual_designer()
        notebook.append_page(designer_box, Gtk.Label(label="Visual Designer"))
        
        # Performance Settings tab
        perf_box = self.create_performance_settings()
        notebook.append_page(perf_box, Gtk.Label(label="Performance"))
        
        # Advanced Settings tab
        advanced_box = self.create_advanced_settings()
        notebook.append_page(advanced_box, Gtk.Label(label="Advanced"))
        
        # Summary tab
        summary_box = self.create_summary_view()
        notebook.append_page(summary_box, Gtk.Label(label="Summary"))
        
        return notebook
        
    def create_visual_designer(self) -> Gtk.Box:
        """Create visual pool designer"""
        designer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Drawing area for pool visualization
        self.pool_drawing = Gtk.DrawingArea()
        self.pool_drawing.set_size_request(400, 300)
        self.pool_drawing.connect("draw", self.on_draw_pool)
        
        designer_frame = Gtk.Frame()
        designer_frame.add(self.pool_drawing)
        designer_box.pack_start(designer_frame, True, True, 0)
        
        # Pool statistics
        stats_grid = Gtk.Grid()
        stats_grid.set_column_spacing(20)
        stats_grid.set_row_spacing(5)
        
        stats = [
            ("Total Capacity:", self.calculate_total_capacity),
            ("Usable Capacity:", self.calculate_usable_capacity),
            ("Redundancy Level:", self.get_redundancy_level),
            ("Expected Performance:", self.estimate_performance),
            ("Fault Tolerance:", self.get_fault_tolerance)
        ]
        
        self.stat_labels = {}
        for i, (label_text, _) in enumerate(stats):
            label = Gtk.Label(label=label_text)
            label.set_alignment(1, 0.5)
            stats_grid.attach(label, 0, i, 1, 1)
            
            value_label = Gtk.Label()
            value_label.set_alignment(0, 0.5)
            self.stat_labels[label_text] = value_label
            stats_grid.attach(value_label, 1, i, 1, 1)
        
        designer_box.pack_start(stats_grid, False, False, 0)
        
        self.update_pool_stats()
        
        return designer_box
        
    def create_performance_settings(self) -> Gtk.Box:
        """Create performance tuning settings"""
        perf_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        perf_box.set_margin_top(10)
        perf_box.set_margin_bottom(10)
        perf_box.set_margin_left(10)
        perf_box.set_margin_right(10)
        
        # Workload profiles
        profile_frame = Gtk.Frame(label="Workload Profile")
        profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        profile_box.set_margin_top(10)
        profile_box.set_margin_bottom(10)
        profile_box.set_margin_left(10)
        profile_box.set_margin_right(10)
        
        profiles = [
            ("general", "General Purpose", "Balanced for mixed workloads"),
            ("database", "Database Server", "Optimized for random I/O"),
            ("media", "Media Storage", "Optimized for large files"),
            ("vm", "Virtual Machines", "Optimized for VM storage"),
            ("backup", "Backup Target", "Optimized for deduplication")
        ]
        
        self.profile_buttons = {}
        first_button = None
        for profile_id, label, tooltip in profiles:
            if first_button is None:
                button = Gtk.RadioButton.new_with_label(None, label)
                first_button = button
            else:
                button = Gtk.RadioButton.new_with_label_from_widget(first_button, label)
            
            button.set_tooltip_text(tooltip)
            button.connect("toggled", self.on_profile_changed, profile_id)
            self.profile_buttons[profile_id] = button
            profile_box.pack_start(button, False, False, 0)
        
        # Set default profile
        if self.pool_config.get('workload', 'general') in self.profile_buttons:
            self.profile_buttons[self.pool_config['workload']].set_active(True)
        
        profile_frame.add(profile_box)
        perf_box.pack_start(profile_frame, False, False, 0)
        
        # ARC size configuration
        arc_frame = Gtk.Frame(label="ARC (RAM Cache) Configuration")
        arc_grid = Gtk.Grid()
        arc_grid.set_column_spacing(10)
        arc_grid.set_row_spacing(10)
        arc_grid.set_margin_top(10)
        arc_grid.set_margin_bottom(10)
        arc_grid.set_margin_left(10)
        arc_grid.set_margin_right(10)
        
        # Get system RAM
        total_ram = self.get_system_ram()
        
        arc_label = Gtk.Label(label="Maximum ARC Size:")
        arc_grid.attach(arc_label, 0, 0, 1, 1)
        
        self.arc_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL,
            1, max(2, total_ram // 2), 1
        )
        self.arc_scale.set_value(min(8, total_ram // 4))  # Default to 25% of RAM, max 8GB
        self.arc_scale.set_hexpand(True)
        self.arc_scale.set_draw_value(True)
        self.arc_scale.connect("value-changed", self.on_arc_changed)
        arc_grid.attach(self.arc_scale, 1, 0, 1, 1)
        
        self.arc_value_label = Gtk.Label()
        self.update_arc_label()
        arc_grid.attach(self.arc_value_label, 2, 0, 1, 1)
        
        arc_frame.add(arc_grid)
        perf_box.pack_start(arc_frame, False, False, 0)
        
        return perf_box
        
    def create_advanced_settings(self) -> Gtk.Box:
        """Create advanced ZFS settings"""
        advanced_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        advanced_box.set_margin_top(10)
        advanced_box.set_margin_bottom(10)
        advanced_box.set_margin_left(10)
        advanced_box.set_margin_right(10)
        
        # Sector size (ashift)
        ashift_frame = Gtk.Frame(label="Sector Size (ashift)")
        ashift_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        ashift_box.set_margin_top(10)
        ashift_box.set_margin_bottom(10)
        ashift_box.set_margin_left(10)
        ashift_box.set_margin_right(10)
        
        ashifts = [
            (9, "512 bytes (Legacy HDDs)"),
            (12, "4K (Modern HDDs/SSDs)"),
            (13, "8K (Some enterprise SSDs)")
        ]
        
        self.ashift_buttons = {}
        first_button = None
        for ashift, label in ashifts:
            if first_button is None:
                button = Gtk.RadioButton.new_with_label(None, label)
                first_button = button
            else:
                button = Gtk.RadioButton.new_with_label_from_widget(first_button, label)
            
            button.connect("toggled", self.on_ashift_changed, ashift)
            self.ashift_buttons[ashift] = button
            ashift_box.pack_start(button, False, False, 0)
        
        # Set default ashift
        if self.pool_config.get('ashift', 12) in self.ashift_buttons:
            self.ashift_buttons[self.pool_config['ashift']].set_active(True)
        
        ashift_frame.add(ashift_box)
        advanced_box.pack_start(ashift_frame, False, False, 0)
        
        # Compression
        comp_frame = Gtk.Frame(label="Compression")
        comp_grid = Gtk.Grid()
        comp_grid.set_column_spacing(10)
        comp_grid.set_row_spacing(10)
        comp_grid.set_margin_top(10)
        comp_grid.set_margin_bottom(10)
        comp_grid.set_margin_left(10)
        comp_grid.set_margin_right(10)
        
        comp_label = Gtk.Label(label="Algorithm:")
        comp_grid.attach(comp_label, 0, 0, 1, 1)
        
        self.comp_combo = Gtk.ComboBoxText()
        compressions = ["off", "lz4", "zstd", "zstd-3", "zstd-9", "gzip", "gzip-9"]
        for comp in compressions:
            self.comp_combo.append_text(comp)
        
        # Set default compression
        current_comp = self.pool_config.get('compression', 'lz4')
        for i, comp in enumerate(compressions):
            if comp == current_comp:
                self.comp_combo.set_active(i)
                break
        else:
            self.comp_combo.set_active(1)  # Default to lz4
            
        self.comp_combo.connect("changed", self.on_compression_changed)
        comp_grid.attach(self.comp_combo, 1, 0, 1, 1)
        
        comp_frame.add(comp_grid)
        advanced_box.pack_start(comp_frame, False, False, 0)
        
        # Encryption
        enc_frame = Gtk.Frame(label="Encryption")
        enc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        enc_box.set_margin_top(10)
        enc_box.set_margin_bottom(10)
        enc_box.set_margin_left(10)
        enc_box.set_margin_right(10)
        
        self.enc_check = Gtk.CheckButton(label="Enable encryption")
        self.enc_check.set_active(self.pool_config.get('encryption', False))
        self.enc_check.connect("toggled", self.on_encryption_toggled)
        enc_box.pack_start(self.enc_check, False, False, 0)
        
        # Password fields
        self.enc_grid = Gtk.Grid()
        self.enc_grid.set_column_spacing(10)
        self.enc_grid.set_row_spacing(10)
        self.enc_grid.set_sensitive(self.pool_config.get('encryption', False))
        
        pass_label = Gtk.Label(label="Password:")
        self.enc_grid.attach(pass_label, 0, 0, 1, 1)
        
        self.pass_entry = Gtk.Entry()
        self.pass_entry.set_visibility(False)
        self.pass_entry.set_hexpand(True)
        self.enc_grid.attach(self.pass_entry, 1, 0, 1, 1)
        
        confirm_label = Gtk.Label(label="Confirm:")
        self.enc_grid.attach(confirm_label, 0, 1, 1, 1)
        
        self.confirm_entry = Gtk.Entry()
        self.confirm_entry.set_visibility(False)
        self.confirm_entry.set_hexpand(True)
        self.enc_grid.attach(self.confirm_entry, 1, 1, 1, 1)
        
        enc_box.pack_start(self.enc_grid, False, False, 0)
        enc_frame.add(enc_box)
        advanced_box.pack_start(enc_frame, False, False, 0)
        
        return advanced_box
        
    def create_summary_view(self) -> Gtk.Box:
        """Create configuration summary view"""
        summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        summary_box.set_margin_top(10)
        summary_box.set_margin_bottom(10)
        summary_box.set_margin_left(10)
        summary_box.set_margin_right(10)
        
        # Summary text view
        self.summary_buffer = Gtk.TextBuffer()
        self.summary_view = Gtk.TextView(buffer=self.summary_buffer)
        self.summary_view.set_editable(False)
        self.summary_view.set_wrap_mode(Gtk.WrapMode.WORD)
        
        # Use monospace font for command preview
        font_desc = Pango.FontDescription("monospace 10")
        self.summary_view.modify_font(font_desc)
        
        summary_scroll = Gtk.ScrolledWindow()
        summary_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        summary_scroll.add(self.summary_view)
        
        summary_box.pack_start(summary_scroll, True, True, 0)
        
        # Update summary
        self.update_summary()
        
        return summary_box
        
    # Helper methods
    def load_available_disks(self):
        """Load available disks using lsblk"""
        self.disk_store.clear()
        self.available_disks = []
        
        try:
            # Get disk information
            output = subprocess.check_output([
                "lsblk", "-J", "-o", "NAME,SIZE,MODEL,ROTA,TYPE,FSTYPE"
            ]).decode()
            
            data = json.loads(output)
            
            for device in data.get("blockdevices", []):
                if device.get("type") == "disk" and not device.get("fstype"):
                    name = f"/dev/{device['name']}"
                    size = device.get("size", "Unknown")
                    model = device.get("model", "Unknown").strip() if device.get("model") else "Unknown"
                    disk_type = "HDD" if device.get("rota") == "1" else "SSD"
                    
                    # Check disk health
                    health = self.check_disk_health(name)
                    
                    # Check if disk was previously selected
                    selected = name in self.selected_disks
                    
                    self.available_disks.append({
                        'path': name,
                        'size': size,
                        'model': model,
                        'type': disk_type,
                        'health': health
                    })
                    
                    self.disk_store.append([
                        selected, name, size, model, disk_type, health
                    ])
                    
        except Exception as e:
            print(f"Error loading disks: {e}")
            
    def check_disk_health(self, device: str) -> str:
        """Check disk health using smartctl"""
        try:
            output = subprocess.check_output([
                "smartctl", "-H", device
            ], stderr=subprocess.DEVNULL).decode()
            
            if "PASSED" in output:
                return "Healthy"
            else:
                return "Check"
        except:
            return "Unknown"
            
    def on_draw_pool(self, widget, cr):
        """Draw visual representation of the pool"""
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        
        # Clear background
        cr.set_source_rgb(0.95, 0.95, 0.95)
        cr.paint()
        
        if not self.selected_disks:
            # Show placeholder text
            cr.set_source_rgb(0.5, 0.5, 0.5)
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(14)
            text = "Select disks to visualize pool"
            extents = cr.text_extents(text)
            cr.move_to(width/2 - extents.width/2, height/2)
            cr.show_text(text)
            return
            
        # Draw pool visualization based on RAID type
        raid_type = self.pool_config['raid_type']
        num_disks = len(self.selected_disks)
        
        if num_disks == 0:
            return
            
        # Calculate disk dimensions
        disk_width = min(80, (width - 40) / max(1, num_disks) - 10)
        disk_height = 120
        start_x = (width - (num_disks * (disk_width + 10))) / 2
        start_y = (height - disk_height) / 2
        
        # Draw disks
        for i, disk in enumerate(self.selected_disks):
            x = start_x + i * (disk_width + 10)
            y = start_y
            
            # Draw disk rectangle
            cr.set_source_rgb(0.2, 0.4, 0.8)
            cr.rectangle(x, y, disk_width, disk_height)
            cr.fill_preserve()
            cr.set_source_rgb(0.1, 0.2, 0.4)
            cr.stroke()
            
            # Draw disk label
            cr.set_source_rgb(1, 1, 1)
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(10)
            cr.move_to(x + 5, y + 20)
            cr.show_text(disk.split('/')[-1])
            
            # Draw RAID indicators
            if raid_type == "mirror" and i > 0:
                # Draw mirror link
                cr.set_source_rgb(0.2, 0.8, 0.2)
                cr.move_to(x - 5, y + disk_height/2)
                cr.line_to(x - 10 + disk_width, y + disk_height/2)
                cr.stroke()
                
    def update_status(self, message: str, error: bool = False):
        """Update status label"""
        if error:
            self.status_label.set_markup(f'<span color="red">{message}</span>')
        else:
            self.status_label.set_markup(f'<span color="green">{message}</span>')
            
    def update_recommendations(self):
        """Update disk recommendations based on selection"""
        num_selected = len(self.selected_disks)
        raid_type = self.pool_config['raid_type']
        
        recommendations = {
            'stripe': (1, "Minimum 1 disk. No redundancy!"),
            'mirror': (2, "Minimum 2 disks. Can lose 1 disk."),
            'raidz1': (3, "Minimum 3 disks. Can lose 1 disk."),
            'raidz2': (4, "Minimum 4 disks. Can lose 2 disks."),
            'raidz3': (5, "Minimum 5 disks. Can lose 3 disks.")
        }
        
        min_disks, desc = recommendations.get(raid_type, (1, "Unknown RAID type"))
        
        if num_selected < min_disks:
            self.recommendation_label.set_markup(
                f'<span color="red">Need {min_disks - num_selected} more disk(s) for {raid_type}</span>\n{desc}'
            )
        else:
            self.recommendation_label.set_markup(
                f'<span color="green">✓ Valid configuration</span>\n{desc}'
            )
            
    def update_pool_stats(self):
        """Update pool statistics display"""
        for label_text, calc_func in [
            ("Total Capacity:", self.calculate_total_capacity),
            ("Usable Capacity:", self.calculate_usable_capacity),
            ("Redundancy Level:", self.get_redundancy_level),
            ("Expected Performance:", self.estimate_performance),
            ("Fault Tolerance:", self.get_fault_tolerance)
        ]:
            value = calc_func()
            if label_text in self.stat_labels:
                self.stat_labels[label_text].set_text(value)
            
    def calculate_total_capacity(self) -> str:
        """Calculate total raw capacity"""
        # This is a simplified calculation
        # In reality, would parse actual disk sizes
        num_disks = len(self.selected_disks)
        if num_disks == 0:
            return "0 GB"
        # Assume 1TB disks for demo
        return f"{num_disks} TB"
        
    def calculate_usable_capacity(self) -> str:
        """Calculate usable capacity after redundancy"""
        num_disks = len(self.selected_disks)
        if num_disks == 0:
            return "0 GB"
            
        raid_type = self.pool_config['raid_type']
        
        # Simplified calculation assuming 1TB disks
        capacities = {
            'stripe': num_disks,
            'mirror': num_disks // 2,
            'raidz1': num_disks - 1,
            'raidz2': num_disks - 2,
            'raidz3': num_disks - 3
        }
        
        usable = capacities.get(raid_type, 0)
        return f"{max(0, usable)} TB"
        
    def get_redundancy_level(self) -> str:
        """Get redundancy description"""
        levels = {
            'stripe': "None",
            'mirror': "High (2x)",
            'raidz1': "Normal (1 disk)",
            'raidz2': "High (2 disks)",
            'raidz3': "Very High (3 disks)"
        }
        return levels.get(self.pool_config['raid_type'], "Unknown")
        
    def estimate_performance(self) -> str:
        """Estimate relative performance"""
        # Simplified performance estimation
        num_disks = len(self.selected_disks)
        if num_disks == 0:
            return "N/A"
            
        raid_type = self.pool_config['raid_type']
        
        if raid_type == 'stripe':
            return f"Very High ({num_disks}x read/write)"
        elif raid_type == 'mirror':
            return f"High ({num_disks}x read, 1x write)"
        else:
            return "Good (optimized for redundancy)"
            
    def get_fault_tolerance(self) -> str:
        """Get fault tolerance description"""
        tolerances = {
            'stripe': "0 disks (no redundancy)",
            'mirror': "1 disk per mirror",
            'raidz1': "1 disk",
            'raidz2': "2 disks",
            'raidz3': "3 disks"
        }
        return tolerances.get(self.pool_config['raid_type'], "Unknown")
        
    def get_system_ram(self) -> int:
        """Get system RAM in GB"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        kb = int(line.split()[1])
                        return kb // (1024 * 1024)
        except:
            return 8  # Default fallback
            
    def update_arc_label(self):
        """Update ARC size label"""
        size_gb = int(self.arc_scale.get_value())
        self.arc_value_label.set_text(f"{size_gb} GB")
        self.pool_config['arc_max'] = size_gb
        
    def update_summary(self):
        """Update configuration summary"""
        summary = f"""ZFS Pool Configuration Summary
==============================

Pool Name: {self.pool_config['name']}
RAID Type: {self.pool_config['raid_type'].upper()}
Selected Disks: {len(self.selected_disks)}
"""
        
        if self.selected_disks:
            summary += "\nDisks:\n"
            for disk in self.selected_disks:
                summary += f"  - {disk}\n"
                
        summary += f"""
Performance Profile: {self.pool_config.get('workload', 'general')}
Compression: {self.pool_config.get('compression', 'lz4')}
Encryption: {'Enabled' if self.pool_config.get('encryption', False) else 'Disabled'}
Sector Size: {2 ** self.pool_config.get('ashift', 12)} bytes (ashift={self.pool_config.get('ashift', 12)})

Estimated Capacity:
  Total: {self.calculate_total_capacity()}
  Usable: {self.calculate_usable_capacity()}
  
ZFS Command Preview:
--------------------
zpool create {self.build_zpool_command()}
"""
        
        self.summary_buffer.set_text(summary)
        
    def build_zpool_command(self) -> str:
        """Build the zpool create command"""
        cmd_parts = [self.pool_config['name']]
        
        # Add options
        cmd_parts.extend(['-o', f"ashift={self.pool_config.get('ashift', 12)}"])
        
        if self.pool_config.get('compression', 'off') != 'off':
            cmd_parts.extend(['-o', f"compression={self.pool_config['compression']}"])
            
        # Add RAID configuration
        raid_type = self.pool_config['raid_type']
        if raid_type == 'stripe':
            cmd_parts.extend(self.selected_disks)
        elif raid_type == 'mirror':
            cmd_parts.append('mirror')
            cmd_parts.extend(self.selected_disks)
        else:  # raidz variants
            cmd_parts.append(raid_type)
            cmd_parts.extend(self.selected_disks)
            
        return ' '.join(cmd_parts)
        
    # Event handlers
    def on_pool_name_changed(self, entry):
        """Handle pool name change"""
        self.pool_config['name'] = entry.get_text()
        self.update_summary()
        
    def on_disk_toggled(self, renderer, path):
        """Handle disk selection toggle"""
        iter = self.disk_store.get_iter(path)
        current = self.disk_store.get_value(iter, 0)
        self.disk_store.set_value(iter, 0, not current)
        
        # Update selected disks list
        disk_path = self.disk_store.get_value(iter, 1)
        if not current:
            if disk_path not in self.selected_disks:
                self.selected_disks.append(disk_path)
        else:
            if disk_path in self.selected_disks:
                self.selected_disks.remove(disk_path)
        
        # Update configuration
        self.pool_config['disks'] = self.selected_disks
        
        # Update UI
        self.update_recommendations()
        self.update_pool_stats()
        self.update_summary()
        self.pool_drawing.queue_draw()
        
    def on_raid_type_changed(self, button, raid_type):
        """Handle RAID type change"""
        if button.get_active():
            self.pool_config['raid_type'] = raid_type
            self.update_recommendations()
            self.update_pool_stats()
            self.update_summary()
            self.pool_drawing.queue_draw()
            
    def on_profile_changed(self, button, profile):
        """Handle workload profile change"""
        if button.get_active():
            self.pool_config['workload'] = profile
            
            # Apply profile-specific settings
            profiles = {
                'general': {'compression': 'lz4', 'recordsize': '128K'},
                'database': {'compression': 'lz4', 'recordsize': '16K'},
                'media': {'compression': 'off', 'recordsize': '1M'},
                'vm': {'compression': 'lz4', 'recordsize': '64K'},
                'backup': {'compression': 'zstd-3', 'recordsize': '128K'}
            }
            
            settings = profiles.get(profile, {})
            if 'compression' in settings:
                self.pool_config['compression'] = settings['compression']
                # Update compression combo
                model = self.comp_combo.get_model()
                for i in range(len(model)):
                    if model[i][0] == settings['compression']:
                        self.comp_combo.set_active(i)
                        break
                        
            self.update_summary()
            
    def on_ashift_changed(self, button, ashift):
        """Handle ashift change"""
        if button.get_active():
            self.pool_config['ashift'] = ashift
            self.update_summary()
            
    def on_compression_changed(self, combo):
        """Handle compression change"""
        self.pool_config['compression'] = combo.get_active_text()
        self.update_summary()
        
    def on_encryption_toggled(self, check):
        """Handle encryption toggle"""
        enabled = check.get_active()
        self.pool_config['encryption'] = enabled
        self.enc_grid.set_sensitive(enabled)
        self.update_summary()
        
    def on_arc_changed(self, scale):
        """Handle ARC size change"""
        self.update_arc_label()
        
    def get_configuration(self) -> Dict:
        """Get the current pool configuration"""
        # Validate encryption passwords if enabled
        if self.pool_config.get('encryption', False):
            pass1 = self.pass_entry.get_text()
            pass2 = self.confirm_entry.get_text()
            
            if not pass1:
                self.update_status("Encryption password required", True)
                return None
                
            if pass1 != pass2:
                self.update_status("Passwords do not match", True)
                return None
                
            # Store password temporarily (will be used during pool creation)
            self.pool_config['encryption_password'] = pass1
        
        # Ensure disks are in config
        self.pool_config['disks'] = self.selected_disks
        
        return self.pool_config
#!/usr/bin/env python3
"""
Storage Layout Templates GUI for Calamares
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango
from typing import Dict

class StorageLayoutWidget(Gtk.Box):
    """Storage layout template selection widget"""
    
    def __init__(self, globalstorage, pool_name):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.gs = globalstorage
        self.pool_name = pool_name or "tank"
        self.selected_template = "none"
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        # Header
        header = Gtk.Label()
        header.set_markup("<b>Storage Layout Templates</b>")
        self.pack_start(header, False, False, 0)
        
        if not self.pool_name:
            no_pool_label = Gtk.Label()
            no_pool_label.set_markup("<i>No ZFS pool configured. Please configure a pool first.</i>")
            self.pack_start(no_pool_label, True, True, 0)
        else:
            # Pool info
            pool_info = Gtk.Label()
            pool_info.set_markup(f"Configuring datasets for pool: <b>{self.pool_name}</b>")
            self.pack_start(pool_info, False, False, 0)
            
            # Template selection
            template_frame = Gtk.Frame(label="Select Template")
            template_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            template_box.set_margin_top(10)
            template_box.set_margin_bottom(10)
            template_box.set_margin_left(10)
            template_box.set_margin_right(10)
            
            templates = [
                ("none", "No Template", "Skip automatic dataset creation"),
                ("proxmox", "Proxmox Virtualization Server", "Optimized for VMs and containers"),
                ("media", "Homelab Media Server", "Optimized for media storage and streaming"),
                ("database", "Database Server", "Optimized for PostgreSQL, MySQL, MongoDB"),
                ("development", "Development Workstation", "Optimized for coding and development")
            ]
            
            self.template_buttons = {}
            first_button = None
            
            for template_id, name, description in templates:
                if first_button is None:
                    button = Gtk.RadioButton.new_with_label(None, name)
                    first_button = button
                else:
                    button = Gtk.RadioButton.new_with_label_from_widget(first_button, name)
                
                button.set_tooltip_text(description)
                button.connect("toggled", self.on_template_changed, template_id)
                self.template_buttons[template_id] = button
                template_box.pack_start(button, False, False, 0)
            
            # Set default
            self.template_buttons["none"].set_active(True)
            
            template_frame.add(template_box)
            self.pack_start(template_frame, False, False, 0)
            
            # Preview area
            preview_frame = Gtk.Frame(label="Preview")
            
            # Scrolled window for preview
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scroll.set_min_content_height(200)
            
            self.preview_buffer = Gtk.TextBuffer()
            self.preview_view = Gtk.TextView(buffer=self.preview_buffer)
            self.preview_view.set_editable(False)
            self.preview_view.set_wrap_mode(Gtk.WrapMode.WORD)
            
            # Use monospace font
            font_desc = Pango.FontDescription("monospace 9")
            self.preview_view.modify_font(font_desc)
            
            scroll.add(self.preview_view)
            preview_frame.add(scroll)
            self.pack_start(preview_frame, True, True, 0)
            
            # Options
            options_frame = Gtk.Frame(label="Options")
            options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            options_box.set_margin_top(10)
            options_box.set_margin_bottom(10)
            options_box.set_margin_left(10)
            options_box.set_margin_right(10)
            
            self.snapshot_check = Gtk.CheckButton(label="Create snapshot schedule")
            self.snapshot_check.set_tooltip_text("Automatically snapshot important datasets")
            options_box.pack_start(self.snapshot_check, False, False, 0)
            
            self.quota_check = Gtk.CheckButton(label="Set recommended quotas")
            self.quota_check.set_tooltip_text("Apply size limits to prevent runaway growth")
            options_box.pack_start(self.quota_check, False, False, 0)
            
            options_frame.add(options_box)
            self.pack_start(options_frame, False, False, 0)
            
            # Update preview
            self.update_preview()
        
        self.show_all()
        
    def on_template_changed(self, button, template_id):
        """Handle template selection change"""
        if button.get_active():
            self.selected_template = template_id
            self.update_preview()
            
            # Enable/disable options based on template
            if template_id == "none":
                self.snapshot_check.set_sensitive(False)
                self.quota_check.set_sensitive(False)
            else:
                self.snapshot_check.set_sensitive(True)
                self.quota_check.set_sensitive(True)
    
    def update_preview(self):
        """Update the preview text"""
        if self.selected_template == "none":
            preview_text = "No datasets will be created automatically."
        else:
            preview_text = self.generate_preview(self.selected_template)
        
        self.preview_buffer.set_text(preview_text)
    
    def generate_preview(self, template):
        """Generate preview text for template"""
        templates = {
            "proxmox": """Proxmox Virtualization Server Layout:

{}/vm-disks         (64K records, lz4)
  └─ VM disk images

{}/containers       (128K records, zstd-3)
  └─ LXC container storage

{}/templates        (1M records, no compression)
  └─ ISO and template storage

{}/backups          (1M records, zstd-6)
  └─ Backup storage

{}/shared           (128K records, lz4)
  └─ Shared data between VMs/containers""",
  
            "media": """Homelab Media Server Layout:

{}/media/movies     (1M records, no compression)
  └─ Movie collection

{}/media/tv         (1M records, no compression)
  └─ TV show collection

{}/media/music      (128K records, zstd)
  └─ Music library

{}/media/photos     (128K records, zstd)
  └─ Photo collection

{}/downloads        (128K records, lz4)
  └─ Download directory

{}/apps             (128K records, lz4)
  └─ Application data

{}/documents        (128K records, zstd-6)
  └─ Document storage""",
  
            "database": """Database Server Layout:

{}/postgres/data    (8K records, lz4, throughput)
  └─ PostgreSQL data directory

{}/postgres/wal     (128K records, no compression, sync)
  └─ PostgreSQL WAL logs

{}/mysql/data       (16K records, lz4)
  └─ MySQL data directory

{}/mysql/logs       (128K records, zstd)
  └─ MySQL logs

{}/mongodb          (16K records, lz4)
  └─ MongoDB data

{}/redis            (8K records, lz4, async)
  └─ Redis persistence""",
  
            "development": """Development Workstation Layout:

{}/home             (128K records, lz4)
  └─ User home directories

{}/projects         (128K records, lz4)
  └─ Development projects

{}/docker           (128K records, zstd)
  └─ Docker images and volumes

{}/vms              (64K records, lz4)
  └─ Virtual machines

{}/snapshots        (128K records, zstd-6)
  └─ Snapshot storage"""
        }
        
        template_text = templates.get(template, "Unknown template")
        # Replace {} with pool name
        return template_text.replace("{}", self.pool_name)
    
    def get_configuration(self) -> Dict:
        """Get the storage layout configuration"""
        return {
            "template": self.selected_template,
            "snapshot_schedule": self.snapshot_check.get_active() if hasattr(self, 'snapshot_check') else False,
            "set_quotas": self.quota_check.get_active() if hasattr(self, 'quota_check') else False
        }

#!/usr/bin/env python3
"""
Storage Layout Templates GUI for Calamares
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox, QLineEdit, QTextEdit, QGroupBox, QRadioButton, QScrollArea, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict

class StorageLayoutGui(QGroupBox):
    """Storage layout template selection widget"""
    
    def __init__(self, globalstorage, pool_name):
        super().__init__("Storage Layout Templates")
        self.gs = globalstorage
        self.pool_name = pool_name or "tank"
        self.selected_template = "none"
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("<b>Storage Layout Templates</b>")
        layout.addWidget(header)
        
        if not self.pool_name:
            no_pool_label = QLabel("<i>No ZFS pool configured. Please configure a pool first.</i>")
            layout.addWidget(no_pool_label)
        else:
            # Pool info
            pool_info = QLabel(f"Configuring datasets for pool: <b>{self.pool_name}</b>")
            layout.addWidget(pool_info)
            
            # Template selection
            template_frame = QGroupBox("Select Template")
            template_layout = QVBoxLayout()
            template_frame.setLayout(template_layout)
            
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
                button = QRadioButton(name)
                button.setToolTip(description)
                button.toggled.connect(lambda checked, tid=template_id: self.on_template_changed(checked, tid))
                self.template_buttons[template_id] = button
                template_layout.addWidget(button)
            
            # Set default
            self.template_buttons["none"].setChecked(True)
            
            layout.addWidget(template_frame)
            
            # Preview area
            preview_frame = QGroupBox("Preview")
            preview_layout = QVBoxLayout()
            preview_frame.setLayout(preview_layout)
            
            # Scrolled area for preview
            self.preview_view = QTextEdit()
            self.preview_view.setReadOnly(True)
            self.preview_view.setMinimumHeight(200)
            
            # Use monospace font
            font = QFont("monospace", 9)
            self.preview_view.setFont(font)
            
            preview_layout.addWidget(self.preview_view)
            layout.addWidget(preview_frame)
            
            # Options
            options_frame = QGroupBox("Options")
            options_layout = QVBoxLayout()
            options_frame.setLayout(options_layout)
            
            self.snapshot_check = QCheckBox("Create snapshot schedule")
            self.snapshot_check.setToolTip("Automatically snapshot important datasets")
            options_layout.addWidget(self.snapshot_check)
            
            self.quota_check = QCheckBox("Set recommended quotas")
            self.quota_check.setToolTip("Apply size limits to prevent runaway growth")
            options_layout.addWidget(self.quota_check)
            
            layout.addWidget(options_frame)
            
            # Update preview
            self.update_preview()
        
        self.show()
        
    def on_template_changed(self, checked, template_id):
        """Handle template selection change"""
        if checked:
            self.selected_template = template_id
            self.update_preview()
            
            # Enable/disable options based on template
            if template_id == "none":
                self.snapshot_check.setEnabled(False)
                self.quota_check.setEnabled(False)
            else:
                self.snapshot_check.setEnabled(True)
                self.quota_check.setEnabled(True)
    
    def update_preview(self):
        """Update the preview text"""
        if self.selected_template == "none":
            preview_text = "No datasets will be created automatically."
        else:
            preview_text = self.generate_preview(self.selected_template)
        
        self.preview_view.setText(preview_text)
    
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
            "snapshot_schedule": self.snapshot_check.isChecked() if hasattr(self, 'snapshot_check') else False,
            "set_quotas": self.quota_check.isChecked() if hasattr(self, 'quota_check') else False
        }
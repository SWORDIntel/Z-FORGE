#!/usr/bin/env python3
"""
Rich ZFS Configuration GUI Widget for Calamares
Provides comprehensive ZFS configuration with visual feedback
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QLineEdit, 
                             QTextEdit, QGroupBox, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QSpinBox,
                             QProgressBar, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
import json
import subprocess
from typing import Dict, List, Optional, Tuple

class ZFSRichConfigWidget(QWidget):
    """
    Rich ZFS configuration widget for Calamares integration
    """
    
    def __init__(self, globalstorage):
        super().__init__()
        self.gs = globalstorage
        
        # Initialize data structures
        self.available_disks = self._detect_disks()
        self.pool_configs = []
        self.boot_pool_config = {}
        self.data_pool_configs = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the comprehensive UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("<h2>Rich ZFS Pool Configuration</h2>")
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Configure advanced ZFS pools with separate boot and data pools, "
                     "encryption, compression, and performance tuning.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Main tab widget
        self.tabs = QTabWidget()
        
        # Add tabs
        self.tabs.addTab(self._create_boot_pool_tab(), "Boot Pool")
        self.tabs.addTab(self._create_data_pools_tab(), "Data Pools")
        self.tabs.addTab(self._create_advanced_tab(), "Advanced Settings")
        self.tabs.addTab(self._create_summary_tab(), "Summary")
        
        layout.addWidget(self.tabs)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.validate_button = QPushButton("Validate Configuration")
        self.validate_button.clicked.connect(self.validate_configuration)
        button_layout.addWidget(self.validate_button)
        
        self.apply_button = QPushButton("Apply Configuration")
        self.apply_button.clicked.connect(self.apply_configuration)
        self.apply_button.setEnabled(False)
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
    def _create_boot_pool_tab(self) -> QWidget:
        """Create boot pool configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Boot pool name
        name_group = QGroupBox("Boot Pool Name")
        name_layout = QHBoxLayout()
        name_group.setLayout(name_layout)
        
        self.boot_pool_name = QLineEdit("bpool")
        name_layout.addWidget(QLabel("Pool Name:"))
        name_layout.addWidget(self.boot_pool_name)
        layout.addWidget(name_group)
        
        # Boot drive selection
        disk_group = QGroupBox("Boot Drive Selection")
        disk_layout = QVBoxLayout()
        disk_group.setLayout(disk_layout)
        
        self.boot_disk_table = QTableWidget()
        self.boot_disk_table.setColumnCount(5)
        self.boot_disk_table.setHorizontalHeaderLabels(["Select", "Device", "Size", "Type", "Model"])
        
        # Populate disks
        self.boot_disk_table.setRowCount(len(self.available_disks))
        for i, disk in enumerate(self.available_disks):
            # Checkbox for selection
            check_item = QTableWidgetItem()
            check_item.setCheckState(Qt.Unchecked)
            self.boot_disk_table.setItem(i, 0, check_item)
            
            # Disk info
            self.boot_disk_table.setItem(i, 1, QTableWidgetItem(disk.get("device", "")))
            self.boot_disk_table.setItem(i, 2, QTableWidgetItem(disk.get("size", "")))
            self.boot_disk_table.setItem(i, 3, QTableWidgetItem(disk.get("type", "")))
            self.boot_disk_table.setItem(i, 4, QTableWidgetItem(disk.get("model", "")))
        
        self.boot_disk_table.resizeColumnsToContents()
        disk_layout.addWidget(self.boot_disk_table)
        layout.addWidget(disk_group)
        
        # Boot pool layout
        layout_group = QGroupBox("Boot Pool Layout")
        layout_layout = QHBoxLayout()
        layout_group.setLayout(layout_layout)
        
        layout_layout.addWidget(QLabel("Layout Type:"))
        self.boot_layout = QComboBox()
        self.boot_layout.addItems(["single", "mirror", "raidz1"])
        self.boot_layout.setCurrentIndex(1)  # Default to mirror
        layout_layout.addWidget(self.boot_layout)
        layout.addWidget(layout_group)
        
        # Boot pool options
        options_group = QGroupBox("Boot Pool Options")
        options_layout = QVBoxLayout()
        options_group.setLayout(options_layout)
        
        # Compression
        comp_layout = QHBoxLayout()
        comp_layout.addWidget(QLabel("Compression:"))
        self.boot_compression = QComboBox()
        self.boot_compression.addItems(["off", "lz4", "zstd", "gzip"])
        self.boot_compression.setCurrentIndex(1)  # Default to lz4
        comp_layout.addWidget(self.boot_compression)
        options_layout.addLayout(comp_layout)
        
        # Encryption
        self.boot_encrypt = QCheckBox("Enable encryption (requires passphrase at boot)")
        options_layout.addWidget(self.boot_encrypt)
        
        layout.addWidget(options_group)
        
        # Add stretch
        layout.addStretch()
        
        return widget
    
    def _create_data_pools_tab(self) -> QWidget:
        """Create data pools configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Info
        info = QLabel("<i>Configure one or more data pools. You can separate fast and slow storage, "
                     "or create specialized pools.</i>")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Pool list
        self.pool_list = QListWidget()
        layout.addWidget(self.pool_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("Add Pool")
        add_button.clicked.connect(self.add_data_pool)
        button_layout.addWidget(add_button)
        
        remove_button = QPushButton("Remove Pool")
        remove_button.clicked.connect(self.remove_data_pool)
        button_layout.addWidget(remove_button)
        
        edit_button = QPushButton("Edit Pool")
        edit_button.clicked.connect(self.edit_data_pool)
        button_layout.addWidget(edit_button)
        
        layout.addLayout(button_layout)
        
        # Pool configuration area
        self.pool_config_group = QGroupBox("Pool Configuration")
        pool_config_layout = QVBoxLayout()
        self.pool_config_group.setLayout(pool_config_layout)
        
        # Pool name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Pool Name:"))
        self.data_pool_name = QLineEdit("tank")
        name_layout.addWidget(self.data_pool_name)
        pool_config_layout.addLayout(name_layout)
        
        # Layout type
        layout_layout = QHBoxLayout()
        layout_layout.addWidget(QLabel("Layout:"))
        self.data_layout = QComboBox()
        self.data_layout.addItems(["single", "mirror", "raidz1", "raidz2", "raidz3"])
        layout_layout.addWidget(self.data_layout)
        pool_config_layout.addLayout(layout_layout)
        
        # Compression
        comp_layout = QHBoxLayout()
        comp_layout.addWidget(QLabel("Compression:"))
        self.data_compression = QComboBox()
        self.data_compression.addItems(["off", "lz4", "zstd", "zstd-3", "zstd-6", "gzip"])
        self.data_compression.setCurrentIndex(1)  # Default to lz4
        comp_layout.addWidget(self.data_compression)
        pool_config_layout.addLayout(comp_layout)
        
        # Encryption
        self.data_encrypt = QCheckBox("Enable encryption")
        pool_config_layout.addWidget(self.data_encrypt)
        
        # Deduplication
        self.data_dedup = QCheckBox("Enable deduplication (requires lots of RAM)")
        pool_config_layout.addWidget(self.data_dedup)
        
        layout.addWidget(self.pool_config_group)
        
        # Add stretch
        layout.addStretch()
        
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # ARC settings
        arc_group = QGroupBox("ARC (Adaptive Replacement Cache) Settings")
        arc_layout = QVBoxLayout()
        arc_group.setLayout(arc_layout)
        
        # ARC max size
        arc_max_layout = QHBoxLayout()
        arc_max_layout.addWidget(QLabel("Maximum ARC Size (GB):"))
        self.arc_max = QSpinBox()
        self.arc_max.setMinimum(1)
        self.arc_max.setMaximum(256)
        self.arc_max.setValue(8)  # Default 8GB
        arc_max_layout.addWidget(self.arc_max)
        arc_layout.addLayout(arc_max_layout)
        
        # ARC min size
        arc_min_layout = QHBoxLayout()
        arc_min_layout.addWidget(QLabel("Minimum ARC Size (GB):"))
        self.arc_min = QSpinBox()
        self.arc_min.setMinimum(1)
        self.arc_min.setMaximum(256)
        self.arc_min.setValue(4)  # Default 4GB
        arc_min_layout.addWidget(self.arc_min)
        arc_layout.addLayout(arc_min_layout)
        
        layout.addWidget(arc_group)
        
        # Performance tuning
        perf_group = QGroupBox("Performance Tuning")
        perf_layout = QVBoxLayout()
        perf_group.setLayout(perf_layout)
        
        # Record size
        record_layout = QHBoxLayout()
        record_layout.addWidget(QLabel("Default Record Size:"))
        self.record_size = QComboBox()
        self.record_size.addItems(["4K", "8K", "16K", "32K", "64K", "128K", "256K", "512K", "1M"])
        self.record_size.setCurrentIndex(5)  # Default to 128K
        record_layout.addWidget(self.record_size)
        perf_layout.addLayout(record_layout)
        
        # Sync mode
        sync_layout = QHBoxLayout()
        sync_layout.addWidget(QLabel("Sync Mode:"))
        self.sync_mode = QComboBox()
        self.sync_mode.addItems(["standard", "always", "disabled"])
        sync_layout.addWidget(self.sync_mode)
        perf_layout.addLayout(sync_layout)
        
        # Checkboxes
        self.trim_enable = QCheckBox("Enable TRIM support for SSDs")
        self.trim_enable.setChecked(True)
        perf_layout.addWidget(self.trim_enable)
        
        self.l2arc_enable = QCheckBox("Enable L2ARC (requires separate SSD)")
        perf_layout.addWidget(self.l2arc_enable)
        
        self.zil_enable = QCheckBox("Enable separate ZIL (SLOG) device")
        perf_layout.addWidget(self.zil_enable)
        
        layout.addWidget(perf_group)
        
        # Module parameters
        module_group = QGroupBox("ZFS Module Parameters")
        module_layout = QVBoxLayout()
        module_group.setLayout(module_layout)
        
        self.module_params = QTextEdit()
        self.module_params.setPlainText("# Add custom ZFS module parameters here\n"
                                        "# One per line, e.g.:\n"
                                        "# zfs_arc_max=8589934592\n")
        self.module_params.setMaximumHeight(100)
        module_layout.addWidget(self.module_params)
        
        layout.addWidget(module_group)
        
        # Add stretch
        layout.addStretch()
        
        return widget
    
    def _create_summary_tab(self) -> QWidget:
        """Create configuration summary tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Summary text
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        font = QFont("monospace", 9)
        self.summary_text.setFont(font)
        layout.addWidget(self.summary_text)
        
        # Update button
        update_button = QPushButton("Update Summary")
        update_button.clicked.connect(self.update_summary)
        layout.addWidget(update_button)
        
        return widget
    
    def _detect_disks(self) -> List[Dict]:
        """Detect available disks"""
        # Mock implementation - in real code, would use lsblk or similar
        return [
            {"device": "/dev/sda", "size": "500GB", "type": "SSD", "model": "Samsung 970 EVO"},
            {"device": "/dev/sdb", "size": "1TB", "type": "HDD", "model": "WD Blue"},
            {"device": "/dev/sdc", "size": "2TB", "type": "HDD", "model": "Seagate Barracuda"}
        ]
    
    def add_data_pool(self):
        """Add a new data pool"""
        pool_name = self.data_pool_name.text()
        if pool_name and pool_name not in [p["name"] for p in self.data_pool_configs]:
            pool_config = {
                "name": pool_name,
                "layout": self.data_layout.currentText(),
                "compression": self.data_compression.currentText(),
                "encryption": self.data_encrypt.isChecked(),
                "dedup": self.data_dedup.isChecked()
            }
            self.data_pool_configs.append(pool_config)
            self.pool_list.addItem(f"{pool_name} ({pool_config['layout']})")
            self.update_summary()
    
    def remove_data_pool(self):
        """Remove selected data pool"""
        current_item = self.pool_list.currentItem()
        if current_item:
            row = self.pool_list.row(current_item)
            self.pool_list.takeItem(row)
            if row < len(self.data_pool_configs):
                del self.data_pool_configs[row]
            self.update_summary()
    
    def edit_data_pool(self):
        """Edit selected data pool"""
        # Implementation would open a dialog to edit pool settings
        pass
    
    def update_summary(self):
        """Update the configuration summary"""
        summary = "=== ZFS Configuration Summary ===\n\n"
        
        # Boot pool
        summary += "Boot Pool:\n"
        summary += f"  Name: {self.boot_pool_name.text()}\n"
        summary += f"  Layout: {self.boot_layout.currentText()}\n"
        summary += f"  Compression: {self.boot_compression.currentText()}\n"
        summary += f"  Encryption: {'Yes' if self.boot_encrypt.isChecked() else 'No'}\n\n"
        
        # Data pools
        summary += "Data Pools:\n"
        for pool in self.data_pool_configs:
            summary += f"  {pool['name']}:\n"
            summary += f"    Layout: {pool['layout']}\n"
            summary += f"    Compression: {pool['compression']}\n"
            summary += f"    Encryption: {'Yes' if pool['encryption'] else 'No'}\n"
            summary += f"    Deduplication: {'Yes' if pool['dedup'] else 'No'}\n"
        
        if not self.data_pool_configs:
            summary += "  (No data pools configured)\n"
        
        summary += "\n"
        
        # Advanced settings
        summary += "Advanced Settings:\n"
        summary += f"  ARC Max: {self.arc_max.value()} GB\n"
        summary += f"  ARC Min: {self.arc_min.value()} GB\n"
        summary += f"  Record Size: {self.record_size.currentText()}\n"
        summary += f"  Sync Mode: {self.sync_mode.currentText()}\n"
        summary += f"  TRIM: {'Enabled' if self.trim_enable.isChecked() else 'Disabled'}\n"
        summary += f"  L2ARC: {'Enabled' if self.l2arc_enable.isChecked() else 'Disabled'}\n"
        summary += f"  Separate ZIL: {'Enabled' if self.zil_enable.isChecked() else 'Disabled'}\n"
        
        self.summary_text.setPlainText(summary)
    
    def validate_configuration(self):
        """Validate the current configuration"""
        errors = []
        
        # Check boot pool
        if not self.boot_pool_name.text():
            errors.append("Boot pool name is required")
        
        # Check if at least one disk is selected for boot pool
        selected_boot_disks = 0
        for row in range(self.boot_disk_table.rowCount()):
            item = self.boot_disk_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                selected_boot_disks += 1
        
        if selected_boot_disks == 0:
            errors.append("At least one disk must be selected for boot pool")
        
        # Check layout requirements
        layout = self.boot_layout.currentText()
        if layout == "mirror" and selected_boot_disks < 2:
            errors.append("Mirror layout requires at least 2 disks")
        elif layout == "raidz1" and selected_boot_disks < 3:
            errors.append("RAIDZ1 layout requires at least 3 disks")
        
        # Check ARC settings
        if self.arc_min.value() > self.arc_max.value():
            errors.append("ARC minimum cannot be greater than maximum")
        
        if errors:
            self.status_label.setText(f"Validation failed: {', '.join(errors)}")
            self.status_label.setStyleSheet("color: red")
            self.apply_button.setEnabled(False)
        else:
            self.status_label.setText("Configuration is valid")
            self.status_label.setStyleSheet("color: green")
            self.apply_button.setEnabled(True)
    
    def apply_configuration(self):
        """Apply the configuration to global storage"""
        config = self.get_configuration()
        
        # Store in global storage
        self.gs.setValue("zfsRichConfig", json.dumps(config))
        
        self.status_label.setText("Configuration applied successfully")
        self.status_label.setStyleSheet("color: green")
    
    def get_configuration(self) -> Dict:
        """Get the complete configuration"""
        # Get selected boot disks
        boot_disks = []
        for row in range(self.boot_disk_table.rowCount()):
            item = self.boot_disk_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                device_item = self.boot_disk_table.item(row, 1)
                if device_item:
                    boot_disks.append(device_item.text())
        
        config = {
            "boot_pool": {
                "name": self.boot_pool_name.text(),
                "layout": self.boot_layout.currentText(),
                "disks": boot_disks,
                "compression": self.boot_compression.currentText(),
                "encryption": self.boot_encrypt.isChecked()
            },
            "data_pools": self.data_pool_configs,
            "advanced": {
                "arc_max": self.arc_max.value() * 1024 * 1024 * 1024,  # Convert to bytes
                "arc_min": self.arc_min.value() * 1024 * 1024 * 1024,
                "record_size": self.record_size.currentText(),
                "sync_mode": self.sync_mode.currentText(),
                "trim_enabled": self.trim_enable.isChecked(),
                "l2arc_enabled": self.l2arc_enable.isChecked(),
                "zil_enabled": self.zil_enable.isChecked(),
                "module_params": self.module_params.toPlainText()
            }
        }
        
        return config
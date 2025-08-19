#!/usr/bin/env python3
"""
Enhanced ZFS Configuration GUI Widget for Calamares
Provides advanced ZFS pool configuration with visual feedback
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QLineEdit, 
                             QTextEdit, QGroupBox, QTableWidget, QTableWidgetItem,
                             QTabWidget, QSpinBox, QListWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import json
import subprocess
import math
from typing import Dict, List, Optional, Tuple

class ZfsEnhancedGui(QGroupBox):
    """
    Enhanced ZFS configuration widget for Calamares integration
    """
    
    def __init__(self, globalstorage):
        super().__init__("Enhanced ZFS Configuration")
        
        self.gs = globalstorage
        
        # Initialize data structures
        self.available_disks = []
        self.selected_disks = []
        self.pool_config = {
            "pool_name": "tank",
            "vdev_type": "mirror",
            "compression": "lz4",
            "atime": "off",
            "encryption": False,
            "dedup": False,
            "recordsize": "128K",
            "ashift": "12",
            "mountpoint": "/tank"
        }
        
        self.setup_ui()
        self.detect_disks()
        
    def setup_ui(self):
        """Build the enhanced UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("<h3>Enhanced ZFS Pool Configuration</h3>")
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Configure advanced ZFS pool settings with automatic optimization")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Main content area with tabs
        self.tabs = QTabWidget()
        
        # Disk Selection Tab
        disk_widget = self.create_disk_selection_tab()
        self.tabs.addTab(disk_widget, "Disk Selection")
        
        # Pool Configuration Tab
        pool_widget = self.create_pool_config_tab()
        self.tabs.addTab(pool_widget, "Pool Configuration")
        
        # Advanced Settings Tab
        advanced_widget = self.create_advanced_settings_tab()
        self.tabs.addTab(advanced_widget, "Advanced Settings")
        
        # Summary Tab
        summary_widget = self.create_summary_tab()
        self.tabs.addTab(summary_widget, "Summary")
        
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
        
    def create_disk_selection_tab(self) -> QWidget:
        """Create the disk selection tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Instructions
        instructions = QLabel("Select disks to include in the ZFS pool:")
        layout.addWidget(instructions)
        
        # Disk table
        self.disk_table = QTableWidget()
        self.disk_table.setColumnCount(6)
        self.disk_table.setHorizontalHeaderLabels(["Select", "Device", "Size", "Model", "Type", "Health"])
        
        layout.addWidget(self.disk_table)
        
        # Quick selection buttons
        button_layout = QHBoxLayout()
        
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(self.select_all_disks)
        button_layout.addWidget(select_all_button)
        
        clear_button = QPushButton("Clear Selection")
        clear_button.clicked.connect(self.clear_disk_selection)
        button_layout.addWidget(clear_button)
        
        auto_select_button = QPushButton("Auto-Select Best Disks")
        auto_select_button.clicked.connect(self.auto_select_disks)
        button_layout.addWidget(auto_select_button)
        
        layout.addLayout(button_layout)
        
        # Selection info
        self.selection_info = QLabel("No disks selected")
        layout.addWidget(self.selection_info)
        
        return widget
        
    def create_pool_config_tab(self) -> QWidget:
        """Create the pool configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Pool name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Pool Name:"))
        self.pool_name_input = QLineEdit("tank")
        name_layout.addWidget(self.pool_name_input)
        layout.addLayout(name_layout)
        
        # VDEV type
        vdev_layout = QHBoxLayout()
        vdev_layout.addWidget(QLabel("VDEV Type:"))
        self.vdev_type_combo = QComboBox()
        self.vdev_type_combo.addItems(["single", "mirror", "raidz1", "raidz2", "raidz3"])
        self.vdev_type_combo.setCurrentText("mirror")
        self.vdev_type_combo.currentTextChanged.connect(self.update_vdev_requirements)
        vdev_layout.addWidget(self.vdev_type_combo)
        layout.addLayout(vdev_layout)
        
        # VDEV requirements info
        self.vdev_info = QLabel("Mirror requires at least 2 disks")
        layout.addWidget(self.vdev_info)
        
        # Compression
        comp_layout = QHBoxLayout()
        comp_layout.addWidget(QLabel("Compression:"))
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["off", "lz4", "zstd", "zstd-3", "zstd-6", "gzip", "gzip-9"])
        self.compression_combo.setCurrentText("lz4")
        comp_layout.addWidget(self.compression_combo)
        layout.addLayout(comp_layout)
        
        # Mount point
        mount_layout = QHBoxLayout()
        mount_layout.addWidget(QLabel("Mount Point:"))
        self.mountpoint_input = QLineEdit("/tank")
        mount_layout.addWidget(self.mountpoint_input)
        layout.addLayout(mount_layout)
        
        # Features
        features_group = QGroupBox("Features")
        features_layout = QVBoxLayout()
        features_group.setLayout(features_layout)
        
        self.encryption_check = QCheckBox("Enable native encryption")
        features_layout.addWidget(self.encryption_check)
        
        self.dedup_check = QCheckBox("Enable deduplication (requires lots of RAM)")
        features_layout.addWidget(self.dedup_check)
        
        self.atime_check = QCheckBox("Enable access time updates")
        features_layout.addWidget(self.atime_check)
        
        layout.addWidget(features_group)
        
        return widget
        
    def create_advanced_settings_tab(self) -> QWidget:
        """Create the advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Record size
        record_layout = QHBoxLayout()
        record_layout.addWidget(QLabel("Record Size:"))
        self.recordsize_combo = QComboBox()
        self.recordsize_combo.addItems(["4K", "8K", "16K", "32K", "64K", "128K", "256K", "512K", "1M"])
        self.recordsize_combo.setCurrentText("128K")
        record_layout.addWidget(self.recordsize_combo)
        layout.addLayout(record_layout)
        
        # Ashift (sector size)
        ashift_layout = QHBoxLayout()
        ashift_layout.addWidget(QLabel("Ashift (sector size):"))
        self.ashift_spin = QSpinBox()
        self.ashift_spin.setMinimum(9)
        self.ashift_spin.setMaximum(16)
        self.ashift_spin.setValue(12)  # 4K sectors
        ashift_layout.addWidget(self.ashift_spin)
        ashift_layout.addWidget(QLabel(f"(2^12 = 4096 bytes)"))
        layout.addLayout(ashift_layout)
        
        # ARC settings
        arc_group = QGroupBox("ARC Settings")
        arc_layout = QVBoxLayout()
        arc_group.setLayout(arc_layout)
        
        arc_max_layout = QHBoxLayout()
        arc_max_layout.addWidget(QLabel("Max ARC Size (GB):"))
        self.arc_max_spin = QSpinBox()
        self.arc_max_spin.setMinimum(1)
        self.arc_max_spin.setMaximum(256)
        self.arc_max_spin.setValue(8)
        arc_max_layout.addWidget(self.arc_max_spin)
        arc_layout.addLayout(arc_max_layout)
        
        layout.addWidget(arc_group)
        
        # Performance tuning
        perf_group = QGroupBox("Performance Tuning")
        perf_layout = QVBoxLayout()
        perf_group.setLayout(perf_layout)
        
        self.sync_disabled_check = QCheckBox("Disable sync writes (faster but less safe)")
        perf_layout.addWidget(self.sync_disabled_check)
        
        self.trim_check = QCheckBox("Enable TRIM for SSDs")
        self.trim_check.setChecked(True)
        perf_layout.addWidget(self.trim_check)
        
        self.l2arc_check = QCheckBox("Enable L2ARC (requires separate SSD)")
        perf_layout.addWidget(self.l2arc_check)
        
        layout.addWidget(perf_group)
        
        # Custom properties
        custom_group = QGroupBox("Custom Properties")
        custom_layout = QVBoxLayout()
        custom_group.setLayout(custom_layout)
        
        self.custom_props = QTextEdit()
        self.custom_props.setPlainText("# Add custom ZFS properties here\n# Format: property=value\n# Example: logbias=throughput")
        self.custom_props.setMaximumHeight(100)
        custom_layout.addWidget(self.custom_props)
        
        layout.addWidget(custom_group)
        
        return widget
        
    def create_summary_tab(self) -> QWidget:
        """Create the summary tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Summary text area
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
        
    def detect_disks(self):
        """Detect available disks"""
        # Mock implementation - in real code would use lsblk
        self.available_disks = [
            {"device": "/dev/sda", "size": "500GB", "model": "Samsung 970 EVO", "type": "SSD", "health": "Good"},
            {"device": "/dev/sdb", "size": "1TB", "model": "WD Blue", "type": "HDD", "health": "Good"},
            {"device": "/dev/sdc", "size": "2TB", "model": "Seagate Barracuda", "type": "HDD", "health": "Good"}
        ]
        
        # Populate disk table
        self.disk_table.setRowCount(len(self.available_disks))
        for i, disk in enumerate(self.available_disks):
            # Checkbox for selection
            check_item = QTableWidgetItem()
            check_item.setCheckState(Qt.Unchecked)
            self.disk_table.setItem(i, 0, check_item)
            
            # Disk info
            self.disk_table.setItem(i, 1, QTableWidgetItem(disk.get("device", "")))
            self.disk_table.setItem(i, 2, QTableWidgetItem(disk.get("size", "")))
            self.disk_table.setItem(i, 3, QTableWidgetItem(disk.get("model", "")))
            self.disk_table.setItem(i, 4, QTableWidgetItem(disk.get("type", "")))
            self.disk_table.setItem(i, 5, QTableWidgetItem(disk.get("health", "")))
        
        self.disk_table.resizeColumnsToContents()
        
    def select_all_disks(self):
        """Select all disks"""
        for row in range(self.disk_table.rowCount()):
            item = self.disk_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)
        self.update_selection_info()
        
    def clear_disk_selection(self):
        """Clear all disk selections"""
        for row in range(self.disk_table.rowCount()):
            item = self.disk_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self.update_selection_info()
        
    def auto_select_disks(self):
        """Auto-select best disks based on type and size"""
        # Simple heuristic: prefer SSDs, then larger disks
        # This would be more sophisticated in production
        self.clear_disk_selection()
        
        # Select first 2 disks for mirror
        for row in range(min(2, self.disk_table.rowCount())):
            item = self.disk_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)
        
        self.update_selection_info()
        
    def update_selection_info(self):
        """Update the selection info label"""
        selected_count = 0
        total_size = 0
        
        for row in range(self.disk_table.rowCount()):
            item = self.disk_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                selected_count += 1
                # In real implementation, would parse size properly
                
        if selected_count == 0:
            self.selection_info.setText("No disks selected")
        else:
            self.selection_info.setText(f"{selected_count} disk(s) selected")
            
    def update_vdev_requirements(self, vdev_type):
        """Update VDEV requirements info"""
        requirements = {
            "single": "Requires 1 disk (no redundancy)",
            "mirror": "Requires at least 2 disks",
            "raidz1": "Requires at least 3 disks",
            "raidz2": "Requires at least 4 disks",
            "raidz3": "Requires at least 5 disks"
        }
        self.vdev_info.setText(requirements.get(vdev_type, ""))
        
    def update_summary(self):
        """Update the configuration summary"""
        summary = "=== ZFS Pool Configuration Summary ===\n\n"
        
        # Pool basics
        summary += f"Pool Name: {self.pool_name_input.text()}\n"
        summary += f"VDEV Type: {self.vdev_type_combo.currentText()}\n"
        summary += f"Mount Point: {self.mountpoint_input.text()}\n\n"
        
        # Selected disks
        summary += "Selected Disks:\n"
        for row in range(self.disk_table.rowCount()):
            item = self.disk_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                device_item = self.disk_table.item(row, 1)
                size_item = self.disk_table.item(row, 2)
                if device_item and size_item:
                    summary += f"  - {device_item.text()} ({size_item.text()})\n"
        
        summary += "\n"
        
        # Features
        summary += "Features:\n"
        summary += f"  Compression: {self.compression_combo.currentText()}\n"
        summary += f"  Encryption: {'Enabled' if self.encryption_check.isChecked() else 'Disabled'}\n"
        summary += f"  Deduplication: {'Enabled' if self.dedup_check.isChecked() else 'Disabled'}\n"
        summary += f"  Access Time: {'Enabled' if self.atime_check.isChecked() else 'Disabled'}\n\n"
        
        # Advanced settings
        summary += "Advanced Settings:\n"
        summary += f"  Record Size: {self.recordsize_combo.currentText()}\n"
        summary += f"  Ashift: {self.ashift_spin.value()} (sector size: {2**self.ashift_spin.value()} bytes)\n"
        summary += f"  Max ARC: {self.arc_max_spin.value()} GB\n"
        summary += f"  TRIM: {'Enabled' if self.trim_check.isChecked() else 'Disabled'}\n"
        summary += f"  Sync Disabled: {'Yes' if self.sync_disabled_check.isChecked() else 'No'}\n"
        
        self.summary_text.setPlainText(summary)
        
    def validate_configuration(self):
        """Validate the current configuration"""
        errors = []
        
        # Check pool name
        pool_name = self.pool_name_input.text().strip()
        if not pool_name:
            errors.append("Pool name is required")
        elif not pool_name.replace("_", "").replace("-", "").isalnum():
            errors.append("Pool name must be alphanumeric (plus _ and -)")
            
        # Check disk selection
        selected_disks = 0
        for row in range(self.disk_table.rowCount()):
            item = self.disk_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                selected_disks += 1
                
        vdev_type = self.vdev_type_combo.currentText()
        min_disks = {
            "single": 1,
            "mirror": 2,
            "raidz1": 3,
            "raidz2": 4,
            "raidz3": 5
        }
        
        required = min_disks.get(vdev_type, 1)
        if selected_disks < required:
            errors.append(f"{vdev_type} requires at least {required} disk(s), but only {selected_disks} selected")
            
        # Check mountpoint
        mountpoint = self.mountpoint_input.text().strip()
        if not mountpoint.startswith("/"):
            errors.append("Mount point must be an absolute path")
            
        # Display results
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
        # Gather selected disks
        selected_disks = []
        for row in range(self.disk_table.rowCount()):
            item = self.disk_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                device_item = self.disk_table.item(row, 1)
                if device_item:
                    selected_disks.append(device_item.text())
                    
        # Build configuration
        config = {
            "pool_name": self.pool_name_input.text(),
            "vdev_type": self.vdev_type_combo.currentText(),
            "disks": selected_disks,
            "compression": self.compression_combo.currentText(),
            "mountpoint": self.mountpoint_input.text(),
            "encryption": self.encryption_check.isChecked(),
            "dedup": self.dedup_check.isChecked(),
            "atime": "on" if self.atime_check.isChecked() else "off",
            "recordsize": self.recordsize_combo.currentText(),
            "ashift": self.ashift_spin.value(),
            "arc_max": self.arc_max_spin.value() * 1024 * 1024 * 1024,  # Convert to bytes
            "trim": self.trim_check.isChecked(),
            "sync": "disabled" if self.sync_disabled_check.isChecked() else "standard",
            "custom_props": self.custom_props.toPlainText()
        }
        
        # Store in global storage
        self.gs.setValue("zfsEnhancedConfig", json.dumps(config))
        
        self.status_label.setText("Configuration applied successfully")
        self.status_label.setStyleSheet("color: green")
        
    def get_configuration(self) -> Dict:
        """Get the current configuration"""
        return self.pool_config